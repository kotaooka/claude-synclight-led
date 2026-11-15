# claude-synclight-led

[Claude Code](https://claude.com/claude-code) の動作状況を、Robobloq の [**SyncLight**](https://quiklight.robobloq.com/sync-lights) 対応 LED テープ（モニター背面ライトなど）に表示します。

| Claude Code の状態 | フック | LED |
|---|---|---|
| 作業中（プロンプト送信・ツール実行） | `UserPromptSubmit` / `PostToolUse` | 🟠 オレンジ |
| 許可・入力待ち | `Notification` | 🟡 黄 |
| 応答完了 | `Stop` | 🟢 緑 |
| セッション終了 | `SessionEnd` | 🔵 うす青 |

## 必要なもの

- Windows 10 / 11
- Python 3.8 以上（追加パッケージ不要。`ctypes` で Windows の HID API を直接呼びます）
- USB HID 接続の SyncLight 対応ライト（VID `1A86` / PID `FE07`）

> **SyncLight アプリは終了してください。** 起動中は画面同期などの色で上書きされます。

## インストール

```bash
git clone https://github.com/kotaooka/claude-synclight-led.git
cd claude-synclight-led
python install.py
```

`synclight_led.py` が `~/.claude/hooks/` にコピーされ、`~/.claude/settings.json` にフックが追加されます（元のファイルは `settings.json.bak` に保存）。
このPCで動くすべての Claude Code セッション（CLI・デスクトップアプリの Code タブ・IDE 拡張）に適用されます。

アンインストール:

```bash
python install.py --uninstall
```

## 手動で使う

```bash
python synclight_led.py working     # working / waiting / done / idle / off
python synclight_led.py "#ff00ff"   # 任意の色
python examples/rainbow.py          # 虹のデモ
```

LED の灯数が 54 でない場合は、環境変数 `SYNCLIGHT_LAMPS` で指定してください。
色は `synclight_led.py` 冒頭の `STATES` で変更できます。

## プロトコル

SyncLight の通信を調べて分かった区間点灯コマンドを使っています。

```
"RB" | 全長 | 連番 | 0x86 | [開始LED, R, G, B, 終了LED] × n | チェックサム(全バイト合計 % 256)
```

HID には report ID `0x00` を前置し、64 バイトずつ書き込みます。LED 番号は 1 始まりです。

## 注意

- 非公式ツールです。Robobloq とは関係ありません。
- 動作確認は 54 灯のモニター背面ライト 1 台のみです（[使用した製品](https://ja.aliexpress.com/item/1005009023785106.html)）。
- 使用は自己責任でお願いします。

## License

MIT
