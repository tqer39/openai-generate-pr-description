# PR タイトルにラベル文字列が漏れるバグの修正プラン

> **For agentic workers (Codex CLI 等):** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** OpenRouter で生成される PR タイトルに `プルリクエストタイトル` のようなラベル文字列が漏れるバグを、プロンプト書き換えと後処理ガードで修正する。

**Architecture:** 修正は 2 層構造。(1) `scripts/generate_pr_description.py` の `create_prompt()` を、指示と出力フォーマットを明確に分離した形へ書き換え、LLM がラベルを翻訳・再現しないようにする。(2) 後処理ヘルパー `_strip_label_lines()` を追加し、出力先頭にラベル風行が残っても除去する defense-in-depth を入れる。`action.yml` の `head -n 1 / tail -n +2` による分割ロジックには手を加えない。

**Tech Stack:** Python 3.13 / uv / OpenAI SDK (OpenRouter base_url) / ruff / pytest (新規追加)

---

## バグの背景

このリポジトリは GitHub Action として PR タイトル・本文を OpenRouter 経由で生成する。`locale: ja` で動かすと PR タイトルが `プルリクエストタイトル` という literal なラベル文字列になり、本文の冒頭にも `プルリクエストの説明` というラベルが混入する。

**実例:** https://github.com/tqer39/terraform-github/pull/1607

**実際の LLM 出力 (PR 1607):**

```
プルリクエストタイトル       ← line 1 = head -n 1 で title に
🔒 tts-partner リポジトリを private に変更   ← 本来のタイトル
（空行）
プルリクエストの説明                ← 「## Pull Request Description」が翻訳されて混入
## 📒 変更の概要
...
```

**根本原因:** `scripts/generate_pr_description.py:28-75` の `create_prompt()` テンプレートが「指示」と「出力テンプレート」を区別できておらず、LLM が以下 2 箇所を「再現すべき内容」と解釈している。

1. 箇条書きラベル `- Pull Request Title` / `- Pull Request Description` (line 48, 51)
2. プロンプト末尾の literal な markdown 見出し `## Pull Request Description` (line 62)

`temperature: 0.1` の低温度設定がこのテンプレート忠実再現傾向を強めている。

---

## ファイル構成

| ファイル | 操作 | 役割 |
|---------|------|------|
| `scripts/generate_pr_description.py` | Modify | プロンプト書き換え + `_strip_label_lines` 追加 + `generate_pr_description()` に後処理適用 |
| `pyproject.toml` | Modify | `pytest` を dev-dependencies に追加 |
| `tests/__init__.py` | Create | テストパッケージマーカー（空ファイル） |
| `tests/test_generate_pr_description.py` | Create | `_strip_label_lines` のユニットテスト |

`action.yml` は変更しない（`head -n 1 / tail -n +2` ロジックは正しく動作している）。

---

### Task 1: pytest を dev-dependencies に追加してテストディレクトリを作る

**Files:**
- Modify: `pyproject.toml:15-18`
- Create: `tests/__init__.py`

- [ ] **Step 1: pyproject.toml の `[tool.uv]` セクションに `pytest` を追加**

`pyproject.toml` の以下のブロックを変更する:

変更前 (lines 15-18):

```toml
[tool.uv]
dev-dependencies = [
    "openai==2.32.0",
]
```

変更後:

```toml
[tool.uv]
dev-dependencies = [
    "openai==2.32.0",
    "pytest>=8.0",
]
```

- [ ] **Step 2: テストディレクトリを作って空の `__init__.py` を置く**

```bash
mkdir -p tests
touch tests/__init__.py
```

- [ ] **Step 3: 依存をインストールして pytest が動くことを確認**

Run:

```bash
uv sync
uv run pytest --version
```

Expected: `pytest 8.x.x` 等のバージョン文字列が表示される。エラーが出なければ OK。

- [ ] **Step 4: コミット**

```bash
git add pyproject.toml uv.lock tests/__init__.py
git commit -m "🧪 pytest を dev-dependencies に追加してテスト環境を整備"
```

---

### Task 2: `_strip_label_lines` の失敗するテストを書く

**Files:**
- Create: `tests/test_generate_pr_description.py`

- [ ] **Step 1: テストファイルを作成して失敗するテストを書く**

`tests/test_generate_pr_description.py` を以下の内容で作成:

```python
"""Tests for generate_pr_description helpers."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_module():
    """`scripts/generate_pr_description.py` は API_KEY を import 時に要求するため、
    API_KEY を環境変数にセットしてからロードする。"""
    import os

    os.environ.setdefault("API_KEY", "dummy-for-tests")

    script_path = Path(__file__).parent.parent / "scripts" / "generate_pr_description.py"
    spec = importlib.util.spec_from_file_location("generate_pr_description", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["generate_pr_description"] = module
    spec.loader.exec_module(module)
    return module


MOD = _load_module()


def test_strips_japanese_label_at_start():
    """LLM が日本語ラベルを 1 行目に出した場合、それを剥がして本来のタイトルを 1 行目に持ってくる。"""
    bad = (
        "プルリクエストタイトル  \n"
        "🔒 tts-partner リポジトリを private に変更\n"
        "\n"
        "プルリクエストの説明\n"
        "\n"
        "## 📒 変更の概要\n"
    )
    cleaned = MOD._strip_label_lines(bad)
    assert cleaned.splitlines()[0] == "🔒 tts-partner リポジトリを private に変更"


def test_strips_english_label_at_start():
    """英語ラベル ("Pull Request Title", "Title:" 等) も剥がす。"""
    bad = "Pull Request Title\n🔧 refactor auth helpers\n\n## Summary\n"
    cleaned = MOD._strip_label_lines(bad)
    assert cleaned.splitlines()[0] == "🔧 refactor auth helpers"


def test_strips_title_colon_prefix():
    """`Title:` のようなラベル行も剥がす。"""
    bad = "Title: foo\n🚀 release v1\n\nbody\n"
    cleaned = MOD._strip_label_lines(bad)
    assert cleaned.splitlines()[0] == "🚀 release v1"


def test_keeps_label_in_middle():
    """中間に偶然ラベル風文字列が出ても剥がさない（先頭のみ対象）。"""
    text = "🔒 title\n\nプルリクエストの説明 should stay\n"
    cleaned = MOD._strip_label_lines(text)
    assert "プルリクエストの説明 should stay" in cleaned


def test_no_label_passthrough():
    """ラベルが無い正常出力はそのまま返す（前後の strip のみ）。"""
    text = "🚀 fix bug\n\nbody here"
    cleaned = MOD._strip_label_lines(text)
    assert cleaned.splitlines()[0] == "🚀 fix bug"
    assert "body here" in cleaned


def test_strips_leading_blank_lines():
    """先頭の空行は剥がす。"""
    text = "\n\n🔧 fix\n\nbody"
    cleaned = MOD._strip_label_lines(text)
    assert cleaned.splitlines()[0] == "🔧 fix"
```

- [ ] **Step 2: テストを実行して失敗することを確認**

Run:

```bash
uv run pytest tests/test_generate_pr_description.py -v
```

Expected: 6 個のテストすべてが失敗する。エラーメッセージは `AttributeError: module 'generate_pr_description' has no attribute '_strip_label_lines'` または類似。

- [ ] **Step 3: コミット**

```bash
git add tests/test_generate_pr_description.py
git commit -m "🧪 _strip_label_lines の失敗テストを追加"
```

---

### Task 3: `_strip_label_lines` ヘルパーを実装する

**Files:**
- Modify: `scripts/generate_pr_description.py` (`generate_pr_description` 関数の手前にヘルパーを追加)

- [ ] **Step 1: `scripts/generate_pr_description.py:78` の `def generate_pr_description` の直前に以下を挿入**

挿入位置: `def create_prompt(...)` の戻り値 `return custom_prompt or default_prompt` を持つブロックの直後、`def generate_pr_description(...)` の直前。

挿入する内容:

```python
_LABEL_NOISE_PATTERNS = (
    # English labels
    "pull request title",
    "pull request description",
    "title:",
    "description:",
    "body:",
    # Japanese labels
    "プルリクエストタイトル",
    "プルリクエストの説明",
    "プルリクエスト説明",
    "タイトル:",
    "タイトル：",
    "説明:",
    "説明：",
)


def _strip_label_lines(text: str) -> str:
    """Remove leading lines that are just label echoes from the LLM.

    The OpenRouter prompt previously contained literal section labels
    ("Pull Request Title" / "## Pull Request Description") which gpt-4o-mini
    occasionally reproduced (translated when locale=ja) as the first lines
    of its response. The shell side splits the response with `head -n 1`,
    so a leaked label becomes the PR title. This helper drops any such
    leading label lines (and leading blanks) before the response is printed.

    Only the leading run is stripped; identical strings appearing later in
    the body are kept as-is to avoid false positives.
    """
    lines = text.splitlines()
    while lines:
        head = lines[0].strip().strip("#").strip().strip("*").strip().lower()
        if head and any(head == pat or head.startswith(pat) for pat in _LABEL_NOISE_PATTERNS):
            lines.pop(0)
            continue
        if not head:
            lines.pop(0)
            continue
        break
    return "\n".join(lines)
```

- [ ] **Step 2: テストを実行して通ることを確認**

Run:

```bash
uv run pytest tests/test_generate_pr_description.py -v
```

Expected: 6 個のテストすべてが PASS する。

- [ ] **Step 3: ruff でリント・フォーマットを確認**

Run:

```bash
uv run ruff check scripts/generate_pr_description.py
uv run ruff format --check scripts/generate_pr_description.py
```

Expected: `All checks passed!` と `1 file already formatted`（もし `format --check` が差分を出したら `uv run ruff format scripts/generate_pr_description.py` を実行して再 check）。

- [ ] **Step 4: コミット**

```bash
git add scripts/generate_pr_description.py
git commit -m "✨ LLM 出力先頭のラベル風行を剥がす _strip_label_lines を追加"
```

---

### Task 4: `generate_pr_description()` の戻り値に `_strip_label_lines` を適用する

**Files:**
- Modify: `scripts/generate_pr_description.py:93` 付近（`return str(response.choices[0].message.content).strip()` の行）

- [ ] **Step 1: `_strip_label_lines` を戻り値に適用する**

変更前 (line 93 付近):

```python
    return str(response.choices[0].message.content).strip()
```

変更後:

```python
    raw = str(response.choices[0].message.content).strip()
    return _strip_label_lines(raw)
```

- [ ] **Step 2: ruff チェック**

Run:

```bash
uv run ruff check scripts/generate_pr_description.py
uv run ruff format --check scripts/generate_pr_description.py
```

Expected: いずれもパス。

- [ ] **Step 3: テスト実行（前タスクの 6 テストが引き続き通ることを確認）**

Run:

```bash
uv run pytest tests/ -v
```

Expected: 6 個 PASS。

- [ ] **Step 4: コミット**

```bash
git add scripts/generate_pr_description.py
git commit -m "🔧 generate_pr_description の戻り値にラベル剥がし後処理を適用"
```

---

### Task 5: プロンプトを書き換えてラベル混入の根本原因を除去する

**Files:**
- Modify: `scripts/generate_pr_description.py` (`create_prompt` 関数全体, line 28-76)

- [ ] **Step 1: `create_prompt` 関数を以下の内容で完全に置き換える**

変更前 (line 28-76):

```python
def create_prompt(commit_logs: str, custom_prompt: str | None = None, locale: str = "en") -> str:
    default_prompt = f"""
    ## Instructions

    - Read the following commit logs and file diffs, and create an easy-to-understand pull request title and detailed description.
    -
    - From the second line onward, write in Markdown format.
    - Enclose file names in backticks.
    - Refer to the following:
        - Use GitHub's Markdown syntax (https://github.com/orgs/community/discussions/16925) for NOTE, TIPS, IMPORTANT, WARNING, CAUTION as needed.
    - Respond in the language specified by the locale: {locale}.
    - Ensure that the response is entirely in the specified locale language.

    Example:
    ```
    > [!WARNING]
    >
    > - 💣 This includes a breaking change. Please be cautious.
    ```

    - Pull Request Title
        1. Output on the first line. Do not use Markdown.
        2. Add an appropriate emoji at the beginning of the title.
    - Pull Request Description
        1. From the second line onward, provide the pull request description.
        2. Read the commit logs and files, and describe the summary of changes, technical details, and any points of caution.
            1. If there are none, do not output the section.
            2. Do not fabricate information.
        3. If a diagram of the process is needed, use mermaid.js syntax.

    ## Commit Logs and File Diffs

    {commit_logs}

    ## Pull Request Description

    ## 📒 Summary of Changes

    1. Add an appropriate emoji at the beginning of each item.

    ## ⚒ Technical Details

    1. Add an appropriate emoji at the beginning of each item.

    ## ⚠ Points of Caution

    1. Add an appropriate emoji at the beginning of each item.
    """
    return custom_prompt or default_prompt
```

変更後:

```python
def create_prompt(commit_logs: str, custom_prompt: str | None = None, locale: str = "en") -> str:
    default_prompt = f"""
    You generate a pull request title and description from commit logs and diffs.

    # Output format (STRICT)

    Your entire response MUST follow this exact shape and nothing else:

    Line 1: The pull request title.
      - Plain text only. No Markdown, no quotes, no labels, no prefix like "Title:".
      - Start with one emoji that fits the change, followed by a single space.
      - One line only. No trailing blank line before the body.

    Line 2 onward: The pull request description body in Markdown.
      - Do NOT repeat or translate any label such as "Pull Request Title",
        "Pull Request Description", "Title", "Body", or "Description".
      - Do NOT output a top-level heading for the description itself.
      - Use the section headings listed below as `##` headings (translated into the
        response language). Omit any section that has nothing meaningful to say.
      - Enclose file names in backticks.
      - You MAY use GitHub Markdown alerts (`> [!NOTE]`, `> [!TIP]`, `> [!IMPORTANT]`,
        `> [!WARNING]`, `> [!CAUTION]`) when appropriate.
      - You MAY use mermaid.js code blocks when a diagram clarifies the change.
      - Do NOT fabricate information; rely only on the commit logs and diffs.

    # Section headings to use in the body (translate into the response language)

    - 📒 Summary of Changes — bullet list, one emoji at the start of each item.
    - ⚒ Technical Details — bullet list, one emoji at the start of each item.
    - ⚠ Points of Caution — bullet list, one emoji at the start of each item.

    # Language

    Write the entire response in the locale: {locale}.

    # Example shape (do NOT copy the wording; only the structure)

    🔧 Refactor authentication helpers

    ## 📒 Summary of Changes

    - ♻️ Consolidate token validation into a single helper.

    ## ⚒ Technical Details

    - 🔐 Replace ad-hoc JWT parsing with `jwt.decode` in `auth/token.py`.

    # Commit logs and diffs

    {commit_logs}
    """
    return custom_prompt or default_prompt
```

主な差分:

1. `## Instructions` / `## Pull Request Description` / `## 📒 Summary of Changes` のような literal な markdown 見出しをプロンプト本文の見出しとしては使わず、`# Output format (STRICT)` のような単一 `#` の指示用見出しに変更（LLM が「再現すべき構造」と誤認しにくくする）
2. 箇条書きラベル `- Pull Request Title` / `- Pull Request Description` を完全に削除し、「Line 1 / Line 2 onward」形式で出力ルールを明示
3. 「`Pull Request Title` / `Pull Request Description` / `Title` / `Body` / `Description` などのラベルを翻訳・再現するな」を明示
4. 出力例 (few-shot) を 1 つだけ末尾近くに置き、「文言はコピーするな、構造だけ参照しろ」と明示
5. 末尾の literal `## Pull Request Description` 見出しは完全に削除

- [ ] **Step 2: ruff チェック**

Run:

```bash
uv run ruff check scripts/generate_pr_description.py
uv run ruff format --check scripts/generate_pr_description.py
```

Expected: いずれもパス。

- [ ] **Step 3: pytest が引き続き通ることを確認**

Run:

```bash
uv run pytest tests/ -v
```

Expected: 6 個 PASS（プロンプトは文字列なのでテストには影響しないが、念のため）。

- [ ] **Step 4: スクリプトが import / 解析エラー無く起動できることを smoke test**

Run:

```bash
API_KEY=dummy uv run python -c "
import sys
sys.path.insert(0, 'scripts')
from generate_pr_description import create_prompt
prompt = create_prompt('dummy commit log', locale='ja')
assert 'Pull Request Title' not in prompt.split('Example shape')[0] or 'Do NOT' in prompt
assert '## Pull Request Description' not in prompt
print('prompt smoke test PASS')
print('prompt length:', len(prompt))
"
```

Expected: `prompt smoke test PASS` が表示される。

- [ ] **Step 5: コミット**

```bash
git add scripts/generate_pr_description.py
git commit -m "🐛 プロンプトを書き換えて PR タイトルへのラベル文字列漏れを修正"
```

---

### Task 6: 最終検証

**Files:** なし（検証のみ）

- [ ] **Step 1: 全テストを実行**

Run:

```bash
uv run pytest tests/ -v
```

Expected: 6 個 PASS。

- [ ] **Step 2: ruff の全体チェック**

Run:

```bash
uv run ruff check .
uv run ruff format --check .
```

Expected: いずれもパス。

- [ ] **Step 3: pre-commit を全ファイルに適用**

Run:

```bash
uv run pre-commit run --all-files || true
```

Expected: 既存ファイル由来の警告は許容するが、本 PR で変更した `scripts/generate_pr_description.py` / `tests/test_generate_pr_description.py` / `pyproject.toml` には新規エラーが出ないこと。

- [ ] **Step 4: コミット履歴と差分を確認**

Run:

```bash
git log --oneline origin/main..HEAD
git diff --stat origin/main..HEAD
```

Expected: 5 個のコミット (Task 1 / 2 / 3 / 4 / 5) と、`scripts/generate_pr_description.py`・`tests/test_generate_pr_description.py`・`tests/__init__.py`・`pyproject.toml`・`uv.lock` の差分が見える。

- [ ] **Step 5: 実機検証の手順をメモ（コードには反映しない）**

本機能は OpenRouter への外部 API 呼び出しを伴うため、ユニットテストでは「ラベルが漏れた場合に剥がす」ことしか検証できない。プロンプト変更の効果は実際に PR を起こして Action を走らせる必要がある。

検証手順:

1. このブランチをマージしてタグを切る（あるいは `@main` を一時参照する）
2. 別リポジトリ（例: `tqer39/terraform-github`）で適当な PR を起こす
3. Action 実行後、PR タイトルが絵文字 + タイトル本文の形になっていること、`プルリクエストタイトル` / `プルリクエストの説明` のラベル混入が無いことを確認

---

## 自己レビュー（書き手による事前チェック）

- [x] **Spec coverage:** 根本原因（プロンプト構造）と症状（ラベル漏れ）の両方に対応するタスクがある（Task 5 = プロンプト書き換え、Task 3-4 = 後処理ガード）。
- [x] **Placeholder scan:** "TBD" / "TODO" / "implement later" / "add appropriate error handling" 等のプレースホルダーは無し。全てのコードはそのまま貼れる完全形。
- [x] **Type consistency:** `_strip_label_lines` のシグネチャは Task 3 で定義 (`(text: str) -> str`)、Task 4 で `_strip_label_lines(raw)` と呼んでおり一致。`_LABEL_NOISE_PATTERNS` も同タスク内で定義・参照。
- [x] **コミット粒度:** 5 コミット（pytest 環境追加、失敗テスト、ヘルパー実装、後処理適用、プロンプト書き換え）。各コミットは独立にレビュー可能。
