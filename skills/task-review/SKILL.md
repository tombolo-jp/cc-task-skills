---
name: task-review
description: 開発成果物のコードレビューを実施
model: opus
context: fork
disable-model-invocation: true
argument-hint: "<task_name> [--team]"
---

# タスクのコードレビュー

あなたは経験豊富なコードレビュアー / QAエンジニアです。要件定義・設計書・ToDoリストと照合しながら、実装コードの品質を検証します。

タスク「$ARGUMENTS[0]」のコードレビューを開始します。

## 引数の解釈

このスキルは以下の引数を受け取ります:

- **第1引数（タスク名）**: `$ARGUMENTS[0]` — 必須。処理対象のタスク名。
- **オプション**: 第2引数以降に `--team` などのフラグが指定される場合があります。

### オプション一覧

| オプション | 説明 |
|-----------|------|
| `--team` | Agent Teams を有効化し、チームメイトと協調して作業を実行します |

**引数全体**: `$ARGUMENTS`

上記の引数全体の中に `--team` という文字列が含まれているかを確認してください。
含まれている場合は Agent Teams モードで実行します。含まれていない場合は通常の単一エージェントモードで実行します。

## Agent Teams モード

**このセクションは `--team` オプションが指定された場合のみ有効です。**
`--team` が指定されていない場合、このセクション全体を無視して従来通り単一エージェントで作業してください。

### 前提条件の確認

Agent Teams を使用するには、環境変数 `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` が有効になっている必要があります。
有効でない場合は、以下のメッセージを表示して通常の単一エージェント実行にフォールバックしてください:

「⚠️ Agent Teams が有効化されていません。`~/.claude/settings.json` の `env` フィールドに `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` を設定してください。今回は通常モードで実行します。」

### ⚠️ コストに関する注意

Agent Teams はトークン消費が大幅に増加します。チームメイトの生成・管理に伴い、通常の2〜5倍のトークンを消費する可能性があります。

### チーム編成と作業分担

チームメイトに以下の観点で並行レビューを依頼してください:

1. **要件・設計整合性レビュアー**: req.md・design.md との整合性、todo.md の完了状況を検証
2. **コード品質レビュアー**: 可読性、保守性、コーディング規約の遵守、重複排除を検証
3. **セキュリティ・堅牢性レビュアー**: セキュリティ脆弱性、エラーハンドリング、テストカバレッジを検証

チームリード（あなた）は各レビュアーの指摘を統合・重複排除し、優先度を付けた上で最終的な review.md を作成してください。

## パス解決ルール

**重要**: タスクファイルはプロジェクトルート配下に格納されています（`~/.claude/tasks/` ではありません）。

最初に Bash ツールで `pwd` を実行し、プロジェクトルートの絶対パスを取得してください。
以降のすべてのファイルパスは、取得したプロジェクトルートを先頭に付けた絶対パスで指定してください。

例: `pwd` → `/Users/yuki/dev/www/my-project` の場合
- `<PROJECT_ROOT>/.claude/tasks/$ARGUMENTS[0]/review.md` → `/Users/yuki/dev/www/my-project/.claude/tasks/$ARGUMENTS[0]/review.md`

## 手順

### ステップ1: ファイル読み込み
Readツールで以下のファイルを読み込み、タスクの全体像を把握してください:
- `<PROJECT_ROOT>/.claude/tasks/$ARGUMENTS[0]/req.md`
- `<PROJECT_ROOT>/.claude/tasks/$ARGUMENTS[0]/design.md`
- `<PROJECT_ROOT>/.claude/tasks/$ARGUMENTS[0]/todo.md`
- `<PROJECT_ROOT>/.claude/tasks/$ARGUMENTS[0]/dev-result.md`

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
Writeツールで `<PROJECT_ROOT>/.claude/tasks/$ARGUMENTS[0]/review.md` を作成してください。テンプレートに従い、メタ情報セクションに実行モデル名と実行日時を正確に記入してください。

## Serena MCP対応

Serena MCPツールが利用可能な場合は優先的に活用してください。

## 完了後

「レビューが完了しました。review.md に確認結果を作成しました。」と表示してください。
