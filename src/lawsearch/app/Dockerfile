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
COPY ./cache/hub/models--intfloat--multilingual-e5-large-instruct /app/cache/hub/models--intfloat--multilingual-e5-large-instruct
COPY ./outputs/law/laws.qdrant /app/outputs/law/laws.qdrant

ARG PORT="8501"
ENV PORT=${PORT}
EXPOSE ${PORT}

COPY ./src ./src
COPY ./Makefile ./Makefile
ENV PYTHONPATH=src

CMD ["streamlit", "run", "src/lawsearch/app/app.py"]
