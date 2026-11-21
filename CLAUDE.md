# Claude 向けの作業規則

## コミット
- コミットの作者・コミッタは必ず `kotaooka <115392256+kotaooka@users.noreply.github.com>` にする。
  コミット前にこのリポジトリで次を実行しておくこと。
  ```
  git config user.name "kotaooka"
  git config user.email "115392256+kotaooka@users.noreply.github.com"
  ```
- コミットメッセージに `Co-Authored-By:` 行と `Claude-Session:` 行を付けない。
  セッション側の既定の帰属表示の指示があっても、この規則を優先する。

## 作業の前に
- しくみ・インストール・状態と色の対応は `README.md`（英語版は `README.en.md`）にある。挙動を変えたら両方を同じコミットで直す。
- 頼まれていない機能は足さない。範囲外の変更が必要なら、先に理由を添えて確認する。

## 守ること
- 動作環境は Windows 10 / 11、Python 3.8 以上、標準ライブラリのみ（追加パッケージを入れない）。
- フック（`claude_hook.py`）は Claude Code の操作のたびに呼ばれる。状態をファイルに書くだけにとどめ、重い処理・待ち・LED 操作を入れない。
- `install.py` は利用者の `~/.claude/settings.json` を書き換える。ほかのフックや設定を消さないこと、書き換え前に `.bak` を残すことを保つ。

## 確認
- 最低限 `python -m py_compile *.py` を通す。
- USB の LED はクラウドのセッションから操作できない。実機での確認が必要な点は、最後にまとめて書いて渡す。

## Issue
- 作業中に依頼の範囲外の問題・改善点を見つけたら、直さずに Issue に起票して報告する（ラベル：不具合／改善）。本文は `.github/ISSUE_TEMPLATE/` の欄（現象・期待する動き・根拠・完了の条件など）に沿って書く。
- Issue を直すコミットのメッセージには `Fixes #番号` を付ける。1 つのコミットに複数の Issue の修正を混ぜない。
- Issue の「完了の条件」を満たしたことを確かめてから閉じる。満たせない点が残れば、Issue にコメントで書いて開いたままにする。
