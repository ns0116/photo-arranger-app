#!/bin/bash

# エラーが起きたら処理を中断
set -e

echo "=== Photo Arranger App ビルドスクリプト ==="

# 修正 #10: 仮想環境の存在確認（Windows版 build_app.bat と一貫性を持たせる）
if [ ! -d "venv" ]; then
    echo "[エラー] venv (Python仮想環境) がフォルダ内に見つかりません。"
    echo "先に仮想環境を作成し、依存関係をセットアップしてください。"
    echo "コマンド例: python3 -m venv venv && ./venv/bin/pip install -r requirements.txt"
    exit 1
fi

# 仮想環境が有効か確認し、PyInstallerをインストール
echo "1. 依存ライブラリのインストール..."
./venv/bin/pip install pyinstaller

# PyInstallerでビルド
# --onefile: 1つの実行ファイルにまとめる
# --windowed: バックグラウンドのCUIウィンドウを表示しない（macOSでは.appバンドルが生成される）
# --add-data: テンプレートやCSS/JS静的ファイルをバイナリに同梱する
echo "2. スタンドアローン.appのビルドを開始..."
./venv/bin/pyinstaller --onefile --windowed \
  --icon="assets/icon.icns" \
  --add-data "templates:templates" \
  --add-data "static:static" \
  --name "PhotoArranger" \
  app.py

echo "=== ビルド完了 ==="
echo "プロジェクトの 'dist/' ディレクトリ内に 'PhotoArranger.app' が作成されました。"
echo "Finderで 'dist/' を開き、'PhotoArranger.app' をダブルクリックして起動できます。"
echo "また、この.appファイルをアプリケーションフォルダにコピーして利用することも可能です。"
