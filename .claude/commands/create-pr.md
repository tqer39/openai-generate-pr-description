---
name: create-pr
description: 現在のブランチから PR を作成する（自動 push + claude-auto ラベル付与）
allowed-tools: [Bash]
---

# Create PR

現在のブランチから main に対して PR を作成する。未 push なら自動で push し、`claude-auto` ラベルを付与する。

## 手順

### 1. ブランチの確認

- `git branch --show-current` で現在のブランチ名を取得する
- ブランチが `main` の場合は **エラーを表示して終了** する

### 2. Push 状態の確認と自動 Push

- `git status` で未コミットの変更がないか確認する（あれば警告を表示して終了）
- `git rev-parse --abbrev-ref @{upstream}` でリモート追跡ブランチを確認する
- 追跡ブランチがない、またはリモートに未 push のコミットがある場合:
  - `git push -u origin <ブランチ名>` を実行する

### 3. 既存 PR の確認

- `gh pr view --json url --jq '.url'` で既存の PR を確認する
- PR が既に存在する場合は URL を表示して終了する

### 4. PR の作成

- 以下のコマンドで PR を作成する:

```bash
gh pr create --base main --fill --label claude-auto
```

### 5. 結果の表示

- 作成された PR の URL を表示する

## 禁止事項

- `main` ブランチでの PR 作成
- `git push --force` の使用
- PR のタイトルや説明文のカスタマイズ（ワークフローが自動生成するため `--fill` を使用）
