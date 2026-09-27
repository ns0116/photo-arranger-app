#!/bin/bash

# エラーが起きたら処理を中断
set -e

# スクリプトがある場所の親ディレクトリ（プロジェクトルート）に移動
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "=== Photo Arranger App ビルドスクリプト (Linux) ==="

# 仮想環境の存在確認
if [ ! -d "venv" ]; then
    echo "[エラー] venv (Python仮想環境) がフォルダ内に見つかりません。"
    echo "先に仮想環境を作成し、依存関係をセットアップしてください。"
    echo "コマンド例: python3 -m venv venv && ./venv/bin/pip install -r requirements.txt"
    exit 1
fi

# 仮想環境が有効か確認し、PyInstallerをインストール
echo "1. 依存ライブラリのインストール..."
./venv/bin/python -m pip install pyinstaller

# PyInstallerでビルド（クロスプラットフォーム対応のPhotoArranger.specを使用）
echo "2. Linuxスタンドアローンバイナリのビルドを開始..."
./venv/bin/python -m PyInstaller PhotoArranger.spec

echo "=== ビルド完了 ==="
echo "プロジェクトの 'dist/' ディレクトリ内に 'PhotoArranger' が作成されました。"
echo "'./dist/PhotoArranger' を実行して起動できます。"
