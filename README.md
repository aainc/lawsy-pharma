# Lawsy -- Legal Search Made Easy

## Requirements

- Python
    - uv `pip install uv`
- GCP
    - [Cloud SDK](https://cloud.google.com/sdk?hl=ja)

## Setup

Install Python packages

```shell
make install
```

## Create .env file

Create .env file and put it in the repository root directory.

```text
OUTPUT_DIR=./outputs  # output directory in which processed data are placed
HISTORY_BUCKET_NAME=885188444194-history  #  GCP bucket to store history data
OPENAI_API_KEY=<<your api key>>
TAVILY_API_KEY=<<your api key>>
```

## Run App

### Download Preprocessed Data

```shell
make lawsy-download-preprocessed-data
```

### Run

```shell
make gcloud-application-default-login  # if you haven't logged in Google Cloud
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

### Development Flow (merge into dev)

1. Create your branch `feature/{{feature-name}}` from dev
2. Create a pull request into dev
3. Fix lint errors
4. Review the PR
5. Merge the PR
