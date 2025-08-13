# Lawsy - Making Law Easy

薬事法令に特化した法令Deep Researchツール

## 謝辞

Lawsy Pharma は Lawsy からフォークして作成されました、素晴らしいツールを開発してくれた Lawsy Team に感謝します。

## 📋 Overview

Lawsy Pharma は、日本の薬事法令（薬機法、GCP省令、GMP省令など）に関する質問に対して、関連法令を検索・分析し、包括的なレポートを生成するAIツールです。

### 主な機能
- 🔍 薬事法令の高精度検索
- 📊 違反・問題点の自動分析
- 📝 包括的なレポート生成
- 🗺️ マインドマップによる可視化
- ⚠️ 具体的な問題点と該当法律のサマリー表示

## 🚀 Quick Start (薬事法版)

薬事法に特化したLawsy Pharma を起動する方法：

```bash
# 1. リポジトリのクローン
git clone https://github.com/happy-ryo/lawsy.git
cd lawsy

# 2. 依存関係のインストール
make install

# 3. 環境設定（.envファイルを作成）
cp .env.example .env
# .envファイルを編集してOpenAI APIキーを設定

# 4. 薬事法データセットの準備（初回のみ、約30分）
make pharma-setup

# 5. アプリケーションの起動
make pharma-run
```

ブラウザで http://localhost:8502 にアクセスしてください。

## 📦 Requirements

### 必須要件
- Python 3.11以上
- [uv](https://github.com/astral-sh/uv) (Pythonパッケージマネージャー)
  ```bash
  pip install uv
  ```
- OpenAI API Key
  - [OpenAI Platform](https://platform.openai.com/)でAPIキーを取得

## 🔧 Installation

### 1. 依存関係のインストール

```bash
make install
```

### 2. 環境設定

`.env`ファイルを作成し、必要な環境変数を設定します：

```bash
cp .env.example .env
```

`.env`ファイルを編集：
```env
# 必須
OPENAI_API_KEY=sk-...

# オプション（デフォルト値あり）
LAWSY_LM=openai/gpt-5-mini
LAWSY_WEB_SEARCH_ENGINE=DuckDuckGo
LAWSY_VIOLATION_SUMMARY_MAX_ITEMS=10
LAWSY_HISTORY_DIR=./lawsy_history
```

## 📊 データセットの準備

### 薬事法データセット（推奨）

薬事法に特化したデータセットを作成します：

```bash
# 全ステップを一括実行（約30分）
make pharma-prepare
```

または、各ステップを個別に実行：

```bash
# 1. 薬事法令XMLをダウンロード（e-Gov法令APIから）
make pharma-download-laws

# 2. XMLファイルを処理
make pharma-process-xml

# 3. 法令をチャンクに分割
make pharma-create-article-chunks

# 4. エンベディングを生成（OpenAI APIを使用）
make pharma-embed-article-chunks

# 5. ベクトルインデックスを作成
make pharma-create-article-chunk-vector-index
```

## 🎮 使い方

### アプリケーションの起動

```bash
# 薬事法版の起動
make pharma-run

# または標準版の起動
make lawsy-run-app
```

### 使用例

1. ブラウザで http://localhost:8502 にアクセス
2. 検索ボックスに質問を入力（例：「治験の同意取得について教えて」）
3. AIが関連法令を検索・分析してレポートを生成
4. 違反・問題点のサマリーが上部に表示
5. マインドマップで全体構造を確認

## ⚙️ 設定オプション

### 環境変数

| 変数名 | 説明 | デフォルト値 | 例 |
|--------|------|------------|-----|
| `OPENAI_API_KEY` | OpenAI APIキー | （必須） | `sk-...` |
| `LAWSY_LM` | 使用するLLMモデル | `openai/gpt-4o-mini` | `openai/gpt-4o` |
| `LAWSY_VIOLATION_SUMMARY_LM` | 違反サマリー生成専用LM | `LAWSY_LM`と同じ | `anthropic/claude-3-5-sonnet-latest` |
| `LAWSY_WEB_SEARCH_ENGINE` | Web検索エンジン | `DuckDuckGo` | `Google` |
| `LAWSY_VIOLATION_SUMMARY_MAX_ITEMS` | 違反サマリーの最大表示数 | `10` | `5` |
| `LAWSY_HISTORY_DIR` | 履歴保存ディレクトリ | `./lawsy_history` | `/path/to/history` |
| `LAWSY_OUTPUT_DIR` | データ出力ディレクトリ | `./outputs` | `/path/to/outputs` |

### カスタマイズ

設定ファイル `.streamlit/config.toml` でUIのカスタマイズが可能です。

## 🛠️ Development

### コードフォーマット

```bash
make format
```

### リント

```bash
make lint
```

### 利用可能なMakeコマンド

```bash
make help  # 全コマンドの一覧表示
```

主なコマンド：
- `make install` - 依存関係のインストール
- `make pharma-setup` - 薬事法データセットの完全セットアップ
- `make pharma-run` - 薬事法版の起動
- `make pharma-clean` - 生成データのクリーンアップ
- `make format` - コードフォーマット
- `make lint` - リントチェック

### 技術スタック
- **Frontend**: Streamlit
- **LLM**: OpenAI GPT-4 / GPT-4o-mini
- **Vector Search**: FAISS
- **Embedding**: OpenAI text-embedding-3-small
- **Framework**: DSPy

## 📄 License

MIT License

## 🤝 Contributing

プルリクエストを歓迎します！
バグ報告や機能要望は[Issues](https://github.com/happy-ryo/lawsy/issues)にお願いします。


**注意**: 本ツールの回答は必ずしも正確とは限りません。薬事に関する重要な判断は、必ず専門家に確認してください。