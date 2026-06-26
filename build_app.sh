#!/bin/bash

# エラーが起きたら処理を中断
set -e

echo "=== Photo Arranger App ビルドスクリプト ==="

# 仮想環境が有効か確認し、PyInstallerをインストール
echo "1. 依存ライブラリのインストール..."
./venv/bin/pip install pyinstaller

# PyInstallerでビルド
# --onefile: 1つの実行ファイルにまとめる
# --windowed: バックグラウンドのCUIウィンドウを表示しない（macOSでは.appバンドルが生成される）
# --add-data: テンプレートやCSS/JS静的ファイルをバイナリに同梱する
echo "2. スタンドアローン.appのビルドを開始..."
./venv/bin/pyinstaller --onefile --windowed \
  --icon="icon.icns" \
  --add-data "templates:templates" \
  --add-data "static:static" \
  --name "PhotoArranger" \
  app.py

echo "=== ビルド完了 ==="
echo "プロジェクトの 'dist/' ディレクトリ内に 'PhotoArranger.app' が作成されました。"
echo "Finderで 'dist/' を開き、'PhotoArranger.app' をダブルクリックして起動できます。"
echo "また、この.appファイルをアプリケーションフォルダにコピーして利用することも可能です。"
