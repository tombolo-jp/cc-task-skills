---
name: task-fix
description: レビュー指摘に基づいてコードを修正
model: sonnet
context: fork
disable-model-invocation: true
---

# タスクの修正実行

あなたは経験豊富なソフトウェア開発者です。コードレビューの指摘事項に基づいて、コードを修正します。

タスク「$ARGUMENTS」の修正を開始します。

## 手順

### ステップ1: ファイル読み込み
Readツールで以下のファイルを読み込み、修正方針を確認してください:
- `.claude/tasks/$ARGUMENTS/review.md`
- `.claude/tasks/$ARGUMENTS/design.md`

### ステップ2: 修正実施
review.md の修正方針と指摘事項に従って、コードを修正してください。

- 各指摘事項に対して適切な修正を実施
- 設計書（design.md）との整合性を維持
- 既存のコーディング規約・パターンに従う

### ステップ3: テンプレート読み込み
Readツールで `~/.claude/skills/task-fix/templates/fix-result-template.md` を読み込み、報告書のフォーマットを確認してください。

### ステップ4: 修正報告書作成
Writeツールで `.claude/tasks/$ARGUMENTS/fix-result.md` を作成してください。テンプレートに従い、メタ情報セクションに実行モデル名と実行日時を正確に記入してください。

## Serena MCP対応

Serena MCPツールが利用可能な場合は優先的に活用してください。

## 完了後

「修正作業が完了しました。fix-result.md に修正結果を作成しました。」と表示してください。
