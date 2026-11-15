"""Claude Code のフックから呼ばれる。セッションの状態をファイルに書き、
常駐プログラムが動いていなければ起動する。USBには触らないので軽い。"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import slcommon as C  # noqa: E402


def state_for(event, data):
    if event in ("UserPromptSubmit", "PostToolUse"):
        return "working"
    if event == "PermissionRequest":  # 許可ダイアログの表示と同時に呼ばれる
        return "waiting"
    if event == "Notification":  # 許可待ちの通知は少し遅れて届くので保険として使う
        kind = data.get("notification_type", "")
        msg = data.get("message", "").lower()
        if kind == "permission_prompt" or "permission" in msg:
            return "waiting"
        return None  # 入力待ちのリマインドなどは無視
    if event == "Stop":
        return "done"
    if event == "SessionStart":
        return "idle"
    return None


def ensure_daemon():
    if C.daemon_running():
        return
    exe = Path(sys.executable)
    pyw = exe.with_name("pythonw.exe")
    subprocess.Popen([str(pyw if pyw.exists() else exe), "-I",
                      str(Path(__file__).with_name("synclight_daemon.py"))],
                     creationflags=C.DETACHED | C.NO_WINDOW, close_fds=True,
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main():
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        data = {}
    event = data.get("hook_event_name", sys.argv[1] if len(sys.argv) > 1 else "")
    sid = "".join(ch for ch in str(data.get("session_id", "default")) if ch.isalnum() or ch in "-_") or "default"
    C.SESSIONS.mkdir(parents=True, exist_ok=True)
    path = C.SESSIONS / f"{sid}.json"
    if C.load_config().get("debug"):  # 調査用: フックが呼ばれた時刻を記録
        with open(C.HOME / "hook.log", "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%H:%M:%S')}.{int(time.time() * 1000) % 1000:03d} {event} {sid[:8]}\n")

    if event == "SessionEnd":
        path.unlink(missing_ok=True)
        return
    state = state_for(event, data)
    if state is None:
        return
    tmp = path.with_suffix(f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps({"state": state, "ts": time.time()}), encoding="utf-8")
    os.replace(tmp, path)
    ensure_daemon()

    if event == "SessionStart" and not C.load_config()["takeover"] and C.synclight_running():
        print(json.dumps({"systemMessage":
                          "SyncLight が起動中のため、LED表示は SyncLight を終了するまで停止します。"
                          "（config.json の takeover を true にすると自動で切り替えます）"},
                         ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # フックの失敗で Claude を止めない
        print(f"claude-synclight: {e}", file=sys.stderr)
    sys.exit(0)
