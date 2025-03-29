<p align="center">
  <a href="">
    <img src="./docs/header.jpg" alt="header" width="100%">
  </a>
  <h1 align="center">OpenAI Generate PR Title and Description</h1>
</p>

<p align="center">
  <i>This workflow uses an article generation model by OpenAI to generate the title and body of a pull request.</i>

## Usage

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
      - uses: actions/checkout@v4
      - uses: tqer39/openai-generate-pr-description@v1.0.5
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
          openai-api-key: ${{ secrets.OPENAI_API_KEY }}
          locale: 'ja' # Specify 'ja' to generate in Japanese
```

## Inputs

### `github-token`

**Required** GitHub token. Specify `${{ secrets.GITHUB_TOKEN }}`.

### `openai-api-key`

**Required** OpenAI API key. Specify `${{ secrets.OPENAI_API_KEY }}`.

### `openai-model`

**Optional** OpenAI model to use. Default is `gpt-3.5-turbo`.

> [!NOTE]
>
> - 📝 The default model is `gpt-3.5-turbo` and can be used for free in the OpenAI API specification. If you use another model, you may incur charges for the OpenAI API.

### `commit-log-history-limit`

**Optional** Limit of commit log history. Default is `70`.

> [!NOTE]
>
> - 📝 Due to the limit of the number of tokens that can be used in one request in the OpenAI API specification, limiting the number of commit log histories can prevent request failures.

### `locale`

**Optional** Language for the generated title and description. Default is `en` (English). You can specify `ja` for Japanese.

## Contribution

If you find any issues or have improvements, please create an Issue or submit a Pull Request.

## License

This action is released under the MIT license. For more information, see [LICENSE](LICENSE).
