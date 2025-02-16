-include .env  # load .env if it exists

DATA_DIR ?= ./data
OUTPUT_DIR ?= ./outputs # set OUTPUT_DIR=./outputs if it's unset
PYTHON := python
RUFF := ruff
PYRIGHT := pyright
HF_HOME := ./cache
ENCODER_MODEL_NAME := openai/text-embedding-3-small
ENCODER_DIM := 512
PREPROCESSED_DATA_VERSION := v20250216.0


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


# GCP ----------------------------------------------------------------------------
.PHONY: gcloud-login gcloud-application-default-login


gcloud-login:
	@gcloud auth login


gcloud-application-default-login:
	@gcloud auth application-default login


# Docker -------------------------------------------------------------------------
.PHONY: docker-login


docker-login:
	@gcloud auth print-access-token | docker login -u oauth2accesstoken https://asia-northeast1-docker.pkg.dev --password-stdin


# Lawsy --------------------------------------------------------------------------
.PHONY:	lawsy-download-preprocessed-data \
        lawsy-create-article-chunks \
        lawsy-embed-article-chunks \
		lawsy-create-article-chunk-vector-index \
		lawsy-prepare \
        lawsy-run-app \
		lawsy-docker-build-app \
		lawsy-docker-push-app \
		lawsy-docker-run-app


lawsy-download-preprocessed-data:
	@mkdir -p outputs && gcloud storage cp -r gs://885188444194-public-data/${PREPROCESSED_DATA_VERSION}/lawsy ./outputs/


lawsy-create-article-chunks:
	@PATH=".venv/bin:${PATH}" PYTHONPATH=src python src/lawsy/main.py create-article-chunks $(shell echo ${DATA_DIR})/all_xml $(shell echo ${OUTPUT_DIR})/lawsy/article_chunks.jsonl


lawsy-embed-article-chunks:
	@PATH=".venv/bin:${PATH}" PYTHONPATH=src python src/lawsy/main.py embed-article-chunks $(shell echo ${OUTPUT_DIR})/lawsy/article_chunks.jsonl $(shell echo ${OUTPUT_DIR})/lawsy/article_chunk_embeddings.parquet --model_name ${ENCODER_MODEL_NAME}


lawsy-create-article-chunk-vector-index:
	@PATH=".venv/bin:${PATH}" PYTHONPATH=src python src/lawsy/main.py create-article-chunk-vector-index $(shell echo ${OUTPUT_DIR})/lawsy/article_chunk_embeddings.parquet $(shell echo ${OUTPUT_DIR})/lawsy/article_chunks.jsonl $(shell echo ${OUTPUT_DIR})/lawsy/article_chunks_faiss --dim ${ENCODER_DIM}


lawsy-prepare: lawsy-create-article-chunks lawsy-embed-article-chunks lawsy-create-article-chunk-vector-index


lawsy-run-app:
	@PATH=".venv/bin:${PATH}" HF_HOME=$(shell echo ${HF_HOME}) PYTHONPATH=src ENCODER_MODEL_NAME=${ENCODER_MODEL_NAME} streamlit run src/lawsy/app/app.py


lawsy-docker-build-app:
	@docker build --platform=linux/amd64 -t lawsy-app -f src/lawsy/app/Dockerfile .


lawsy-docker-push-app:
	@docker build --platform=linux/amd64 -t asia-northeast1-docker.pkg.dev/law-dx-hackathon-2025/lawsy/lawsy-app:latest -f src/lawsy/app/Dockerfile . --push


lawsy-docker-run-app:
	@docker run -it --rm --name lawsy-app -v ./src:/app/src -p 8501:8501 lawsy-app:latest


# Kokkai Crawler -----------------------------------------------------------------
.PHONY: kokkai-crawl-all


kokkai-crawl-all:
	@PATH=".venv/bin:${PATH}" python src/kokkai_crawler/main.py $(shell echo ${OUTPUT_DIR})/data/kokkai/mtgs.jsonl --from-year 1945
