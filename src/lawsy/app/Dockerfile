FROM python:3.12-slim

# install basic libs
ENV DEBIAN_FRONTEND=noninteractive

ARG WORKDIR="/app"
ENV WORKDIR=${WORKDIR}
WORKDIR /app

RUN pip install uv
COPY pyproject.toml pyproject.toml
RUN uv sync
ENV PATH="/app/.venv/bin:$PATH"

ENV HF_HOME="/app/cache/"
# uncomment if you use ME5 model
# COPY ./cache/hub/models--intfloat--multilingual-e5-large-instruct /app/cache/hub/models--intfloat--multilingual-e5-large-instruct
COPY .env /app/.env
COPY sa.json /app/sa.json
COPY ./outputs/lawsy/article_chunks.jsonl /app/outputs/lawsy/article_chunks.jsonl
COPY ./outputs/lawsy/article_chunks_faiss /app/outputs/lawsy/article_chunks_faiss

ARG PORT="8501"
ENV PORT=${PORT}
EXPOSE ${PORT}

COPY ./src ./src
COPY ./Makefile ./Makefile
ENV PYTHONPATH=src

CMD ["streamlit", "run", "src/lawsy/app/app.py"]
