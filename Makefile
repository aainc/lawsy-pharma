-include .env  # load .env if it exists

LAWSY_DATA_DIR ?= ./data
LAWSY_OUTPUT_DIR ?= ./outputs # set OUTPUT_DIR=./outputs if it's unset
LAWSY_ENCODER_MODEL_NAME ?= openai/text-embedding-3-small
LAWSY_ENCODER_DIM ?= 512
LAWSY_PREPROCESSED_DATA_VERSION ?= latest

# Help --------------------------------------------------------------------------
.PHONY: help
help:
	@echo "Lawsy - 薬事法令Deep Researchツール"
	@echo ""
	@echo "使用方法: make [コマンド]"
	@echo ""
	@echo "📦 セットアップコマンド:"
	@echo "  install               依存関係のインストール"
	@echo "  pharma-setup          薬事法データセットの完全セットアップ（初回のみ）"
	@echo ""
	@echo "🚀 起動コマンド:"
	@echo "  pharma-run            薬事法版アプリの起動（推奨）"
	@echo "  lawsy-run-app         標準版アプリの起動"
	@echo ""
	@echo "📊 データ準備コマンド:"
	@echo "  pharma-prepare        薬事法データセットを一括作成"
	@echo "  pharma-download-laws  薬事法令XMLをダウンロード"
	@echo "  pharma-process-xml    XMLファイルを処理"
	@echo "  pharma-create-article-chunks  法令をチャンクに分割"
	@echo "  pharma-embed-article-chunks   エンベディングを生成"
	@echo "  pharma-create-article-chunk-vector-index  ベクトルインデックスを作成"
	@echo ""
	@echo "🛠️ 開発コマンド:"
	@echo "  format                コードフォーマット"
	@echo "  lint                  リントチェック"
	@echo "  pharma-clean          生成データのクリーンアップ"
	@echo ""
	@echo "📋 その他:"
	@echo "  help                  このヘルプメッセージを表示"


# Setup --------------------------------------------------------------------------
.PHONY: activate install


activate:
	. .venv/bin/activate


deactivate:
	deactivate


install:
	@uv sync --all-groups


# Formatter / Linter / Test ------------------------------------------------------
.PHONY: format lint


format:
	@PATH=".venv/bin:${PATH}" ruff format


lint:
	@PATH=".venv/bin:${PATH}" ruff check src
	@PATH=".venv/bin:${PATH}" pyright src


# Lawsy --------------------------------------------------------------------------
.PHONY:	lawsy-download-preprocessed-data \
        lawsy-create-article-chunks \
        lawsy-embed-article-chunks \
		lawsy-create-article-chunk-vector-index \
		lawsy-prepare \
        lawsy-run-app \
		lawsy-docker-build-app \
		lawsy-docker-push-app \
		lawsy-docker-run-app \
		pharma-download-laws \
		pharma-process-xml \
		pharma-create-article-chunks \
		pharma-embed-article-chunks \
		pharma-create-article-chunk-vector-index \
		pharma-prepare


lawsy-download-preprocessed-data:
	@mkdir -p outputs && gcloud storage cp -r gs://885188444194-public-data/${LAWSY_PREPROCESSED_DATA_VERSION}/lawsy ./outputs/


lawsy-create-article-chunks:
	@PATH=".venv/bin:${PATH}" PYTHONPATH=src python src/lawsy/main.py create-article-chunks $(shell echo ${LAWSY_DATA_DIR})/all_xml $(shell echo ${LAWSY_OUTPUT_DIR})/lawsy/article_chunks.jsonl


lawsy-embed-article-chunks:
	@PATH=".venv/bin:${PATH}" PYTHONPATH=src python src/lawsy/main.py embed-article-chunks $(shell echo ${LAWSY_OUTPUT_DIR})/lawsy/article_chunks.jsonl $(shell echo ${LAWSY_OUTPUT_DIR})/lawsy/article_chunk_embeddings.parquet --model_name ${LAWSY_ENCODER_MODEL_NAME}


lawsy-create-article-chunk-vector-index:
	@PATH=".venv/bin:${PATH}" PYTHONPATH=src python src/lawsy/main.py create-article-chunk-vector-index $(shell echo ${LAWSY_OUTPUT_DIR})/lawsy/article_chunk_embeddings.parquet $(shell echo ${LAWSY_OUTPUT_DIR})/lawsy/article_chunks.jsonl $(shell echo ${LAWSY_OUTPUT_DIR})/lawsy/article_chunks_faiss --dim ${LAWSY_ENCODER_DIM}


lawsy-prepare: lawsy-create-article-chunks lawsy-embed-article-chunks lawsy-create-article-chunk-vector-index


lawsy-run-app:
	@PATH=".venv/bin:${PATH}" PYTHONPATH=src LAWSY_OUTPUT_DIR=${LAWSY_OUTPUT_DIR} streamlit run src/lawsy/app/app.py


lawsy-docker-build-app:
	@docker build --platform=linux/amd64 -t lawsy-app -f src/lawsy/app/Dockerfile .


lawsy-docker-run-app:
	@docker run -it --rm --name lawsy-app \
	    -v ./src:/app/src \
		-v ./.env:/app/.env \
		-v ./.streamlit:/app/.streamlit \
		-v ./lawsy_history:/app/lawsy_history \
		-v ./outputs:/app/outputs \
		-p 8501:8501 lawsy-app:latest


# Pharma-specific targets -------------------------------------------------------

pharma-download-laws:
	@uv run python src/lawsy/data/pharma_law_downloader.py --output-dir data/pharma_xml --delay 2.0

pharma-process-xml:
	@uv run python src/lawsy/data/egov_xml_processor.py data/pharma_xml data/pharma_xml_processed

pharma-create-article-chunks:
	@PATH=".venv/bin:${PATH}" PYTHONPATH=src python src/lawsy/main.py create-article-chunks data/pharma_xml_processed $(shell echo ${LAWSY_OUTPUT_DIR})/pharma/article_chunks.jsonl

pharma-embed-article-chunks:
	@PATH=".venv/bin:${PATH}" PYTHONPATH=src python src/lawsy/main.py embed-article-chunks $(shell echo ${LAWSY_OUTPUT_DIR})/pharma/article_chunks.jsonl $(shell echo ${LAWSY_OUTPUT_DIR})/pharma/article_chunk_embeddings.parquet --model-name ${LAWSY_ENCODER_MODEL_NAME}

pharma-create-article-chunk-vector-index:
	@PATH=".venv/bin:${PATH}" PYTHONPATH=src python src/lawsy/main.py create-article-chunk-vector-index $(shell echo ${LAWSY_OUTPUT_DIR})/pharma/article_chunk_embeddings.parquet $(shell echo ${LAWSY_OUTPUT_DIR})/pharma/article_chunks.jsonl $(shell echo ${LAWSY_OUTPUT_DIR})/pharma/article_chunks_faiss --dim ${LAWSY_ENCODER_DIM}

pharma-prepare: pharma-download-laws pharma-process-xml pharma-create-article-chunks pharma-embed-article-chunks pharma-create-article-chunk-vector-index


# Pharma convenience targets -----------------------------------------------------
.PHONY: pharma-setup pharma-run pharma-clean

pharma-setup: install pharma-prepare
	@echo "✅ 薬事法版Lawsyのセットアップが完了しました！"
	@echo "次のコマンドでアプリを起動できます: make pharma-run"

pharma-run:
	@echo "🚀 薬事法版Lawsyを起動しています..."
	@PATH=".venv/bin:${PATH}" PYTHONPATH=src LAWSY_OUTPUT_DIR=${LAWSY_OUTPUT_DIR} streamlit run src/lawsy/app/app.py

pharma-clean:
	@echo "🧹 生成データをクリーンアップしています..."
	@rm -rf data/pharma_xml data/pharma_xml_processed
	@rm -rf outputs/pharma
	@echo "✅ クリーンアップが完了しました"
