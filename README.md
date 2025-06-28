# Lawsy - Making Law Easy

## Requirements

- uv
    - `pip install uv`
- OpenAI
    - `OPENAI_API_KEY`
- GCloud CLI
    - https://cloud.google.com/sdk/docs/install

## Run

### 1. Install dependencies

Install Python packages

```shell
make install
```

### 2. Create .env file

Create .env file and put it in the repository root directory.

```text
OPENAI_API_KEY=sk-...  # OpenAI API KEY
LAWSY_WEB_SEARCH_ENGINE=DuckDuckGo
LAWSY_LM=openai/gpt-4o-mini
```

### 3. Download Preprocessed Data

```shell
make lawsy-download-preprocessed-data
```

## Run App

```shell
make lawsy-run-app
```

## Development

### Format & Lint

format:

```shell
make format
```

lint:

```shell
make lint
```

## References

ブログ記事

- 2025-03-16 [行政と技術の融合へ—法令Deep ResearchツールLawsyの開発記録](https://note.com/policygarage/n/nbea6a40f9a0a)
- 2025-03-06 [法令 Deep Research ツール Lawsy を OSS として公開しました](https://note.com/tatsuyashirakawa/n/nbda706503902)
