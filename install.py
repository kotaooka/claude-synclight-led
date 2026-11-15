"""claude-synclight-led を ~/.claude/synclight に入れ、Claude Code のフックを登録する。

  python install.py               インストール（再実行で更新）
  python install.py --takeover    Claude作業中はSyncLightを自動で終了し、終わったら起動し直す
  python install.py --no-takeover 上の自動切り替えをやめる
  python install.py --uninstall   フックを削除して常駐プログラムを止める
既存の ~/.claude/settings.json は settings.json.bak にバックアップされる。
"""
import json
import shutil
import sys
import time
from pathlib import Path

SRC = Path(__file__).resolve().parent
sys.path.insert(0, str(SRC))
import slcommon as C  # noqa: E402

SETTINGS = Path.home() / ".claude" / "settings.json"
FILES = ["synclight_led.py", "slcommon.py", "synclight_daemon.py", "claude_hook.py"]
EVENTS = ["SessionStart", "UserPromptSubmit", "PostToolUse", "Notification", "Stop", "SessionEnd"]
MARK = "synclight"  # 旧バージョン(synclight_led.py直接呼び出し)のフックも消す


def load():
    if SETTINGS.exists():
        shutil.copy2(SETTINGS, SETTINGS.with_suffix(".json.bak"))
        return json.loads(SETTINGS.read_text(encoding="utf-8"))
    return {}


def save(settings):
    SETTINGS.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS.write_text(json.dumps(settings, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def strip(settings):
    hooks = settings.get("hooks", {})
    for ev in list(hooks):
        groups = [g for g in hooks[ev]
                  if not any(MARK in h.get("command", "") for h in g.get("hooks", []))]
        if groups:
            hooks[ev] = groups
        else:
            del hooks[ev]
    if not hooks:
        settings.pop("hooks", None)
    return settings


def stop_daemon():
    if C.daemon_running():
        C.HOME.mkdir(parents=True, exist_ok=True)
        C.STOP_FLAG.touch()
        for _ in range(40):
            if not C.daemon_running():
                break
            time.sleep(0.1)


def install(takeover):
    stop_daemon()  # 更新時は古い常駐プログラムを止める
    C.HOME.mkdir(parents=True, exist_ok=True)
    for f in FILES:
        shutil.copy2(SRC / f, C.HOME / f)
    cfg = C.load_config()
    if takeover is not None:
        cfg["takeover"] = takeover
    C.save_config(cfg)

    settings = strip(load())
    hooks = settings.setdefault("hooks", {})
    cmd = f'"{Path(sys.executable).as_posix()}" -I "{(C.HOME / "claude_hook.py").as_posix()}"'
    for ev in EVENTS:
        group = {"hooks": [{"type": "command", "command": cmd, "timeout": 5}]}
        if ev == "PostToolUse":
            group = {"matcher": "*", **group}
        hooks.setdefault(ev, []).append(group)
    save(settings)
    print(f"インストールしました: {C.HOME}")
    print(f"フックを登録しました: {SETTINGS}")
    print(f"設定ファイル: {C.CONFIG}（takeover = {cfg['takeover']}）")


def uninstall():
    save(strip(load()))
    stop_daemon()
    print(f"フックを削除し、常駐プログラムを止めました（{C.HOME} は残しています）")


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--uninstall" in args:
        uninstall()
    else:
        install(True if "--takeover" in args else False if "--no-takeover" in args else None)
