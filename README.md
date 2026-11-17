# claude-synclight-led

[English](README.en.md)

[Claude Code](https://claude.com/claude-code) の動作状況を、Robobloq の [**SyncLight**](https://quiklight.robobloq.com/sync-lights) 対応 LED テープ（モニター背面ライトなど）に表示します。

| Claude Code の状態 | LED |
|---|---|
| 作業中（プロンプト送信・ツール実行） | 🟠 オレンジがゆっくり明滅 |
| 許可待ち | 🟡 黄の点滅 |
| 応答完了 | 🟢 緑（3分間） |
| 待機中（セッションあり） | 🔵 うす青 |
| セッションなし | 消灯 |

複数のセッションを同時に動かしているときは **許可待ち ＞ 作業中 ＞ 完了 ＞ 待機** の優先順で表示するので、どれかが許可を待っていれば見逃しません。

## しくみ

- **フック**（`claude_hook.py`）：セッションごとの状態をファイルに書くだけなので軽量です（1回あたり約0.1秒）。
- **常駐プログラム**（`synclight_daemon.py`）：全セッションの状態をまとめて LED を描画します。必要なときにフックから自動で起動し、セッションがなくなると自動で終了します。

## 必要なもの

- Windows 10 / 11
- Python 3.8 以上（追加パッケージ不要。`ctypes` で Windows の HID API を直接呼びます）
- USB HID 接続の SyncLight 対応ライト（VID `1A86` / PID `FE07`）

## インストール

```bash
git clone https://github.com/kotaooka/claude-synclight-led.git
cd claude-synclight-led
python install.py --takeover
```

- ファイルは `~/.claude/synclight/` にコピーされ、`~/.claude/settings.json` にフックが追加されます（元のファイルは `settings.json.bak` に保存）。
- フックはインストールに使った Python のフルパスで登録されるので、`python` コマンドが PATH にない環境でも動きます。
- このPCで動くすべての Claude Code セッション（CLI・デスクトップアプリの Code タブ・IDE 拡張）に適用されます。新しく開いたセッションから有効になります。
- クラウドで動くセッション（claude.ai/code のクラウド環境など）は、このPCのUSBに届かないため対象外です。
- 更新するときは `git pull` してから、もう一度 `python install.py` を実行してください。

アンインストール:

```bash
python install.py --uninstall
```

## SyncLight アプリとの共存

LED は SyncLight アプリと取り合いになるため、次の 2 つのモードがあります。

| モード | 動き |
|---|---|
| `--takeover`（おすすめ） | Claude が作業を始めると SyncLight を自動で終了し、完了（緑）の表示が終わるとタスクトレイに起動し直して画面同期に戻します |
| `--no-takeover`（初期値） | SyncLight が起動している間は LED 表示を止めます。セッション開始時に警告を出します |

## 設定

`~/.claude/synclight/config.json` を編集します（5秒以内に反映されます）。

| キー | 初期値 | 内容 |
|---|---|---|
| `lamps` | `54` | LED の灯数 |
| `takeover` | `false` | 上記の自動切り替え |
| `done_seconds` | `180` | 完了（緑）を表示する秒数 |
| `colors` | | `working` / `waiting` / `done` / `idle` の RGB |
| `debug` | `false` | `true` にすると、フックが呼ばれた時刻を `hook.log` に記録 |

## 手動で使う

```bash
python synclight_led.py "#ff00ff"   # 任意の色（常駐プログラムが止まっているときに）
python examples/rainbow.py          # 虹のデモ
```

動作ログは `~/.claude/synclight/daemon.log` に出ます。

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
