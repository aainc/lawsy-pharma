-include .env  # load .env if it exists

DATA_DIR ?= ./data
OUTPUT_DIR ?= ./outputs # set OUTPUT_DIR=./outputs if it's unset
PYTHON := python
RUFF := ruff
PYRIGHT := pyright
HF_HOME := ./cache


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


# Docker -------------------------------------------------------------------------
.PHONY: docker-login


docker-login:
	@gcloud auth print-access-token | docker login -u oauth2accesstoken https://asia-northeast1-docker.pkg.dev --password-stdin


# Kokkai Crawler -----------------------------------------------------------------
.PHONY: kokkai-crawl-all


kokkai-crawl-all:
	@PATH=".venv/bin:${PATH}" python src/kokkai_crawler/main.py $(shell echo ${OUTPUT_DIR})/data/kokkai/mtgs.jsonl --from-year 1945


# Law Text Extractor ------------------------------------------------------------
.PHONY: law-extract-texts law-embed-texts law-create-index law-run-app law-prepare-app law-docker-build-app law-docker-run-app


law-extract-texts:
	@PATH=".venv/bin:${PATH}" python src/lawsearch/main.py extract-law-texts $(shell echo ${DATA_DIR})/all_xml $(shell echo ${OUTPUT_DIR})/law/law_texts.jsonl


law-embed-texts:
	@PATH=".venv/bin:${PATH}" HF_HOME=$(shell echo ${HF_HOME}) PYTHONPATH=src python src/lawsearch/main.py embed-law-texts $(shell echo ${OUTPUT_DIR})/law/law_texts.jsonl $(shell echo ${OUTPUT_DIR})/law/law_text_embeddings.jsonl


law-create-index:
	@PATH=".venv/bin:${PATH}" PYTHONPATH=src python src/lawsearch/main.py create-law-index $(shell echo ${OUTPUT_DIR})/law/law_text_embeddings.jsonl $(shell echo ${OUTPUT_DIR})/law/laws.qdrant


law-run-app:
	@PATH=".venv/bin:${PATH}" HF_HOME=$(shell echo ${HF_HOME}) PYTHONPATH=src streamlit run src/lawsearch/app/app.py


law-docker-build-app:
	@docker build --platform=linux/amd64 -t lawsearch-app -f src/lawsearch/app/Dockerfile .


law-docker-push-app:
	@docker build --platform=linux/amd64 -t asia-northeast1-docker.pkg.dev/law-dx-hackathon-2025/lawsearch/lawsearch-app:latest -f src/lawsearch/app/Dockerfile . --push


law-docker-run-app:
	@docker run -it --rm --name lawsearch-app -v ./src:/app/src -p 8501:8501 lawsearch-app:latest
