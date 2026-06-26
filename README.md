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
3. **フォルダ命名規則の変更**: `YYYY-MM-DD`、階層化された `YYYY/MM/DD`、月ごとの `YYYY/MM`、区切り文字なしの `YYYYMMDD` など、自由な命名規則を選択可能です。
4. **シミュレーション (Dry Run) モード**: 実際にファイルを動かす前に、どのような分類が行われるかを画面上でプレビュー確認できます。
5. **安全な移動（Move）モード**: コピー後にファイルが破損していないかを完全に検証した上で、元のファイルを削除する安全な「ファイル移動」に対応しています。
6. **重複・名前衝突の回避**: コピー先に同名ファイルがある場合、ファイルサイズを比較し、同じものであれば自動スキップ、異なるものであれば `photo_1.jpg` のように自動でリネームして保存します。
7. **並行処理による高速化**: `ThreadPoolExecutor` を用いて、大量の写真コピー/移動処理を並行して高速に実行します。
8. **中断（キャンセル）機能**: 処理中にいつでも安全にタスクを中断できます。
9. **シャットダウン機能**: アプリ画面からローカルサーバープロセスを安全に終了できます。

### システム要件
- macOS (AppleScript 連携によるフォルダ選択ダイアログを使用するため)
- Python 3.8 以上

### セットアップ方法
1. 本リポジトリをクローンまたはダウンロードします。
2. フォルダ内で Python 仮想環境を作成し、必要なパッケージをインストールします。
   ```bash
   python3 -m venv venv
   ./venv/bin/pip install Flask pillow
   ```

### 使い方
1. ローカルサーバーを起動します。
   ```bash
   ./venv/bin/python3 app.py
   ```
2. ブラウザで **[http://127.0.0.1:5001](http://127.0.0.1:5001)** にアクセスします。（ポート `5001` が競合している場合は、自動的に `5002` 以降の空きポートで起動します）
3. 画面の「選択」ボタンをクリックし、ダイアログから「コピー元」および「コピー先」のフォルダを指定します。
4. 処理モード（コピー / 移動）やフォルダ命名規則を選択します。
5. 「シミュレーション」ボタンで事前に確認した後、「整理を実行する」をクリックします。
6. 使用後は、画面右上の「電源マーク」からサーバーを終了してください。

### ディレクトリ構造
```
photo-arranger-app/
├── app.py              # Flask バックエンドサーバーのメインプログラム
├── templates/          # UIテンプレート (HTML)
│   └── index.html
├── static/             # フロントエンドの静的アセット (CSS, JS)
│   ├── style.css
│   └── main.js
├── assets/             # アプリで使用するアイコンアセット類
│   ├── icon_base.png   # アイコン元の高解像度画像
│   ├── icon.icns       # macOS アプリ用アイコン
│   └── icon.ico        # Windows アプリ用アイコン
├── scripts/            # 開発・ビルドユーティリティスクリプト
│   └── convert_icons.py # PNG画像から各種アイコンを自動生成するスクリプト
├── build_app.sh        # macOS用アプリビルドスクリプト (.app生成)
├── build_app.bat       # Windows用アプリビルドスクリプト (.exe生成)
├── README.md
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
3. **Custom Folder Naming Rules**: Choose from various naming formats such as `YYYY-MM-DD`, nested `YYYY/MM/DD`, monthly `YYYY/MM`, or flat `YYYYMMDD`.
4. **Dry Run (Simulation) Mode**: Preview the output folder structure and actions (copy, skip, rename) in the browser before any files are modified.
5. **Safe Move Mode**: Move mode safely verifies file integrity (e.g. file size) after copying before deleting the original files.
6. **Conflict Resolution (Auto-Rename)**: If a filename collision occurs, it compares the file sizes. It skips identical files, and automatically renames different files (e.g., `photo_1.jpg`) to prevent data overwrite.
7. **Multithreaded Performance**: Fast concurrent copying/moving utilizing Python's `ThreadPoolExecutor`.
8. **Cancel Operation**: Stop the operation safely mid-way at any time.
9. **Graceful Shutdown**: Safely terminate the local backend server process directly from the Web UI.

### Requirements
- macOS (leveraging AppleScript integration for native directory dialogs)
- Python 3.8 or higher

### Setup
1. Clone or download this repository.
2. Initialize a Python virtual environment and install the required dependencies:
   ```bash
   python3 -m venv venv
   ./venv/bin/pip install Flask pillow
   ```

### Usage
1. Start the local server:
   ```bash
   ./venv/bin/python3 app.py
   ```
2. Navigate to **[http://127.0.0.1:5001](http://127.0.0.1:5001)** in your browser. (If port `5001` is already in use, the server dynamically binds to the next available port, e.g. `5002`.)
3. Use the "Select" buttons to choose source and destination directories through the macOS native dialogs.
4. Set the processing mode (Copy / Move) and Folder Naming Rule.
5. Optionally click "Simulation" to preview the results, then click "Run Organizer".
6. When finished, shut down the server by clicking the power icon in the top-right corner.

### Directory Structure
```
photo-arranger-app/
├── app.py              # Main Flask backend server program
├── templates/          # UI Templates (HTML)
│   └── index.html
├── static/             # Frontend static assets (CSS, JS)
│   ├── style.css
│   └── main.js
├── assets/             # App icon assets
│   ├── icon_base.png   # Original high-res icon image
│   ├── icon.icns       # macOS app icon
│   └── icon.ico        # Windows app icon
├── scripts/            # Utility development scripts
│   └── convert_icons.py # Automation script to convert PNG to multi-format icons
├── build_app.sh        # macOS standalone build script (generates .app)
├── build_app.bat       # Windows standalone build script (generates .exe)
├── README.md
└── .gitignore
```
