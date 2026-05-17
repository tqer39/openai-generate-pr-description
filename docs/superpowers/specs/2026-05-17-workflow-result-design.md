# workflow-result 集約ジョブ導入設計

- 作成日: 2026-05-17
- 対象リポジトリ: `tqer39/generate-pr-description`
- 参照: `tqer39/terraform-github` の `.github/workflows/terraform-github.yml`

## 背景

ワークスペース内の全リポジトリで、PR の Required Status Check として `workflow-result` という単一の集約ジョブを採用している。本リポジトリだけ PR 関連ワークフローが `prek.yml` / `check-version.yml` / `generate-pr-description.yml` の 3 ファイルに分散しており、`workflow-result` が存在しない。

ブランチ保護設定と運用フロー（特に `auto-merge.yml` の `check_suite: completed` トリガ）を他リポジトリと揃えるため、PR トリガーで動くワークフローを単一ファイルに統合し、末尾に `workflow-result` ジョブを追加する。

## ゴール

- PR の Required Status Check を `workflow-result` 一つに集約できる構成にする
- `terraform-github` と同じ「単一ワークフロー＋末尾 workflow-result」の構造に揃える
- 既存のジョブ動作・bot スキップ条件は維持する

## 非ゴール

- ジョブのロジック自体の変更（prek / check-version / generate-pr-description の中身は変えない）
- `auto-assign.yml` / `auto-merge.yml` / `release.yml` / `update-license-year.yml` の変更
- 新しい lint・test の追加

## アーキテクチャ

### ファイル構成の変更

| 状態 | ファイル |
| --- | --- |
| 追加 | `.github/workflows/ci.yml` |
| 削除 | `.github/workflows/prek.yml` |
| 削除 | `.github/workflows/check-version.yml` |
| 削除 | `.github/workflows/generate-pr-description.yml` |
| 無変更 | `.github/workflows/auto-assign.yml` |
| 無変更 | `.github/workflows/auto-merge.yml` |
| 無変更 | `.github/workflows/release.yml` |
| 無変更 | `.github/workflows/update-license-year.yml` |

### `ci.yml` のジョブ構成

```text
on:
  pull_request:
  push:
    branches: [main]

jobs:
  prek                       常に実行
  check-version              PR 時のみ・bot スキップ
  generate-pr-description    PR の opened/synchronize のみ・bot スキップ
  workflow-result            needs 上記 / if: always()
```

## ジョブ仕様

### prek

- 既存 `prek.yml` のロジックそのまま
- 実行条件: push（main）/ pull_request の両方
- ステップ: `actions/checkout@v6` + `j178/prek-action --all-files`

### check-version

- 既存 `check-version.yml` のロジックそのまま
- 実行条件:
  - `github.event_name == 'pull_request'`
  - かつ `github.event.action` が `opened` または `synchronize`（既存挙動を維持）
  - かつ PR 作成者が `renovate[bot]` / `tqer39-apps[bot]` 以外
- ステップ: `actions/checkout@v6 fetch-depth:0` + バージョン比較スクリプト

### generate-pr-description

- 既存 `generate-pr-description.yml` のロジックそのまま
- 実行条件:
  - `github.event_name == 'pull_request'`
  - かつ `github.event.action` が `opened` または `synchronize`
  - かつ `github.event.pull_request.base.ref == 'main'`（既存の `branches: [main]` 相当）
  - かつ PR 作成者が `renovate[bot]` / `tqer39-apps[bot]` 以外
- permissions: `pull-requests: write`, `contents: read`
- ステップ: `actions/checkout@v6 fetch-depth:0` + `uses: ./`（model: `openai/gpt-4o`, locale: `ja`）

### workflow-result

- `needs: [prek, check-version, generate-pr-description]`
- `if: always()`（skip / failure を含めて必ず評価）
- ロジック:
  - `needs.prek.result == "failure"` → exit 1
  - `needs.check-version.result == "failure"` → exit 1
  - `needs.generate-pr-description.result == "failure"` → `::warning::` のみ出力、exit 0（非ブロック）
  - それ以外は exit 0

#### 非ブロック扱いの根拠（generate-pr-description）

副作用ジョブ（PR 本文書き換え）であり、OpenRouter API 障害で PR が一律マージ不可になる事態を避けるため、品質ゲートとは分離する。

## イベント別の挙動

トップレベルの `pull_request:` トリガはデフォルトで `[opened, synchronize, reopened]` のみ発火する（`ready_for_review` 等は対象外）。

| トリガ | prek | check-version | generate-pr-description | workflow-result |
| --- | --- | --- | --- | --- |
| `pull_request` opened/synchronize（人間 PR, base=main） | run | run | run | pass if prek/check-version success |
| `pull_request` reopened（人間 PR） | run | skip | skip | pass if prek success |
| `pull_request` opened/synchronize（renovate / tqer39-apps PR） | run | skip | skip | pass if prek success |
| `push`（main） | run | skip | skip | pass if prek success |

## ワークフロー設定

```yaml
name: CI

on:
  pull_request:
  push:
    branches: [main]

concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true

permissions:
  contents: read
```

- ワークフロー全体は最小権限（`contents: read`）。`generate-pr-description` ジョブのみ `pull-requests: write` を昇格して付与。
- 既存 3 ファイルは個別 `concurrency` group を持っていたが、統合後は `ci-...` に一本化。
- `cancel-in-progress: true` を追加して連続 push 時の無駄なラン消費を抑制。

## 移行手順

ブランチ保護の Required Status Check 名は GitHub UI 側で管理されているため、ワークフロー変更とブランチ保護変更を 2 PR に分割する。

1. **PR 1: `ci.yml` 追加**
   - `.github/workflows/ci.yml` を追加（旧 3 ファイルは残す）
   - この PR では新旧両方のジョブが走る。両方とも green になることを確認
2. **GitHub UI 操作: ブランチ保護更新**
   - PR 1 マージ後、`main` のブランチ保護で Required status checks を以下に変更:
     - 旧: `prek` / `check-version` / `generate-pr-description`
     - 新: `workflow-result`
3. **PR 2: 旧ファイル削除**
   - `.github/workflows/prek.yml` / `check-version.yml` / `generate-pr-description.yml` を削除
   - この PR が問題なくマージできれば移行完了

ステップ 2 を飛ばして旧ファイルを先に削除すると、Required チェックが skipped 扱いになり PR をマージできなくなる。順序厳守。

## テスト計画

- PR 1 の段階で:
  - 人間 PR で `prek` / `check-version` / `generate-pr-description` / `workflow-result` が全て表示され、success になること
  - renovate PR で `check-version` / `generate-pr-description` が skipped、`workflow-result` が success になること
- PR 2 マージ後、`auto-merge.yml` が `check_suite: completed` で正しく発火し続けること（claude-auto ラベル付き PR で検証）
- `generate-pr-description` ジョブを意図的に失敗させた場合に `workflow-result` が success のまま `::warning::` を出すこと（手動検証は任意）

## リスクと対策

| リスク | 対策 |
| --- | --- |
| ブランチ保護更新を忘れて PR 2 を出すと merge 不可 | 移行手順に明記、PR 2 の説明に手順チェックリストを含める |
| 旧 3 ファイルを残したまま放置すると重複実行で API クォータ消費 | PR 2 を必ずセットで実施。PR 1 マージ後 24h 以内を目安 |
| `auto-merge.yml` の `check_suite: completed` が `workflow-result` 完了を検知しない | check_suite はワークフロー単位で発火するため、`ci.yml` 完了で必ず発火する。動作確認は移行後に claude-auto ラベルで実施 |
