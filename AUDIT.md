# AUDIT.md — photo-arranger-app

作成日: 2026-09-24
更新日: 2026-09-24（対応状況追記）

## 対応状況（2026-09-24）

- ✅ **対応済み**: 監査当時「対象ファイルなし」だった `CLAUDE.md` を新規作成し、Git追跡対象とした（`.gitignore:26-28`の`CLAUDE.md`/`.claude/`丸ごと除外を解除し、`.claude/settings.local.json`のみを除外するよう変更）。内容はスタック・実行/テスト/lintコマンド・「フォルダ選択ダイアログはWindows/macOS専用でクラウドサンドボックスでは動かない」という制約を含む。
- 未対応: `.claude/settings.local.json`内の`orca`関連permissionの要否確認、アイコン生成スクリプト・ビルドスクリプトへのOS依存注記などは今回のスコープ外（下記「改善提案」参照、実装は未着手）。
- 備考: 下記の監査本文は「CLAUDE.mdが存在しなかった時点」の記録として原文のまま残す。

> 本ファイルは読み取り専用調査の成果物です（上記対応状況の追記を除く）。このファイル以外、リポジトリ内の他ファイルは一切変更していません。

## プロンプト監査結果

対象ファイルなし。

調査範囲（`CLAUDE.md`, `.claude/agents/*`, `.claude/skills/*`, `.claude/commands/*`, `.claude/rules/*`）はいずれもプロジェクト内に存在しませんでした。

補足事項:

- `.claude/settings.local.json` のみ存在します（今回の監査対象リストには含まれないファイルですが、関連情報として記載）。中身は以下の4行の許可リストのみで、指示文やコンテキストは含まれていません。
  ```json
  {
    "permissions": {
      "allow": [
        "Bash(git fetch *)",
        "Bash(echo \"exit:$?\")",
        "Bash(git *)",
        "Bash(command -v orca)",
        "Bash(orca status *)"
      ]
    }
  }
  ```
  この中の `orca` 関連の許可（`command -v orca`, `orca status *`）は、他プロジェクト（garryu-studio 等）で使われている `orca` CLI を前提とした設定に見えます。本プロジェクトのコード内に `orca` への依存は見当たらず、クラウドサンドボックスに `orca` が存在しなくても実害はありません（コマンドが失敗するだけ）が、テンプレートのコピー跡である可能性があり、要否の見直しは検討の余地があります。
- `.gitignore`（26–28行目）で `CLAUDE.md` と `.claude/` が明示的に除外設定されています。
  ```
  # Claude Code project context (private, not for public repo)
  CLAUDE.md
  .claude/
  ```
  これは「プロジェクト固有のClaude設定を公開リポジトリにコミットしない」という意図的な設計です。裏を返すと、**ローカルで将来 `CLAUDE.md` や `.claude/agents` 等を作成しても、`git clone` ベースで起動するクラウドサンドボックスには一切渡りません**。現状は元々それらのファイルが存在しないため矛盾は生じていませんが、今後ローカルでプロジェクト固有のガードレール（例: 「破壊的なファイル移動操作は確認を取る」といった本アプリ特有の注意点）を `CLAUDE.md` に書いても、クラウド側のセッションはその内容を全く知らない状態でコードに触れることになります。クラウドセッションでも同じ振る舞いをさせたい場合は、`.gitignore` からの除外方針自体を見直すか、機密性のない一般的な開発ルールだけを別途コミット対象のファイル（例: `CONTRIBUTING.md` や `.claude/rules/` のうち非機密なもの）に分離することを検討する余地があります。
- `docs/` も `.gitignore`（31行目）で除外されていますが、ディスク上にも実体は存在しませんでした（調査時点）。

## ローカル依存リスト

このプロジェクトはコード上に `D:\`, `C:\Users\`, `/mnt/`, NASのUNCパス(`\\...`)のようなハードコードされた絶対パスは見つかりませんでした。写真の保存先・整理先パスはすべて実行時にユーザーがOSネイティブのフォルダ選択ダイアログで指定する設計（`routes/directories.py`）になっており、その点は健全です。

一方で、**アプリの設計そのものがローカルのデスクトップGUI環境（Windows/macOS）を前提**にしており、クラウドの隔離サンドボックス（GUIなしのLinuxコンテナ）では以下の点が動作しません。

1. **ネイティブフォルダ選択ダイアログがWindows/macOS限定**
   - `utils/platform_utils.py:15-34` — macOSは `osascript` (AppleScript) 経由でダイアログを表示。
   - `utils/platform_utils.py:36-58` — Windowsは `powershell` + `System.Windows.Forms.FolderBrowserDialog` を `subprocess` 起動して表示。
   - `utils/platform_utils.py:60-61` — それ以外のOS（Linux含む＝クラウドサンドボックス）では `NotImplementedError` を送出。
   - 呼び出し元 `routes/directories.py:19-20` はこれを捕捉して400エラー(`"未対応のOSです。手動でパスを入力してください。"`)を返すため、アプリ全体がクラッシュすることはありませんが、**「フォルダを選択」という中核機能がクラウドサンドボックス上では実質使用不可**です。
   - `README.md:28-31`, `README.md:131-134` の「システム要件」にも明記の通り、対応OSはmacOS/Windowsのみです。

2. **サーバーがlocalhostのみにバインドし、非localhostリクエストを拒否する設計**
   - `app.py:64` — `app.run(host="127.0.0.1", ...)` でループバックにのみバインド。
   - `routes/system.py:10-13` — `_require_localhost()` が `request.remote_addr` を `127.0.0.1`/`::1` 以外は403で拒否（`/api/shutdown`, `/api/undo` に適用）。
   - `routes/directories.py:14`, `routes/thumbnail.py:49` — 同様に `/api/select-dir`, `/api/thumbnail` にも適用。
   - これは意図的なセキュリティ設計（外部からの任意ファイル操作を防ぐ）であり「バグ」ではありませんが、クラウドサンドボックスからポートフォワード/トンネル経由でアプリの動作をブラウザで目視確認しようとした場合、リクエスト元IPがループバックと一致せず403で弾かれる可能性が高い点は留意が必要です。

3. **アイコン生成スクリプトがmacOS専用CLIに依存**
   - `scripts/convert_icons.py:46` — `sips`（macOS標準の画像変換コマンド）を `subprocess.run` で呼び出し。
   - `scripts/convert_icons.py:62` — `iconutil`（macOS専用、`.iconset`→`.icns`変換）を呼び出し。
   - どちらもWindowsやLinux（クラウドサンドボックス含む）には存在しないため、このスクリプトはmacOS以外では実行できません。

4. **デスクトップアプリ化ビルドスクリプトがOS別・GUI環境前提**
   - `build_app.sh` — macOS上でのみ `PyInstaller --windowed` により `.app` を生成（`--icon="assets/icon.icns"` 等）。
   - `build_app.bat` — Windows上でのみ `PyInstaller --windowed` により `.exe` を生成。
   - いずれもクラウドのLinuxサンドボックスでは実行不可（対象OS不一致、および `--windowed` はヘッドレス環境と相性が悪い）。

5. **`.claude/settings.local.json` の `orca` CLI依存**
   - `.claude/settings.local.json:7-8` — `command -v orca`, `orca status *` の許可設定。`orca` はローカル環境（あるいは他プロジェクト）で使われているCLIツールで、クラウドサンドボックスにインストールされている保証はありません。失敗しても許可リストの無駄エントリになるだけで実害はほぼありませんが、参考情報として記載します。

### クラウドサンドボックスでも問題なく動く部分

- `.github/workflows/ci.yml` はすでに `ubuntu-latest` 上で `pytest`, `black`, `isort`, `flake8` を実行しており、CIグリーンの実績がある通り、**コード編集・単体テスト・lintの実行はクラウドサンドボックス（Linux）でも問題なく動作します**。
- `tests/conftest.py:9-12` はログ/DB出力先をユーザーホームディレクトリではなく `tests/../.pytest_cache/logs` 配下に上書きしており、テスト実行がホーム環境に依存しない設計になっています。
- `tests/test_app.py:14-27` では `select_dir_dialog` を `unittest.mock.patch` でモック化しており、OSネイティブダイアログの実体を呼ばずにルートのロジックだけをテストできる構成になっています。
- ソースコード中に見つかったNASのUNCパスやハードコードされたドライブレター、外部プライベートIP・自宅サーバーへの参照は一件もありませんでした。

## 改善提案（優先度付き）

### 高
- ✅ **対応済み** ~~クラウドサンドボックスでの制約をドキュメント化する~~ / ~~プロジェクト用 `CLAUDE.md` の新規作成を推奨~~: `CLAUDE.md`を新規作成しGit追跡対象にした。スタック・実行/テスト/lintコマンド・「フォルダ選択ダイアログはWindows/macOS専用でクラウドサンドボックスでは動かない」旨を記載済み（2026-09-24）。アーキテクチャの詳細（Blueprint構成・`_require_localhost`保護方針等）までは今回は書き切れておらず、必要になれば追記の余地あり。

### 中
- ✅ **対応済み** ~~`.gitignore` による `CLAUDE.md`/`.claude/` 除外方針の再検討~~: `CLAUDE.md`は追跡対象化。`.claude/`は`settings.local.json`のみ除外する方式に変更した（2026-09-24）。
- **`.claude/settings.local.json` の `orca` 関連permissionの要否確認**: 未対応（本人に要確認、今回のスコープ外）。

### 低
- **`scripts/convert_icons.py` にOS依存の注記を追加**: `sips`/`iconutil` はmacOS専用である旨をスクリプト冒頭のコメントに明記し、他OS・クラウド環境での実行不可を明確化する（アイコン生成は開発時の一度きりの作業であるため優先度は低い）。
- **ビルドスクリプトへの一言注記**: `build_app.sh`/`build_app.bat` の実行にはそれぞれmacOS/Windowsの実機（またはGUI付き環境）が必要であり、クラウドサンドボックスではスタンドアローンアプリのビルド・検証ができない旨をREADMEに一言添えると親切。
