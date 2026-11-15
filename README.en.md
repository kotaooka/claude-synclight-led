# claude-synclight-led

[日本語](README.md)

Show the status of [Claude Code](https://claude.com/claude-code) on a Robobloq [**SyncLight**](https://quiklight.robobloq.com/sync-lights) LED strip (e.g. a monitor backlight).

| Claude Code status | LED |
|---|---|
| Working (prompt sent / tools running) | 🟠 Orange, slowly breathing |
| Waiting for permission | 🟡 Blinking yellow |
| Response finished | 🟢 Green (for 3 minutes) |
| Idle (session open) | 🔵 Dim blue |
| No sessions | Off |

With several sessions running, the strip shows the highest-priority state: **waiting > working > done > idle**, so a session asking for permission is never hidden.

## How it works

- **Hook** (`claude_hook.py`): only writes each session's state to a file, so it is fast (~0.1 s per call).
- **Daemon** (`synclight_daemon.py`): merges all session states and drives the LEDs. The hook starts it on demand and it exits by itself when no sessions remain.

## Requirements

- Windows 10 / 11
- Python 3.8+ (no extra packages; it calls the Windows HID API through `ctypes`)
- A SyncLight light connected over USB HID (VID `1A86` / PID `FE07`)

## Install

```bash
git clone https://github.com/kotaooka/claude-synclight-led.git
cd claude-synclight-led
python install.py --takeover
```

- Files are copied to `~/.claude/synclight/` and hooks are added to `~/.claude/settings.json` (the original is saved as `settings.json.bak`).
- Hooks use the full path of the Python that ran the installer, so they work even if `python` is not on PATH.
- Applies to every Claude Code session on the PC (CLI, desktop app Code tab, IDE extensions), starting with newly opened sessions.
- To update, `git pull` and run `python install.py` again.

Uninstall:

```bash
python install.py --uninstall
```

## Living with the SyncLight app

The SyncLight app and this tool both drive the strip, so there are two modes:

| Mode | Behavior |
|---|---|
| `--takeover` (recommended) | Quits SyncLight when Claude starts working, and relaunches it (back to screen sync) 2 minutes after work stops |
| `--no-takeover` (default) | Pauses the LED display while SyncLight is running and warns at session start |

## Configuration

Edit `~/.claude/synclight/config.json` (picked up within 5 seconds).

| Key | Default | Meaning |
|---|---|---|
| `lamps` | `54` | Number of LEDs |
| `takeover` | `false` | Automatic switching described above |
| `done_seconds` | `180` | How long to show green after a response |
| `restore_seconds` | `120` | Delay before handing the strip back to SyncLight |
| `colors` | | RGB for `working` / `waiting` / `done` / `idle` |

## Manual use

```bash
python synclight_led.py "#ff00ff"   # any color (while the daemon is not running)
python examples/rainbow.py          # rainbow demo
```

The daemon logs to `~/.claude/synclight/daemon.log`.

## Protocol

Uses the section-lighting command found by observing SyncLight's traffic:

```
"RB" | length | seq | 0x86 | [first LED, R, G, B, last LED] × n | checksum (sum of all bytes % 256)
```

Each HID write is prefixed with report ID `0x00` and split into 64-byte chunks. LED numbers start at 1.

## Notes

- Unofficial tool, not affiliated with Robobloq.
- Tested only with one 54-LED monitor backlight ([product used](https://ja.aliexpress.com/item/1005009023785106.html)).
- Use at your own risk.

## License

MIT
