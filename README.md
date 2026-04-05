<p align="center">
  <a href="">
    <img src="./docs/header.jpg" alt="header" width="100%">
  </a>
  <h1 align="center">OpenAI Generate PR Title and Description</h1>
</p>

<p align="center">
  <i>This GitHub Action uses OpenAI to automatically generate pull request titles and descriptions.</i>
</p>

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
      - uses: actions/checkout@v6
        with:
          fetch-depth: 0
      - uses: tqer39/generate-pr-description@v1
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

### `commit-log-history-limit`

**Optional** Limit of commit log history. Default is `70`.

### `locale`

**Optional** Language for the generated title and description. Default is `en` (English). You can specify `ja` for Japanese.

## Versioning

This project follows [Semantic Versioning](https://semver.org/). You can reference:

- **`@v1`** — Latest stable release within major version 1 (recommended)
- **`@v1.2.3`** — Specific version

Releases are created via the manual `Release` workflow (`workflow_dispatch`).

## Contribution

If you find any issues or have improvements, please create an Issue or submit a Pull Request.

## License

This action is released under the MIT license. For more information, see [LICENSE](LICENSE).
