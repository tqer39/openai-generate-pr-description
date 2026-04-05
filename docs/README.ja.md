<p align="center">
  <a href="">
    <img src="./header.jpg" alt="header" width="100%">
  </a>
  <h1 align="center">OpenAI Generate PR Title and Description</h1>
</p>

<p align="center">
  <i>OpenAI を使ってプルリクエストのタイトルと本文を自動生成する GitHub Action です。</i>
</p>

## 使い方

```yaml
name: OpenAI Generate PR Title and Description

on:
  pull_request:
    branches:
      - main
    types:
      - opened
      - synchronize

jobs:
  pull-request:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    permissions:
      pull-requests: write
      contents: read
    if: contains(fromJSON('["renovate[bot]"]'), github.event.pull_request.user.login) == false
    steps:
      - uses: actions/checkout@v6
        with:
          fetch-depth: 0
      - uses: tqer39/generate-pr-description@v1
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
          openai-api-key: ${{ secrets.OPENAI_API_KEY }}
          locale: 'ja' # 日本語で生成する場合
```

## Inputs

### `github-token`

**必須** GitHub トークン。`${{ secrets.GITHUB_TOKEN }}` を指定します。

### `openai-api-key`

**必須** OpenAI API キー。`${{ secrets.OPENAI_API_KEY }}` を指定します。

### `openai-model`

**オプション** OpenAI モデル。デフォルトは `gpt-3.5-turbo` です。

### `commit-log-history-limit`

**オプション** コミットログの履歴の制限。デフォルトは `70` です。

### `locale`

**オプション** 言語のロケール。デフォルトは `en` です。

## バージョニング

このプロジェクトは [Semantic Versioning](https://semver.org/) に従います。以下の形式で参照できます:

- **`@v1`** — メジャーバージョン 1 の最新安定版（推奨）
- **`@v1.2.3`** — 特定バージョン

リリースは手動の `Release` ワークフロー（`workflow_dispatch`）で作成されます。

## 貢献方法

問題や課題が発見されたら Issue を作成するか Pull Request を作成していただけると幸いです。

## ライセンス

このアクションは MIT ライセンスのもとで公開されています。詳細については [LICENSE](../LICENSE) を参照してください。
