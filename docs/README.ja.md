<p align="center">
  <a href="">
    <img src="./header.jpg" alt="header" width="100%">
  </a>
  <h1 align="center">OpenAI Generate PR Title and Description</h1>
</p>

<p align="center">
  <i>このワークフローでは OpenAI による文章生成モデルを使って、プルリクエストのタイトルと本文を生成します。</i>
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
    if: contains(fromJSON('["renovate[bot]"]'), github.event.pull_request.user.login) == false
    steps:
      - uses: actions/checkout@v4
      - uses: tqer39/openai-generate-pr-description@v1.0.4
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
          openai-api-key: ${{ secrets.OPENAI_API_KEY }}
```

## Inputs

### `github-token`

**必須** GitHub トークン。`${{ secrets.GITHUB_TOKEN }}` を指定します。

### `openai-api-key`

**必須** OpenAI API キー。`${{ secrets.OPENAI_API_KEY }}` を指定します。

### `openai-model`

**オプション** OpenAI モデル。デフォルトは `gpt-3.5-turbo` です。

> [!NOTE]
>
> - 📝 OpenAI API の仕様で、デフォルトのモデルは `gpt-3.5-turbo` で無料で使用できます。その他のモデルを使用する場合は、OpenAI API の料金が発生する可能性があります。

### `commit-log-history-limit`

**オプション** コミットログの履歴の制限。デフォルトは `70` です。

> [!NOTE]
>
> - 📝 OpenAI API の仕様で、1回のリクエストで使用可能なトークン数に制限があるため、コミットログの履歴の数を制限することで、リクエストの失敗を防ぐことができます。

## 貢献方法

問題や課題が発見されたら Issue を作成するか Pull Request を作成していただけると幸いです。

## ライセンス

このアクションは MIT ライセンスのもとで公開されています。詳細については [LICENSE](LICENSE) を参照してください。
