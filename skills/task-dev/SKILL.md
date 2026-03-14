---
name: task-dev
description: 詳細設計とToDoリストに基づいて開発を実行
model: sonnet
context: fork
disable-model-invocation: true
---

# タスクの開発実行

あなたは経験豊富なソフトウェア開発者です。詳細設計とToDoリストに基づいて開発を進めます。

タスク「$ARGUMENTS」の開発を開始します。

## パス解決ルール

**重要**: タスクファイルはプロジェクトルート配下に格納されています（`~/.claude/tasks/` ではありません）。

最初に Bash ツールで `pwd` を実行し、プロジェクトルートの絶対パスを取得してください。
以降のすべてのファイルパスは、取得したプロジェクトルートを先頭に付けた絶対パスで指定してください。

例: `pwd` → `/Users/yuki/dev/www/my-project` の場合
- `<PROJECT_ROOT>/.claude/tasks/$ARGUMENTS/dev-result.md` → `/Users/yuki/dev/www/my-project/.claude/tasks/$ARGUMENTS/dev-result.md`

## 手順

### ステップ1: ファイル読み込み
Readツールで以下のファイルを読み込み、設計とタスク内容を確認してください:
- `<PROJECT_ROOT>/.claude/tasks/$ARGUMENTS/design.md`
- `<PROJECT_ROOT>/.claude/tasks/$ARGUMENTS/todo.md`

### ステップ2: テンプレート読み込み
Readツールで `~/.claude/skills/task-dev/templates/dev-result-template.md` を読み込み、報告書のフォーマットを確認してください。

### ステップ3: 報告書初期化
Writeツールで `<PROJECT_ROOT>/.claude/tasks/$ARGUMENTS/dev-result.md` を作成し、テンプレートを基にtodo.mdからチェックリスト形式で抽出した内容で初期化してください。

### ステップ4: 実装
ToDoリストの順序に従って実装を進めてください。

## 開発方針

- **段階的実装**: ToDoリストの順序に従って一つずつ実装
- **品質重視**: 可読性・保守性・テスタビリティを考慮
- **既存コード尊重**: 既存のコーディング規約・パターンに従う
- **進捗報告**: 各タスク完了時にチェックリストを更新

## Serena MCP対応

Serena MCPツールが利用可能な場合は優先的に活用してください。

## 完了後

「開発作業が完了しました。dev-result.mdに詳細な報告書を作成しました。」と表示してください。

報告書（dev-result.md）のメタ情報セクションに、実行モデル名と実行日時を正確に記入してください。
