---
name: task-init
description: タスク環境の初期化
model: haiku
context: fork
disable-model-invocation: true
allowed-tools: Write, Bash(mkdir:*), Bash(pwd)
---

# タスク初期化

タスク「$ARGUMENTS」の環境を準備します。

## パス解決ルール

**重要**: タスクファイルはプロジェクトルート配下に作成します（`~/.claude/tasks/` ではありません）。

最初に Bash ツールで `pwd` を実行し、プロジェクトルートの絶対パスを取得してください。
以降のすべてのファイルパスは、取得したプロジェクトルートを先頭に付けた絶対パスで指定してください。

例: `pwd` → `/Users/yuki/dev/www/my-project` の場合
- `<PROJECT_ROOT>/.claude/tasks/$ARGUMENTS/init.md` → `/Users/yuki/dev/www/my-project/.claude/tasks/$ARGUMENTS/init.md`

## 実行手順

### ステップ1: ディレクトリ作成
Bashツールで以下のコマンドを実行してください（`<PROJECT_ROOT>` は `pwd` で取得したパスに置換）:
```
mkdir -p <PROJECT_ROOT>/.claude/tasks/$ARGUMENTS
```

### ステップ2: init.md を作成
Writeツールで `<PROJECT_ROOT>/.claude/tasks/$ARGUMENTS/init.md` を作成してください:
```markdown
<!-- 要件定義の準備をします。このタスクの概要を、簡潔に入力してください。 -->
```

### ステップ3: req.md を作成
Writeツールで `<PROJECT_ROOT>/.claude/tasks/$ARGUMENTS/req.md` を作成してください:
```markdown
# 要件定義

## タスク概要
<!-- 何を実現したいか -->

## 背景・目的
<!-- なぜこのタスクが必要か -->

## 機能要件
<!-- 具体的に追加・変更する機能 -->

## 非機能要件
<!-- パフォーマンス、セキュリティ等の要求 -->

## 影響範囲
<!-- 既存システムのどの部分に影響するか -->

## 制約事項
<!-- 技術的・時間的・リソース的制約 -->

## 既存システムとの関連性
<!-- 既存機能との連携方法 -->
```

## 完了後
「init.md にタスク概要を入力してください（実行モデル: [あなたが動作しているモデル名]）」と表示してください。
