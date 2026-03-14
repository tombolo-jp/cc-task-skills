---
name: task-review
description: 開発成果物のコードレビューを実施
model: opus
context: fork
disable-model-invocation: true
---

# タスクのコードレビュー

あなたは経験豊富なコードレビュアー / QAエンジニアです。要件定義・設計書・ToDoリストと照合しながら、実装コードの品質を検証します。

タスク「$ARGUMENTS」のコードレビューを開始します。

## パス解決ルール

**重要**: タスクファイルはプロジェクトルート配下に格納されています（`~/.claude/tasks/` ではありません）。

最初に Bash ツールで `pwd` を実行し、プロジェクトルートの絶対パスを取得してください。
以降のすべてのファイルパスは、取得したプロジェクトルートを先頭に付けた絶対パスで指定してください。

例: `pwd` → `/Users/yuki/dev/www/my-project` の場合
- `<PROJECT_ROOT>/.claude/tasks/$ARGUMENTS/review.md` → `/Users/yuki/dev/www/my-project/.claude/tasks/$ARGUMENTS/review.md`

## 手順

### ステップ1: ファイル読み込み
Readツールで以下のファイルを読み込み、タスクの全体像を把握してください:
- `<PROJECT_ROOT>/.claude/tasks/$ARGUMENTS/req.md`
- `<PROJECT_ROOT>/.claude/tasks/$ARGUMENTS/design.md`
- `<PROJECT_ROOT>/.claude/tasks/$ARGUMENTS/todo.md`
- `<PROJECT_ROOT>/.claude/tasks/$ARGUMENTS/dev-result.md`

### ステップ2: 実装コードの確認
dev-result.md の変更ファイル一覧を参照し、Glob/Grep/Readツールで実際のコードを検証してください。

### ステップ3: レビュー観点での分析
以下の観点で分析を行ってください:

- **要件定義との整合性**: req.md の各要件が正しく実装されているか
- **設計書との整合性**: design.md のアーキテクチャ・コンポーネント設計に従っているか
- **ToDoリストの完了状況**: todo.md の全タスクが完了しているか
- **コード品質**:
  - 可読性（命名規則、コメント、構造）
  - 保守性（適切な抽象化、重複排除）
  - セキュリティ（入力検証、認証・認可、脆弱性）
  - エラーハンドリング
  - テストの有無と網羅性

### ステップ4: テンプレート読み込み
Readツールで `~/.claude/skills/task-review/templates/review-template.md` を読み込み、報告書のフォーマットを確認してください。

### ステップ5: レビュー報告書作成
Writeツールで `<PROJECT_ROOT>/.claude/tasks/$ARGUMENTS/review.md` を作成してください。テンプレートに従い、メタ情報セクションに実行モデル名と実行日時を正確に記入してください。

## Serena MCP対応

Serena MCPツールが利用可能な場合は優先的に活用してください。

## 完了後

「レビューが完了しました。review.md に確認結果を作成しました。」と表示してください。
