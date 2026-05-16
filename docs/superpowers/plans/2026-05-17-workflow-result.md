# workflow-result 集約ジョブ導入 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** PR トリガーで動く 3 つのワークフロー（prek / check-version / generate-pr-description）を単一の `ci.yml` に統合し、末尾に `workflow-result` ジョブを置いて PR の Required Status Check を 1 つに集約する。

**Architecture:** `terraform-github` リポジトリと同じ「単一ワークフロー + 末尾 workflow-result」構造に揃える。新ファイル `ci.yml` を先に追加し（PR 1）、ブランチ保護を UI で切り替えてから、旧 3 ファイルを削除する（PR 2）。

**Tech Stack:** GitHub Actions（YAML）、`actions/checkout@v6`、`j178/prek-action@v2`、本リポジトリ自身の Composite Action（`uses: ./`）。

**参照スペック:** `docs/superpowers/specs/2026-05-17-workflow-result-design.md`

---

## File Structure

| 状態 | ファイル | 責務 |
| --- | --- | --- |
| 追加 (PR 1) | `.github/workflows/ci.yml` | PR ゲート用の統合ワークフロー。4 ジョブを含む |
| 削除 (PR 2) | `.github/workflows/prek.yml` | 統合先 ci.yml に移管済み |
| 削除 (PR 2) | `.github/workflows/check-version.yml` | 統合先 ci.yml に移管済み |
| 削除 (PR 2) | `.github/workflows/generate-pr-description.yml` | 統合先 ci.yml に移管済み |

無変更ファイル: `auto-assign.yml`, `auto-merge.yml`, `release.yml`, `update-license-year.yml`

---

## Task 1: `ci.yml` を新規作成する（PR 1 のメインコミット）

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: ブランチを作成**

```bash
git checkout -b feat/add-ci-workflow-result main
```

- [ ] **Step 2: `.github/workflows/ci.yml` を作成**

以下の内容で新規作成する。

```yaml
---
name: CI

on:
  pull_request:
  push:
    branches:
      - main

concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true

permissions:
  contents: read

jobs:
  prek:
    name: prek
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - name: Checkout
        uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd # v6
        with:
          ref: ${{ github.head_ref }}

      - name: prek
        uses: j178/prek-action@cbc2f23eb5539cf20d82d1aabd0d0ecbcc56f4e3 # v2
        with:
          extra-args: --all-files

  check-version:
    name: check-version
    runs-on: ubuntu-latest
    timeout-minutes: 5
    if: >-
      github.event_name == 'pull_request' &&
      contains(fromJSON('["opened", "synchronize"]'), github.event.action) &&
      contains(fromJSON('["renovate[bot]", "tqer39-apps[bot]"]'), github.event.pull_request.user.login) == false
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd # v6
        with:
          fetch-depth: 0

      - name: Check version is bumped
        run: |
          LATEST_TAG=$(git tag -l 'v[0-9]*.[0-9]*.[0-9]*' --sort=-v:refname | grep -v '-' | head -1)
          LATEST_TAG=${LATEST_TAG:-v0.0.0}
          TAG_VERSION=${LATEST_TAG#v}

          CURRENT_VERSION=$(grep '^version = ' pyproject.toml | head -1 | sed 's/version = "\(.*\)"/\1/')

          echo "最新タグ: ${LATEST_TAG} (${TAG_VERSION})"
          echo "pyproject.toml: ${CURRENT_VERSION}"

          IFS='.' read -r TAG_MAJOR TAG_MINOR TAG_PATCH <<< "${TAG_VERSION}"
          IFS='.' read -r CUR_MAJOR CUR_MINOR CUR_PATCH <<< "${CURRENT_VERSION}"

          TAG_NUM=$((TAG_MAJOR * 1000000 + TAG_MINOR * 1000 + TAG_PATCH))
          CUR_NUM=$((CUR_MAJOR * 1000000 + CUR_MINOR * 1000 + CUR_PATCH))

          if [ "${CUR_NUM}" -le "${TAG_NUM}" ]; then
            echo "::error::pyproject.toml のバージョン (${CURRENT_VERSION}) が最新タグ (${LATEST_TAG}) より新しくありません。バージョンを更新してください。"
            exit 1
          fi

          echo "OK: バージョン ${CURRENT_VERSION} は最新タグ ${LATEST_TAG} より新しいです。"

  generate-pr-description:
    name: generate-pr-description
    runs-on: ubuntu-latest
    timeout-minutes: 10
    if: >-
      github.event_name == 'pull_request' &&
      contains(fromJSON('["opened", "synchronize"]'), github.event.action) &&
      github.event.pull_request.base.ref == 'main' &&
      contains(fromJSON('["renovate[bot]", "tqer39-apps[bot]"]'), github.event.pull_request.user.login) == false
    permissions:
      pull-requests: write
      contents: read
    steps:
      - uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd # v6
        with:
          fetch-depth: 0

      - uses: ./
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
          api-key: ${{ secrets.OPENROUTER_API_KEY }}
          model: 'openai/gpt-4o'
          locale: 'ja'

  workflow-result:
    name: workflow-result
    needs: [prek, check-version, generate-pr-description]
    if: always()
    runs-on: ubuntu-latest
    timeout-minutes: 2
    steps:
      - name: Check workflow result
        run: |
          if [ "${{ needs.prek.result }}" == "failure" ]; then
            echo "prek failed"
            exit 1
          fi
          if [ "${{ needs.check-version.result }}" == "failure" ]; then
            echo "check-version failed"
            exit 1
          fi
          if [ "${{ needs.generate-pr-description.result }}" == "failure" ]; then
            echo "::warning::generate-pr-description failed (non-blocking)"
          fi
          echo "All required jobs completed successfully"
```

- [ ] **Step 3: YAML 構文チェック**

Run:
```bash
python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"
```
Expected: エラー出力なし、終了コード 0

- [ ] **Step 4: actionlint で静的検証**

Run:
```bash
# actionlint が mise や brew で入っていれば
actionlint .github/workflows/ci.yml 2>&1 || echo "actionlint not installed; skip"
```
Expected: エラーなし、または "not installed; skip"

- [ ] **Step 5: 旧ワークフローと挙動が衝突しないことを確認**

このコミットでは旧 3 ファイル（`prek.yml`, `check-version.yml`, `generate-pr-description.yml`）は残す。PR 1 では新旧両方のジョブが並列実行され、緑になることを後続ステップで確認する。

旧ファイルが存在することを確認:
```bash
ls .github/workflows/prek.yml .github/workflows/check-version.yml .github/workflows/generate-pr-description.yml
```
Expected: 3 ファイル全て表示される

- [ ] **Step 6: コミット**

```bash
git add .github/workflows/ci.yml
git commit -m "$(cat <<'EOF'
✨ workflow-result 集約のための ci.yml を追加

prek / check-version / generate-pr-description を単一ワークフローに統合し、
末尾に workflow-result ジョブで集約。旧 3 ファイルは別 PR で削除予定。

参照: docs/superpowers/specs/2026-05-17-workflow-result-design.md
EOF
)"
```

- [ ] **Step 7: push して PR を作成**

```bash
git push -u origin feat/add-ci-workflow-result
gh pr create --base main --title "✨ workflow-result 集約のための ci.yml を追加" --body "$(cat <<'EOF'
## Summary
- 新規 `.github/workflows/ci.yml` を追加（prek / check-version / generate-pr-description / workflow-result の 4 ジョブ）
- 旧 3 ファイルは本 PR では残し、別 PR で削除する
- 設計書: `docs/superpowers/specs/2026-05-17-workflow-result-design.md`

## Test plan
- [ ] 本 PR で新旧両方のチェックが green になること
- [ ] `workflow-result` ジョブが PR チェック一覧に表示されること
- [ ] PR マージ後にブランチ保護を UI で更新する手順を実施する

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

- [ ] **Step 8: GitHub Actions の結果を確認**

`gh pr checks` または PR ページでチェック状態を確認。

Run:
```bash
gh pr checks --watch
```

Expected: 以下のチェックが全て pass（緑）になる:
- `prek` (旧ワークフロー)
- `check-version` (旧ワークフロー)
- `generate-pr-description` (旧ワークフロー)
- `CI / prek` (新ワークフロー)
- `CI / check-version` (新ワークフロー)
- `CI / generate-pr-description` (新ワークフロー)
- `CI / workflow-result` (新ワークフロー) ← **これが今回の主役**

もし `workflow-result` が failure の場合、`gh run view --log-failed` でログを確認し、`needs.<job>.result` 判定ロジックの誤りを修正する。

- [ ] **Step 9: PR をマージ**

レビュー後（または承認後）:
```bash
gh pr merge --squash --delete-branch
```

---

## 手動ステップ: ブランチ保護を UI で更新

Task 1 マージ後、Task 2 着手前に必ず実施する。**この手順を飛ばすと Task 2 の PR がマージ不可になる。**

- [ ] **Step 1: ブランチ保護ページを開く**

```bash
gh browse --settings
```
または `https://github.com/tqer39/generate-pr-description/settings/branches` に直接アクセス。

- [ ] **Step 2: `main` の保護ルールを編集**

"Require status checks to pass before merging" の中の Required status checks リストを以下のように変更:

- 削除: `prek`
- 削除: `check-version`
- 削除: `generate-pr-description`
- 追加: `workflow-result`

- [ ] **Step 3: 設定を保存し、CLI で確認**

```bash
gh api "repos/tqer39/generate-pr-description/branches/main/protection" \
  --jq '.required_status_checks.contexts'
```
Expected: `["workflow-result"]` のみが表示される（または `workflow-result` を含む配列）

---

## Task 2: 旧 3 ワークフローファイルを削除する（PR 2）

**Files:**
- Delete: `.github/workflows/prek.yml`
- Delete: `.github/workflows/check-version.yml`
- Delete: `.github/workflows/generate-pr-description.yml`

**前提:** Task 1 がマージ済み、かつ手動ステップ（ブランチ保護更新）が完了していること。

- [ ] **Step 1: 最新 main から新ブランチを作成**

```bash
git checkout main
git pull
git checkout -b chore/remove-legacy-workflows
```

- [ ] **Step 2: 旧ファイルを削除**

```bash
git rm .github/workflows/prek.yml
git rm .github/workflows/check-version.yml
git rm .github/workflows/generate-pr-description.yml
```

- [ ] **Step 3: 削除されたことを確認**

Run:
```bash
ls .github/workflows/
```
Expected: 残るのは `auto-assign.yml`, `auto-merge.yml`, `ci.yml`, `release.yml`, `update-license-year.yml` の 5 ファイル

- [ ] **Step 4: コミット**

```bash
git commit -m "$(cat <<'EOF'
🔥 統合済みの旧ワークフロー 3 ファイルを削除

prek.yml / check-version.yml / generate-pr-description.yml は
ci.yml に統合済み。ブランチ保護の Required Status Check も
workflow-result に切り替え済み。

参照: docs/superpowers/specs/2026-05-17-workflow-result-design.md
EOF
)"
```

- [ ] **Step 5: push して PR を作成**

```bash
git push -u origin chore/remove-legacy-workflows
gh pr create --base main --title "🔥 統合済みの旧ワークフロー 3 ファイルを削除" --body "$(cat <<'EOF'
## Summary
- `prek.yml` / `check-version.yml` / `generate-pr-description.yml` を削除
- 機能は `ci.yml` に統合済み（前 PR）
- ブランチ保護の Required Status Check は既に `workflow-result` に切り替え済み

## Test plan
- [ ] `ci.yml` のジョブ（prek / check-version / generate-pr-description / workflow-result）が pass すること
- [ ] 削除した旧ワークフローのチェックが PR 一覧から消えていること
- [ ] `workflow-result` 単独で merge 可能になっていること

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

- [ ] **Step 6: GitHub Actions の結果を確認**

Run:
```bash
gh pr checks --watch
```

Expected: `CI / workflow-result` を含む `ci.yml` の全ジョブが pass。旧 3 ファイルのチェックは表示されない。

- [ ] **Step 7: ブランチ保護が正しく機能していることを目視確認**

PR ページで "Required" バッジが `workflow-result` 系チェックに付いていることを確認。`prek` / `check-version` / `generate-pr-description` の単独チェックは Required バッジが付いていないこと（または存在しないこと）。

- [ ] **Step 8: PR をマージ**

```bash
gh pr merge --squash --delete-branch
```

---

## Task 3: 移行後の動作確認

**Files:** 変更なし（観察のみ）

- [ ] **Step 1: 次の Renovate PR で挙動を観察**

Renovate PR が来たら以下を確認:

- `CI / prek` が run（pass する想定）
- `CI / check-version` が skipped
- `CI / generate-pr-description` が skipped
- `CI / workflow-result` が pass

確認コマンド:
```bash
gh pr list --author "app/renovate" --limit 5
gh pr checks <PR_NUMBER>
```

- [ ] **Step 2: claude-auto ラベル付き PR で auto-merge 動作を確認**

任意の小さな PR を作り、`claude-auto` ラベルを付けて以下を確認:

- `ci.yml` の全ジョブが完了 → `check_suite: completed` が発火
- `auto-merge.yml` が起動し、`gh pr merge --auto --squash` が成功

確認:
```bash
gh run list --workflow=auto-merge.yml --limit 3
```
Expected: 直近の auto-merge ランが success

- [ ] **Step 3: 異常系の動作確認（任意）**

時間に余裕があれば、`generate-pr-description` ジョブを意図的に失敗させる検証 PR を作成（例: 一時的に `api-key` を無効値に上書き）し、以下を確認:

- `CI / generate-pr-description` が failure
- `CI / workflow-result` は pass（`::warning::` を出力）
- PR は merge 可能な状態

検証後、変更は revert して破棄する。

---

## 完了基準

- `.github/workflows/ci.yml` が存在し、4 ジョブ全てが期待通り動作する
- 旧 3 ファイル（`prek.yml`, `check-version.yml`, `generate-pr-description.yml`）が削除されている
- `main` ブランチ保護の Required Status Check が `workflow-result` のみ（または `workflow-result` を含む構成）
- Renovate PR / 人間 PR / push（main）の各ケースで `workflow-result` が pass する
- `auto-merge.yml` が引き続き機能する
