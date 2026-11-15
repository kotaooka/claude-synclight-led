"""synclight_led.py を ~/.claude/hooks に置き、Claude Code のフックを登録する。

  python install.py            インストール
  python install.py --uninstall  フックを削除
既存の ~/.claude/settings.json は settings.json.bak にバックアップされる。
"""
import json
import shutil
import sys
from pathlib import Path

CLAUDE = Path.home() / ".claude"
SETTINGS = CLAUDE / "settings.json"
TARGET = CLAUDE / "hooks" / "synclight_led.py"
MARK = "synclight_led.py"

EVENTS = {
    "UserPromptSubmit": "working",
    "PostToolUse": "working",
    "Notification": "waiting",
    "Stop": "done",
    "SessionEnd": "idle",
}


def load():
    if SETTINGS.exists():
        shutil.copy2(SETTINGS, SETTINGS.with_suffix(".json.bak"))
        return json.loads(SETTINGS.read_text(encoding="utf-8"))
    return {}


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


def install():
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(Path(__file__).with_name("synclight_led.py"), TARGET)
    settings = strip(load())
    hooks = settings.setdefault("hooks", {})
    script = TARGET.as_posix()
    for ev, state in EVENTS.items():
        group = {"hooks": [{"type": "command",
                            "command": f'python -I "{script}" {state}',
                            "timeout": 5}]}
        if ev == "PostToolUse":
            group = {"matcher": "*", **group}
        hooks.setdefault(ev, []).append(group)
    SETTINGS.write_text(json.dumps(settings, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"インストールしました: {TARGET}\nフックを登録しました: {SETTINGS}")


def uninstall():
    settings = strip(load())
    SETTINGS.write_text(json.dumps(settings, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"フックを削除しました: {SETTINGS}（{TARGET} は残しています）")


if __name__ == "__main__":
    uninstall() if "--uninstall" in sys.argv else install()
