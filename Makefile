.PHONY: help run test lint format clean build-mac build-linux build-win

help:
	@echo "Photo Arranger App - 開発コマンド一覧"
	@echo "  make run         - アプリケーションを起動 (http://127.0.0.1:5000)"
	@echo "  make test        - pytestで全テストを実行"
	@echo "  make lint        - black, isort, flake8 でコード検証"
	@echo "  make format      - black, isort でコードを自動整形"
	@echo "  make clean       - ビルド生成物・キャッシュ・一時ファイルを一括削除"
	@echo "  make build-mac   - macOS用スタンドアローンアプリ (.app) をビルド"
	@echo "  make build-linux - Linux用スタンドアローンバイナリをビルド"

run:
	./venv/bin/python app.py

test:
	./venv/bin/pytest tests/

lint:
	./venv/bin/black --check .
	./venv/bin/isort --check-only --diff --profile black .
	./venv/bin/flake8 . --count --select=E9,F63,F7,F82 --exclude=venv,.venv,build,dist

format:
	./venv/bin/black .
	./venv/bin/isort --profile black .
	./venv/bin/flake8 . --count --select=E9,F63,F7,F82 --exclude=venv,.venv,build,dist

clean:
	rm -rf build dist .coverage htmlcov .pytest_cache
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -delete
	find . -name ".DS_Store" -delete
	@echo "クリーンアップが完了しました。"

build-mac:
	./scripts/build_app.sh

build-linux:
	./scripts/build_app_linux.sh

build-win:
	scripts\build_app.bat
