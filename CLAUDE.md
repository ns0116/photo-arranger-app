# photo-arranger-app — Claude Context

複数フォルダの写真/動画をEXIF撮影日時（無ければファイル更新日時にフォールバック）で解析し、日付別フォルダへ自動分類するFlaskベースのローカルWebアプリ。

## スタック

- バックエンド: Python 3.8+ / Flask（`app.py`がapplication factory、`config.py`に設定・拡張子定義）
- フロント: `templates/` + `static/`（多言語対応 i18n）
- 重複管理: SQLite（セッション間の重複ファイル検知）
- パッケージング: PyInstaller（`PhotoArranger.spec`、`build_app.bat`/`build_app.sh`）

## 実行

```bash
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
./venv/bin/python3 app.py
```

## テスト・Lint

```bash
pytest tests/
pre-commit run --all-files   # black / isort / flake8
```

## 注意点

- **フォルダ選択ダイアログはOSネイティブ実装**（macOSはAppleScript連携）に依存しており、**ヘッドレスなクラウドサンドボックス環境ではGUI操作を伴う手動確認ができない**。コードレビュー・単体テスト・lintはクラウドでも問題なく実行可能。
- 動画ファイル（`.mp4`等）はPillowでEXIFを読めないため、常にファイル更新日時にフォールバックする（`config.py`のコメント参照）。
- `docs/`配下はAIエージェント向けの内部作業ドキュメントのため`.gitignore`対象（このリポジトリでは非公開のまま）。
