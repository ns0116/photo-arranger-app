@echo off
chcp 65001 > nul
echo ==================================================
echo Photo Arranger App ビルドスクリプト (Windows用)
echo ==================================================

:: venvの存在確認
if not exist "venv" (
    echo [エラー] venv (Python仮想環境) がフォルダ内に見つかりません。
    echo 先に仮想環境を作成し、依存関係をセットアップしてください。
    echo コマンド例: python -m venv venv
    pause
    exit /b 1
)

echo 1. 依存ライブラリ (PyInstaller, pillow, Flask) のインストール/更新...
call .\venv\Scripts\pip.exe install pyinstaller pillow Flask

echo 2. スタンドアローン.exe のビルドを開始...
:: Windows用のPyInstallerでは --add-data の区切り文字にセミコロン (;) を使用します
call .\venv\Scripts\pyinstaller.exe --onefile --windowed ^
  --icon="assets\icon.ico" ^
  --add-data "templates;templates" ^
  --add-data "static;static" ^
  --name "PhotoArranger" ^
  app.py

echo ==================================================
echo ビルドが完了しました。
echo 'dist' フォルダ内に 'PhotoArranger.exe' が生成されています。
echo ==================================================
pause
