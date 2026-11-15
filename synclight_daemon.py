"""Claude Code の状態をLEDに描画し続ける常駐プログラム。

フック (claude_hook.py) が sessions/<session_id>.json に状態を書き、
ここで全セッションをまとめて 待ち > 作業中 > 完了 > 待機 の優先順で表示する。
  作業中: オレンジがゆっくり明暗   待ち: 黄の点滅
  完了: 緑（done_seconds 秒）→ 待機: うす青   セッションなし: 消灯して終了
"""
import json
import math
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import slcommon as C  # noqa: E402
import synclight_led as L  # noqa: E402

FPS = 30
STALE_WORKING = 30 * 60      # この秒数イベントがない作業中/待ちは止まったとみなす
STALE_SESSION = 12 * 3600    # この秒数更新のないセッションは削除
EXIT_AFTER_OFF = 60          # 何もない状態がこの秒数続いたら終了


def log(msg):
    try:
        C.HOME.mkdir(parents=True, exist_ok=True)
        with open(C.LOG, "a", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + msg + "\n")
    except OSError:
        pass


def read_sessions(now):
    out = []
    for p in C.SESSIONS.glob("*.json"):
        try:
            s = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if now - s.get("ts", 0) > STALE_SESSION:
            p.unlink(missing_ok=True)
            continue
        out.append(s)
    return out


def overall_state(sessions, now, cfg):
    fresh = lambda s: now - s.get("ts", 0) < STALE_WORKING  # noqa: E731
    if any(s["state"] == "waiting" and fresh(s) for s in sessions):
        return "waiting"
    if any(s["state"] == "working" and fresh(s) for s in sessions):
        return "working"
    if any(s["state"] == "done" and now - s.get("ts", 0) < cfg["done_seconds"] for s in sessions):
        return "done"
    return "idle" if sessions else "off"


def render(state, t, cfg):
    c = cfg["colors"]
    if state == "working":
        k = 0.3 + 0.7 * (0.5 + 0.5 * math.sin(2 * math.pi * t / 2.4))
        return tuple(v * k for v in c["working"])
    if state == "waiting":
        return tuple(c["waiting"]) if (t % 0.9) < 0.55 else (0, 0, 0)
    if state in ("done", "idle"):
        return tuple(c[state])
    return (0, 0, 0)


def main():
    mutex = C.acquire_daemon_mutex()
    if mutex is None:
        return 0  # すでに動いている
    C.STOP_FLAG.unlink(missing_ok=True)
    log("start")
    dev = None
    last_rgb, last_send = None, 0.0
    killed_path = ""            # 自分が終了させたSyncLightのパス
    off_since = None
    cfg = C.load_config()
    cfg_time = 0.0

    while not C.STOP_FLAG.exists():
        now = time.time()
        if now - cfg_time > 5:
            cfg, cfg_time = C.load_config(), now
        if dev is None:
            dev = L.Device(cfg["lamps"])
        state = overall_state(read_sessions(now), now, cfg)
        active = state in ("working", "waiting", "done")

        # ---- SyncLight との共存 ----
        if cfg["takeover"] and active and C.synclight_running():
            path = C.kill_synclight()
            killed_path = path or cfg.get("synclight_exe") or killed_path or "?"
            if path and path != cfg.get("synclight_exe"):
                cfg["synclight_exe"] = path
                C.save_config({k: v for k, v in cfg.items()})
            log(f"SyncLightを終了: {path}")
            time.sleep(1.0)
            last_rgb = None
        if killed_path and not active:  # 完了表示が終わったらすぐSyncLightに戻す
            dev.close()
            ok, info = C.launch_synclight(cfg.get("synclight_exe") or killed_path)
            log(f"SyncLightを再起動: {info}" if ok else f"SyncLightを起動できませんでした: {info}")
            killed_path = ""  # 失敗しても何度も試さない
        yielding = C.synclight_running()  # SyncLightが動いている間はLEDを譲る

        if yielding:
            dev.close()
            last_rgb = None
        else:
            rgb = tuple(int(v) for v in render(state, now, cfg))
            if rgb != last_rgb or now - last_send > 3:
                try:
                    dev.color(rgb)
                    last_rgb, last_send = rgb, now
                except Exception as e:  # 抜けている等。少し待って再試行
                    log(f"送信失敗: {e}")
                    time.sleep(2)

        if state == "off" and not killed_path:
            off_since = off_since or now
            if now - off_since > EXIT_AFTER_OFF:
                break
        else:
            off_since = None
        time.sleep(1 / FPS if state in ("working", "waiting") else 0.25)

    if dev and not C.synclight_running():
        try:
            dev.color((0, 0, 0))
        except Exception:
            pass
        dev.close()
    if killed_path:
        ok, info = C.launch_synclight(cfg.get("synclight_exe") or killed_path)
        log(f"SyncLightを再起動: {info}" if ok else f"SyncLightを起動できませんでした: {info}")
    C.STOP_FLAG.unlink(missing_ok=True)
    log("exit")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        log(traceback.format_exc())
        raise
