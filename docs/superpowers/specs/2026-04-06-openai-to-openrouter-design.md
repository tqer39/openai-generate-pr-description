<!-- cSpell:ignore getenv Referer -->
# OpenAI → OpenRouter 移行設計書

## Context

現在の `generate-pr-description` GitHub Action は OpenAI API を直接利用してPR説明を自動生成している。これを OpenRouter 経由に変更することで：

- **統一API**: 1つのAPIキーで複数プロバイダー（OpenAI, Anthropic, Google 等）のモデルを利用可能
- **コスト最適化**: 安価なモデルを柔軟に選択可能
- **軽量実装**: 既存の `openai` SDK の `base_url` を変更するだけで実現。新規依存なし

別ブランチ（`feat/change-ai-service`）で LiteLLM を使ったマルチプロバイダー対応が検討されたが、LiteLLM は依存が大きすぎる（uv.lock +1200行）ため、OpenRouter アプローチを採用する。

## 設計

### アプローチ

`openai` SDK の `base_url` パラメータを `https://openrouter.ai/api/v1` に設定。OpenRouter は OpenAI 互換 API を提供しているため、SDK をそのまま利用できる。

### 変更ファイル

#### 1. `pyproject.toml`

- `version`: `"1.0.6"` → `"2.0.0"`（ブレイキングチェンジ）
- 依存は `openai==1.109.1` のまま変更なし

#### 2. `action.yml`

**メタデータ更新:**

- `name`: OpenAI の記述を削除、OpenRouter を記載
- `description`: OpenRouter API を使用する旨に変更

**input の刷新（ブレイキングチェンジ）:**

| 旧 input         | 新 input      | デフォルト          |
| ----------------- | ------------- | ------------------- |
| `openai-api-key`  | `api-key`     | （必須）            |
| `openai-model`    | `model`       | `openai/gpt-4o-mini` |
| —                 | `max-tokens`  | `1000`              |
| —                 | `temperature` | `0.1`               |

旧 input（`openai-api-key`, `openai-model`）は完全に削除。

**環境変数マッピング:**

```yaml
env:
  API_KEY: ${{ inputs.api-key }}
  MODEL: ${{ inputs.model }}
  MAX_TOKENS: ${{ inputs.max-tokens }}
  TEMPERATURE: ${{ inputs.temperature }}
  COMMIT_LOG_HISTORY_LIMIT: ${{ inputs.commit-log-history-limit }}
  LOCALE: ${{ inputs.locale }}
```

#### 3. `scripts/generate_pr_description.py`

**クライアント初期化:**

```python
default_headers = {
    "HTTP-Referer": f"https://github.com/{os.getenv('GITHUB_REPOSITORY', 'tqer39/generate-pr-description')}",
    "X-Title": "generate-pr-description",
}

client = OpenAI(
    api_key=os.getenv("API_KEY"),
    base_url="https://openrouter.ai/api/v1",
    default_headers=default_headers,
)
```

**API コール:**

```python
response = client.chat.completions.create(
    model=os.getenv("MODEL", "openai/gpt-4o-mini"),
    messages=[...],
    max_completion_tokens=int(os.getenv("MAX_TOKENS", "1000")),
    temperature=float(os.getenv("TEMPERATURE", "0.1")),
    extra_body={"route": "fallback"},
)
```

**OpenRouter 固有対応:**

- `HTTP-Referer` / `X-Title` ヘッダー: レート制限緩和とダッシュボード識別用
- `extra_body={"route": "fallback"}`: モデル利用不可時の自動フォールバック

#### 4. `README.md` / `docs/README.ja.md`

- タイトル・説明から OpenAI を削除、OpenRouter を記載
- Usage 例を新 input に合わせて更新
- バージョン参照を `@v2` に更新

## 注意点

- `max_completion_tokens` は OpenRouter でもサポートされている（OpenAI SDK の新しいパラメータ名）
- `extra_body` は openai SDK の安定機能で、リクエストボディに追加フィールドを渡せる
- `GITHUB_REPOSITORY` は GitHub Actions で自動設定されるため、action.yml での明示的なマッピングは不要

## 検証方法

1. `uv sync` で依存が正常にインストールされることを確認
2. 環境変数 `API_KEY` に OpenRouter API キーを設定し、スクリプトを手動実行
3. OpenRouter ダッシュボードでリクエストが記録されていることを確認
4. GitHub Actions で実際のPRに対して動作確認
