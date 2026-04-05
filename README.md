<p align="center">
  <a href="">
    <img src="./docs/header.jpg" alt="header" width="100%">
  </a>
  <h1 align="center">AI Generate PR Title and Description</h1>
</p>

<p align="center">
  <i>This GitHub Action uses AI to automatically generate pull request titles and descriptions. Supports multiple providers: OpenAI, Anthropic (Claude), Google Gemini, and more.</i>

## Usage

### OpenAI

```yaml
name: AI Generate PR Title and Description

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
      - uses: tqer39/openai-generate-pr-description@v2
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
          api-key: ${{ secrets.OPENAI_API_KEY }}
          provider: openai
          model: gpt-4o-mini
          locale: 'ja'
```

### Anthropic (Claude)

```yaml
      - uses: tqer39/openai-generate-pr-description@v2
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
          api-key: ${{ secrets.ANTHROPIC_API_KEY }}
          provider: anthropic
          model: claude-sonnet-4-20250514
          locale: 'ja'
```

### Google Gemini

```yaml
      - uses: tqer39/openai-generate-pr-description@v2
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
          api-key: ${{ secrets.GEMINI_API_KEY }}
          provider: gemini
          model: gemini-2.0-flash
          locale: 'ja'
```

## Inputs

### `api-key`

**Required** API key for the selected provider.

### `provider`

**Optional** AI provider to use. Default is `openai`.

Supported providers: `openai`, `anthropic`, `gemini`, and [many more via LiteLLM](https://docs.litellm.ai/docs/providers).

### `model`

**Optional** Model name. Default is `gpt-4o-mini`.

Examples:

- OpenAI: `gpt-4o-mini`, `gpt-4o`
- Anthropic: `claude-sonnet-4-20250514`, `claude-haiku-4-5-20251001`
- Gemini: `gemini-2.0-flash`, `gemini-2.5-pro-preview-05-06`

### `github-token`

**Required** GitHub token. Specify `${{ secrets.GITHUB_TOKEN }}`.

### `commit-log-history-limit`

**Optional** Limit of commit log history. Default is `70`.

> [!NOTE]
>
> - 📝 Limiting the number of commit log histories can prevent token overflow on large PRs.

### `locale`

**Optional** Language for the generated title and description. Default is `en` (English). You can specify `ja` for Japanese.

### `max-tokens`

**Optional** Maximum tokens for the response. Default is `1000`.

### `temperature`

**Optional** Temperature for generation (0.0-2.0). Default is `0.1`.

### `api-base-url`

**Optional** Custom API base URL for self-hosted or proxy endpoints.

## Migration from v1

If you are upgrading from v1, replace the deprecated inputs:

```yaml
# v1 (deprecated)
- uses: tqer39/openai-generate-pr-description@v1
  with:
    openai-api-key: ${{ secrets.OPENAI_API_KEY }}
    openai-model: gpt-3.5-turbo

# v2 (new)
- uses: tqer39/openai-generate-pr-description@v2
  with:
    api-key: ${{ secrets.OPENAI_API_KEY }}
    provider: openai
    model: gpt-4o-mini
```

> [!NOTE]
>
> - 📝 The v1 inputs (`openai-api-key`, `openai-model`) still work for backward compatibility but will show deprecation warnings.

## Contribution

If you find any issues or have improvements, please create an Issue or submit a Pull Request.

## License

This action is released under the MIT license. For more information, see [LICENSE](LICENSE).
