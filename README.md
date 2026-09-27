# Photo Arranger

[日本語](#日本語) | [English](#english)

---

## 日本語

### 概要
**Photo Arranger** は、複数のフォルダから写真を自動で収集し、ファイルの更新日時（mtime）や写真ファイルに埋め込まれている **EXIF 撮影日時** を自動解析して、日付別のフォルダ（例: `YYYY-MM-DD`）へきれいに分類・整理する Flask ベースの Web アプリケーションです。

もともとシェルスクリプト `arrange_photos_yyyymmdd.sh` で行っていた処理をベースに、ガラスモフィズムを取り入れたプレミアムな UI と高度な整理機能を備えたローカルツールとして進化させました。

### 主な機能
1. **EXIF 撮影日時の優先利用**: 写真ファイルに埋め込まれている撮影日時情報を最優先して整理します。EXIF 情報のないファイルや画像以外のファイルは、ファイルの更新日時にフォールバックします。
2. **コピー元（入力）ディレクトリの複数指定**: 異なる場所にある複数のフォルダを一括で対象に指定できます。
3. **柔軟なカスタム命名テンプレート**: `YYYY-MM-DD` などの固定規則に加え、`{YYYY}/{MM}/{YYYY}-{MM}-{DD}_{filename}{ext}` のように、プレースホルダーを用いて日付階層とファイル名を自由に組み合わせ可能です。
4. **シミュレーション (Dry Run) モード**: 実際にファイルを動かす前に、どのような分類が行われるかを画面上でプレビュー確認できます。
5. **安全な移動（Move）モード**: コピー後にファイルが破損していないかを完全に検証した上で、元のファイルを削除する安全な「ファイル移動」に対応しています。
6. **SQLiteによるセッション間重複管理**: 整理された写真情報（サイズ、更新日時、ハッシュ値）をローカルDBに記憶し、別フォルダの重複ファイルを高速に自動検知してスキップします。
7. **詳細フィルタ設定**: フロント画面から対象のファイル拡張子（JPG, PNG, WebP等）や特定の撮影・更新日付範囲を指定して整理対象を絞り込めます。
8. **整理の取り消し（Undo）機能**: 直前に実行した整理処理を1クリックで完全に取り消し（コピーの削除・移動の差し戻し）、自動生成された空フォルダも自動クリーンアップします。
9. **多言語対応 (i18n)**: 日本語と英語の表示切り替えに対応しています。
10. **並行処理による高速化**: `ThreadPoolExecutor` を用いて、大量の写真コピー/移動処理を並行して高速に実行します。
11. **中断（キャンセル）機能**: 処理中にいつでも安全にタスクを中断できます。
12. **シャットダウン機能**: アプリ画面からローカルサーバープロセスを安全に終了できます。

### システム要件
- macOS (AppleScript 連携によるフォルダ選択ダイアログ)
- Windows (PowerShell 連携によるフォルダ選択ダイアログ)
- Linux (`zenity`、`kdialog`、または `python3-tk` 連携によるフォルダ選択ダイアログ)
- Python 3.8 以上

### セットアップ方法
1. 本リポジトリをクローンまたはダウンロードします。
2. フォルダ内で Python 仮想環境を作成し、必要なパッケージをインストールします。
   ```bash
   python3 -m venv venv
   ./venv/bin/pip install -r requirements.txt
   ```

### 使い方
1. ローカルサーバーを起動します。
   ```bash
   ./venv/bin/python3 app.py
   ```
2. ブラウザで **[http://127.0.0.1:5001](http://127.0.0.1:5001)** にアクセスします。（ポート `5001` が競合している場合は、自動的に `5002` 以降の空きポートで起動します）
3. 画面の「選択」ボタンをクリックし、ダイアログから「コピー元」および「コピー先」のフォルダを指定します。
   - ※お試し用に `tests/` フォルダの中にダミーの写真フォルダ（`test_src1`, `test_src2` 等）を用意しています。
4. 処理モード（コピー / 移動）やフォルダ命名規則を選択します。
5. 「シミュレーション」ボタンで事前に確認した後、「整理を実行する」をクリックします。
6. 使用後は、画面右上の「電源マーク」からサーバーを終了してください。

### パッケージ化とビルド（デスクトップアプリ化）
本アプリは `PyInstaller` を使用して、Pythonのインストール不要なスタンドアローン形式（macOSの `.app` / Windowsの `.exe` / Linuxのスタンドアローン実行バイナリ）にパッケージ化できます。

> **注意**: アプリのビルドには各OSの実機環境（またはGUI環境）が必要です。クラウドサンドボックス等のヘッドレス環境ではスタンドアローンアプリのビルドや動作検証は行えません。

1. **macOSでビルドする場合**:
   ```bash
   ./scripts/build_app.sh
   # または make build-mac
   ```
   ビルドが成功すると、`dist/` フォルダ内に `PhotoArranger.app` が生成されます。ダブルクリックして起動可能です。

2. **Windowsでビルドする場合**:
   コマンドプロンプトで以下を実行するか、`scripts\build_app.bat` をダブルクリックして実行します。
   ```cmd
   scripts\build_app.bat
   ```
   ビルドが成功すると、`dist/` フォルダ内に `PhotoArranger.exe` が生成されます。

3. **Linuxでビルドする場合**:
   ```bash
   ./scripts/build_app_linux.sh
   # または make build-linux
   ```
   ビルドが成功すると、`dist/` フォルダ内に実行可能バイナリ `PhotoArranger` が生成されます。

### ディレクトリ構造
```
photo-arranger-app/
├── app.py              # Flask バックエンドサーバーのメインプログラム
├── config.py           # アプリの設定値管理クラス（ポート・スレッド・画像拡張子など）
├── PhotoArranger.spec  # PyInstaller クロスプラットフォームビルド設定
├── Makefile            # 開発・テスト・ビルド・クリーンアップ用タスク定義
├── pytest.ini          # pytest 設定ファイル
├── requirements.txt    # Python 依存ライブラリ一覧
├── templates/          # UIテンプレート (HTML)
│   └── index.html
├── static/             # フロントエンドの静的アセット (CSS, JS)
│   ├── style.css
│   └── main.js
├── routes/             # APIエンドポイント・ページルーティング定義
│   ├── __init__.py     # ルートの初期化とBlueprintの登録
│   ├── arrange.py      # /api/arrange, /api/cancel
│   ├── directories.py  # /api/select-dir (フォルダ選択)
│   ├── report.py       # /api/report (整理履歴・統計)
│   ├── system.py       # /, /api/shutdown, /api/undo (Undo・シャットダウン)
│   ├── thumbnail.py    # /api/thumbnail (画像サムネイル配信)
│   └── watcher.py      # /api/watcher/* (フォルダ監視制御)
├── services/           # ビジネスロジック層
│   ├── __init__.py
│   ├── cities_data.py  # 軽量オフライン都市・撮影地データベース
│   ├── db_service.py   # SQLiteデータベースによる重複・履歴管理
│   ├── file_service.py # 安全なファイル移動・コピー・衝突回避ロジック
│   ├── geocoding_service.py # オフライン逆ジオコーディング探索ロジック
│   ├── photo_service.py # 写真解析・整理並行処理の実行パイプライン
│   ├── rule_service.py # 条件分岐ルールの評価と振り分け先解決
│   └── watcher_service.py # バックグラウンドフォルダ監視・自動整理デーモン
├── utils/              # 共通ユーティリティ層
│   ├── __init__.py
│   ├── date_utils.py   # EXIF情報の抽出および日付・GPS解析
│   ├── i18n.py         # 多言語対応の翻訳カタログとヘルパー
│   ├── phash_utils.py  # 知覚ハッシュ(dHash)と類似重複検出
│   └── platform_utils.py # OSネイティブのフォルダ選択ダイアログ呼び出し
├── assets/             # アプリで使用するアイコンアセット類
│   ├── icon_base.png   # アイコン元の高解像度画像
│   ├── icon.icns       # macOS アプリ用アイコン
│   └── icon.ico        # Windows アプリ用アイコン
├── docs/               # プロジェクト仕様・監査ドキュメント
│   └── AUDIT.md        # セキュリティ・品質監査レポート
├── scripts/            # 開発・ビルドユーティリティスクリプト
│   ├── build_app.sh    # macOS用アプリビルドスクリプト (.app生成)
│   ├── build_app.bat   # Windows用アプリビルドスクリプト (.exe生成)
│   ├── build_app_linux.sh # Linux用アプリビルドスクリプト (実行バイナリ生成)
│   └── convert_icons.py # PNG画像から各種アイコンを自動生成するスクリプト
├── tests/              # 各モジュールの単体・結合テストスイート (127テスト)
├── README.md
├── CLAUDE.md
└── .gitignore
```

---

## English

### Overview
**Photo Arranger** is a Flask-based web application that automatically collects photos from multiple source directories, analyzes their file modification time (mtime) and embedded **EXIF date taken**, and organizes them neatly into date-based folders (e.g., `YYYY-MM-DD`).

Evolved from a basic shell script `arrange_photos_yyyymmdd.sh`, this tool now offers a premium glassmorphic UI and advanced sorting capabilities.

### Key Features
1. **EXIF Date Taken Priority**: Prioritizes embedded EXIF data to determine the photo's original date taken. Automatically falls back to file modification time (mtime) for non-image files or images without EXIF.
2. **Multiple Source Directories**: Scan and consolidate files from multiple different directories at once.
3. **Flexible Custom Naming Templates**: In addition to standard formats, define flexible directory paths and filenames using tokens like `{YYYY}`, `{MM}`, `{DD}`, `{filename}`, and `{ext}` (e.g. `{YYYY}/{MM}/{YYYY}-{MM}-{DD}_{filename}{ext}`).
4. **Dry Run (Simulation) Mode**: Preview the output folder structure and actions (copy, skip, rename) in the browser before any files are modified.
5. **Safe Move Mode**: Move mode safely verifies file integrity (e.g. file size) after copying before deleting the original files.
6. **SQLite Cross-Session Duplicate Check**: Stores processed files' metadata (size, mtime, SHA-256) in a local database to detect and skip duplicates across runs.
7. **Advanced Scanning Filters**: Filter target files by extensions (JPG, PNG, WebP, etc.) and specific date ranges.
8. **One-Click Undo (Rollback)**: Easily revert the last copy/move session (deletes copies or moves files back to sources) and clean up empty directories.
9. **Multi-language Support (i18n)**: Seamless language toggling between Japanese and English.
10. **Multithreaded Performance**: Fast concurrent copying/moving utilizing Python's `ThreadPoolExecutor`.
11. **Cancel Operation**: Stop the operation safely mid-way at any time.
12. **Graceful Shutdown**: Safely terminate the local backend server process directly from the Web UI.

### Requirements
- macOS (leveraging AppleScript integration for native directory dialogs)
- Windows (leveraging PowerShell integration for native directory dialogs)
- Linux (leveraging `zenity`, `kdialog`, or `python3-tk` for directory dialogs)
- Python 3.8 or higher

### Setup
1. Clone or download this repository.
2. Initialize a Python virtual environment and install the required dependencies:
   ```bash
   python3 -m venv venv
   ./venv/bin/pip install -r requirements.txt
   ```

### Usage
1. Start the local server:
   ```bash
   ./venv/bin/python3 app.py
   ```
2. Navigate to **[http://127.0.0.1:5001](http://127.0.0.1:5001)** in your browser. (If port `5001` is already in use, the server dynamically binds to the next available port, e.g. `5002`.)
3. Use the "Select" buttons to choose source and destination directories through the native OS dialogs.
   - ※ For quick testing, you can use the dummy photo directories (`test_src1`, `test_src2` etc.) provided under the `tests/` folder.
4. Set the processing mode (Copy / Move) and Folder Naming Rule.
5. Optionally click "Simulation" to preview the results, then click "Run Organizer".
6. When finished, shut down the server by clicking the power icon in the top-right corner.

### Packaging and Building (Standalone App)
You can bundle this application into a standalone desktop application (macOS `.app`, Windows `.exe`, or Linux executable binary) using `PyInstaller`.

> **Note**: Building the application requires physical hardware or a desktop GUI environment on each target OS. Standalone apps cannot be built or validated in headless cloud sandboxes or containers without GUI support.

1. **Building on macOS**:
   Run the build script in your terminal:
   ```bash
   ./scripts/build_app.sh
   # or: make build-mac
   ```
   After a successful build, `PhotoArranger.app` will be created in the `dist/` folder. You can launch it by double-clicking.

2. **Building on Windows**:
   Double-click `scripts\build_app.bat` or run it from Command Prompt:
   ```cmd
   scripts\build_app.bat
   ```
   After a successful build, `PhotoArranger.exe` will be generated in the `dist/` folder.

3. **Building on Linux**:
   ```bash
   ./scripts/build_app_linux.sh
   # or: make build-linux
   ```
   After a successful build, the executable `PhotoArranger` binary will be generated in the `dist/` folder.

### Directory Structure
```
photo-arranger-app/
├── app.py              # Main Flask backend server program
├── config.py           # Configuration management (ports, threads, extensions)
├── PhotoArranger.spec  # Cross-platform PyInstaller packaging specification
├── Makefile            # Developer task runner (run, test, lint, format, clean, build)
├── pytest.ini          # Pytest configuration file
├── requirements.txt    # Python dependencies list
├── templates/          # UI templates (HTML)
│   └── index.html
├── static/             # Frontend static assets (CSS, JS)
│   ├── style.css
│   └── main.js
├── routes/             # API endpoints and routing definitions
│   ├── __init__.py     # Routing initialization and blueprint registration
│   ├── arrange.py      # /api/arrange, /api/cancel
│   ├── directories.py  # /api/select-dir (directory picker)
│   ├── report.py       # /api/report (history & statistics)
│   ├── system.py       # /, /api/shutdown, /api/undo (rollbacks & shutdowns)
│   ├── thumbnail.py    # /api/thumbnail (image thumbnail server)
│   └── watcher.py      # /api/watcher/* (folder monitoring daemon controls)
├── services/           # Business logic layer
│   ├── __init__.py
│   ├── cities_data.py  # Lightweight offline city & sightseeing database
│   ├── db_service.py   # SQLite database for duplication and session history
│   ├── file_service.py # Safe move/copy operations and conflict resolutions
│   ├── geocoding_service.py # Offline reverse geocoding search logic
│   ├── photo_service.py # Photo parsing and organization workflow pipelines
│   ├── rule_service.py # Conditional rules evaluation and target routing
│   └── watcher_service.py # Background folder watcher & auto-arranging daemon
├── utils/              # Common utilities
│   ├── __init__.py
│   ├── date_utils.py   # EXIF tags, GPS coordinates, and date extraction
│   ├── i18n.py         # Bilingual translation logs catalog
│   ├── phash_utils.py  # Perceptual hash (dHash) & near-duplicate detection
│   └── platform_utils.py # Native OS folder dialog invoker
├── assets/             # App icon assets
│   ├── icon_base.png   # Original high-res icon image
│   ├── icon.icns       # macOS app icon
│   └── icon.ico        # Windows app icon
├── docs/               # Project documentation & audit reports
│   └── AUDIT.md        # Security & quality audit report
├── scripts/            # Utility development & build scripts
│   ├── build_app.sh    # macOS standalone build script (generates .app)
│   ├── build_app.bat   # Windows standalone build script (generates .exe)
│   ├── build_app_linux.sh # Linux standalone build script (generates binary)
│   └── convert_icons.py # Automation script to convert PNG to multi-format icons
├── tests/              # Unit and integration test suite (127 tests)
├── README.md
├── CLAUDE.md
└── .gitignore
```
