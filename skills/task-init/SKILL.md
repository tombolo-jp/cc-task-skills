---
name: task-init
description: タスク環境の初期化
model: opus
disable-model-invocation: true
argument-hint: "<task_name> [<URL>]"
---

# タスク初期化

タスク「$ARGUMENTS[0]」の環境を準備します。

## 引数の解釈

このスキルは以下の引数を受け取ります:

- **第1引数（タスク名）**: `$ARGUMENTS[0]` — 必須。処理対象のタスク名。
- **第2引数（URL）**: `$ARGUMENTS[1]` — 任意。課題管理ツール（Backlog / GitHub / Jira / GitLab / Notion 等）や一般 Web ページの URL。指定された場合、その内容を取得して init.md に転記します。

**引数全体**: `$ARGUMENTS`

### URL のクォートについて

URL は `?` `&` `#` `=` などシェルで特別な意味を持つ文字を含むため、**シングルクォートで囲むことを推奨**します:

```bash
/task-init my-task 'https://example.com/issue?id=123&foo=bar'
```

- シングルクォートは内部を一切展開しないため最も安全です（ダブルクォートは `$`・バッククォート・`\` を展開してしまいます）。
- 特殊文字を含まない単純な URL は素のままでも動作します。
- スキルは `$ARGUMENTS[1]` を読み取る際、前後にシングル/ダブルクォートが残っていれば除去してから使用してください。

### 重要: URL の有無による分岐【最優先】

`$ARGUMENTS[1]`（URL）が指定されているかを **最初に** 判定してください。

- **URL が指定されていない場合**: 「通常モード」（後述「実行手順（URL 未指定時）」）を実行します。従来通りの空テンプレートを作成します。
- **URL が指定されている場合**: 「URL 取得モード」（後述「実行手順（URL 指定時）」）を実行します。

## パス解決ルール

**重要**: タスクファイルはプロジェクトルート配下に作成します（`~/.claude/tasks/` ではありません）。

最初に Bash ツールで `pwd` を実行し、プロジェクトルートの絶対パスを取得してください。
以降のすべてのファイルパスは、取得したプロジェクトルートを先頭に付けた絶対パスで指定してください。

例: `pwd` → `/Users/yuki/dev/www/my-project` の場合
- `<PROJECT_ROOT>/.claude/tasks/$ARGUMENTS[0]/init.md` → `/Users/yuki/dev/www/my-project/.claude/tasks/$ARGUMENTS[0]/init.md`

---

## 実行手順（URL 未指定時）

URL が指定されていない場合は、従来通りの空テンプレートを作成します。

### ステップ1: ディレクトリ作成
Bashツールで以下のコマンドを実行してください（`<PROJECT_ROOT>` は `pwd` で取得したパスに置換）:
```
mkdir -p <PROJECT_ROOT>/.claude/tasks/$ARGUMENTS[0]
```

### ステップ2: init.md を作成
Writeツールで `<PROJECT_ROOT>/.claude/tasks/$ARGUMENTS[0]/init.md` を作成してください:
```markdown
<!-- 要件定義の準備をします。このタスクの概要を、簡潔に入力してください。 -->
```

### ステップ3: req.md を作成
Writeツールで `<PROJECT_ROOT>/.claude/tasks/$ARGUMENTS[0]/req.md` を作成してください:
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

### 完了後
「init.md にタスク概要を入力してください（実行モデル: [あなたが動作しているモデル名]）」と表示してください。

---

## 実行手順（URL 指定時）

URL が指定されている場合は、その内容を取得して init.md に転記します。

> **【重要】取得手段ゼロ = 何も作らない**
> 後述「ステップA: 取得方式の決定」で利用可能な取得手段が **一つも見つからなかった** 場合は、
> **エラーメッセージを表示して即終了**し、**ディレクトリ・init.md・req.md を一切作成しないでください**。
> このため、**ディレクトリ作成（mkdir）より前に必ず「ステップA」を実行**してください。

### ステップA: 取得方式の決定（MCP 優先 → ブラウザ系フォールバック）

可能な限り MCP を利用し、無ければブラウザ系へフォールバックします。各段階のツール可用性は **`ToolSearch` の結果が `<functions>` ブロックに対象ツールを含むか** で判定してください（他スキルと同じ判定方式）。

#### A-1. サービス特化 MCP の探索（最優先）

1. URL のドメイン/サービスを判別する（例: `*.backlog.com` / `*.backlog.jp` → Backlog、`github.com` → GitHub、`*.atlassian.net` → Jira/Confluence、`gitlab.com` → GitLab、`notion.so` → Notion、それ以外 → 一般 Web ページ）。
2. 判別したサービスに対応する MCP を `ToolSearch` で探索する。URL から推測したキーワードで検索すること:
   - 例: Backlog → `ToolSearch query="backlog issue comment"`
   - 例: GitHub → `ToolSearch query="github issue pull request"`
   - 例: Jira → `ToolSearch query="jira atlassian issue"`
3. `<functions>` ブロックに該当サービスの MCP ツール（`mcp__<service>__*`）が含まれていれば、**その MCP を採用** して B へ進む。

#### A-2. ブラウザ優先フォールバックチェーン

サービス特化 MCP が見つからない場合、以下の順に探索し、**最初に利用可能になったものを採用** する:

1. **claude-in-chrome**: `ToolSearch query="select:mcp__claude-in-chrome__tabs_create_mcp,mcp__claude-in-chrome__navigate,mcp__claude-in-chrome__get_page_text"`
   → `<functions>` に含まれれば採用。
2. **chrome-devtools MCP**: `ToolSearch query="chrome devtools navigate page content"`
   → `<functions>` に `mcp__chrome-devtools__*` が含まれれば採用。
3. **Playwright**: 提供スキル一覧に `playwright-cli` スキルが存在すれば、`Skill` ツールで `playwright-cli` を利用する。
4. **WebFetch**: `ToolSearch query="select:WebFetch"`
   → `<functions>` に含まれれば採用。

#### A-3. 取得手段ゼロ時のエラー終了【必須】

A-1・A-2 のいずれでも取得手段が見つからなかった場合は、以下を **必ず** 実行してください:

1. ユーザーに以下のメッセージを表示する（省略・要約禁止）:

   > ⚠️ URL からコンテンツを取得できる手段（MCP / ブラウザ自動化 / WebFetch）が現在の環境で利用できないため、タスクを初期化できません。init.md は作成していません。

2. **ディレクトリ・init.md・req.md を一切作成せずに終了する。**

### ステップB: コンテンツ取得

採用した取得方式で対象 URL にアクセスし、以下を **漏れなく** 取得してください:

- **本文**（タイトルを含む）
- **コメント欄**（全コメント。投稿者・日時を含む）

注意点:
- ブラウザ系を使う場合は、「もっと見る」「返信を表示」等の折りたたみやページネーションを **展開してから** `get_page_text` 等で取得し、コメントを取りこぼさないこと。
- **取得した内容はそのまま改変せずに保持** すること（要約・整形・省略をしない）。

### ステップC: 添付ファイルの取得

本文・コメントに添付ファイルがある場合は、`<PROJECT_ROOT>/.claude/tasks/$ARGUMENTS[0]/attachments/` を作成して保存してください。

- **MCP**: 添付取得 API があれば利用して保存。
- **ブラウザ系**: 添付の直リンク URL を特定し、`Bash(curl ...)` 等でダウンロードして保存（認証が必要な場合はブラウザの既存セッション/Cookie を活用、または MCP のダウンロード機能を利用）。
- **WebFetch**: バイナリのダウンロードは不可。添付は取得できないため、ステップ E で未取得として明記する。

### ステップD: ディレクトリ作成と init.md の書き込み

ここまでで取得手段が確定しているので、ディレクトリを作成して init.md を書き込みます。

1. Bash ツールでディレクトリを作成（添付がある場合は attachments も）:
   ```
   mkdir -p <PROJECT_ROOT>/.claude/tasks/$ARGUMENTS[0]
   ```
2. Write ツールで `<PROJECT_ROOT>/.claude/tasks/$ARGUMENTS[0]/init.md` を以下の構成で作成:

```markdown
<!-- このタスクは URL から自動取得した内容です（改変せず転記）。 -->

# 取得元
- URL: <取得した URL>
- 取得方法: <実際に使った方式。例: claude-in-chrome / backlog MCP / WebFetch>
- 取得日時: <YYYY-MM-DD HH:MM:SS>

# 本文
<タイトルと本文を改変せず転記>

# コメント
<全コメントを改変せず転記（投稿者・日時付き）。コメントが無ければ「コメントなし」と記載>

# 添付ファイル
- attachments/<filename>（元: <attachment URL>）
<添付が無ければ「添付なし」と記載>

# 取得できなかった項目
<部分取得時のみ記載。例: WebFetch のため添付ファイルは未取得 / 認証ページのため一部コメント取得不可。完全に取得できた場合はこのセクションを省略>

---

## 要約
<取得内容の要約。このセクションのみスキルが生成する>
```

### ステップE: 部分取得の明記

取得方式の制約で一部（添付・コメント等）が取得できなかった場合でも、**タスクは中断しません**。取得できた分を転記した上で、init.md の「取得できなかった項目」セクションに、何が・なぜ取得できなかったかを明示してください。

### ステップF: req.md を作成

Write ツールで `<PROJECT_ROOT>/.claude/tasks/$ARGUMENTS[0]/req.md` を、URL 未指定時のステップ3と同じテンプレートで作成してください。

### 完了後

以下を表示してください:
- 採用した取得方式
- 取得したコメント件数・添付件数
- 取得できなかった項目（あれば）
- 「init.md に取得内容を転記しました。内容を確認してください（実行モデル: [あなたが動作しているモデル名]）」
