# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository contains a collection of custom skills for Claude Code that implement a task-based development workflow. The skills provide a structured approach to software development with 8 distinct phases: initialization, requirements, design, planning, implementation, review, fix, and verification.

## Skill Architecture

The repository contains 8 interconnected skills that work together (task-init excluded from `--team` option support):

1. **task-design** - Analyzes existing systems and creates technical design. Supports `--team` option.
2. **task-dev** - Executes implementation based on todo list and creates development report. Supports `--team` option.
3. **task-fix** - Fixes code based on review feedback. Supports `--team` option.
4. **task-init** - Creates task environment and requirements gathering. (No `--team` support — uses haiku model)
5. **task-req** - Creates requirements draft from raw customer requests. Supports `--team` option.
6. **task-review** - Reviews implementation against requirements, design, and code quality. Supports `--team` option.
7. **task-todo** - Breaks down design into actionable development tasks with effort estimation. Supports `--team` option.
8. **task-verify** - Generates manual verification procedure document. Supports `--team` option.

Each skill is a directory under `skills/` containing a `SKILL.md` file and optional `templates/` subdirectory for report templates.

## Task Management Structure

Each task follows a standardized directory structure:
```
.claude/tasks/{task_name}/
├── init.md         # Raw customer requests
├── req.md          # Requirements definition
├── design.md       # Technical design
├── todo.md         # Implementation todo list with effort estimation
├── dev-result.md   # Development completion report
├── review.md       # Code review report
├── fix-result.md   # Fix completion report
└── verify.md       # Manual verification procedure
```

**Important**: Task files are always created under the **project root's** `.claude/tasks/`, not `~/.claude/tasks/`. Each skill resolves the project root via `pwd` at the beginning of execution and uses absolute paths for all file operations.

## Model Configuration

Each skill specifies an appropriate model alias via Frontmatter for optimal cost-performance balance:

| Skill | Model | Alias | Reason |
|-------|-------|-------|--------|
| task-init | **Haiku** | `haiku` | Simple file creation, cost reduction |
| task-req | **Opus** | `opus` | High-precision design required |
| task-design | **Opus** | `opus` | High-precision design required |
| task-todo | **Opus** | `opus` | High-precision planning and estimation |
| task-dev | **Opus** | `opus` | High-precision implementation; avoids Sonnet 1M context API requirement |
| task-review | **Opus** | `opus` | High-precision review required |
| task-fix | **Opus** | `opus` | High-precision fixes; avoids Sonnet 1M context API requirement |
| task-verify | **Opus** | `opus` | High-precision verification procedure generation |

Model aliases (`haiku`, `opus`) are used instead of full model IDs. This ensures automatic resolution to the latest model version when Anthropic updates models. The `sonnet` alias is intentionally avoided because Claude Code currently requires an API key for Sonnet's 1M context window, while Opus 1M is included in Pro/Max subscriptions without extra charge.

## モデル確認の仕組み

各コマンドは、出力する報告書の末尾に「メタ情報」セクションを含めます。
スキル本体が自己申告する形で、実際に使用されたモデル名と実行日時が記録されます。
これにより、ユーザーは生成物が想定したモデルで作成されたか確認できます。

### メタ情報のフォーマット

```markdown
## メタ情報
- 実行モデル: [モデル名]
- 実行日時: [日時]
- Agent Teams: [有効 / 無効（指定なし） / 無効（フォールバック）]
```

「Agent Teams」フィールドは以下の3値のいずれかで記録します:

| 状態 | 値 |
|------|-----|
| `--team` 指定あり、かつ ① 環境変数有効、② TeamCreate ツール利用可能、③ チームメイトが少なくとも 1 体稼働、の **すべて**を満たす | `有効` |
| `--team` 指定なし | `無効（指定なし）` |
| `--team` 指定あり、かつ環境変数無効/ツール利用不可/チームメイト spawn 失敗のいずれか | `無効（フォールバック）` |

> **重要**: `TeamCreate` を呼んだだけでチームメイトが稼働しなかった場合は **`有効` ではなく `無効（フォールバック）`** と記録すること。環境変数が有効であっても、チームメイトの実際の稼働が確認できない場合は `有効` とみなしません。

## agent フィールドについて

現在のコマンドはすべてファイル書き込みを伴うため、`agent` フィールドは指定していません（デフォルトの汎用エージェント）。
将来的にread-only分析コマンドを追加する場合は、`agent: Explore` の指定を検討してください。

## Serena MCP Integration

All skills support Serena MCP (Model Context Protocol). When Serena MCP tools are available, skills will:
- Automatically detect and utilize Serena MCP capabilities
- Prioritize Serena MCP functions for document generation, analysis, and validation
- Fall back to traditional methods when Serena MCP is unavailable

## Key Skill Behaviors

### /task-init {task_name}
- Creates `.claude/tasks/{task_name}/` directory structure
- Creates init.md for capturing raw customer requests
- Generates templated req.md with sections for overview, background, functional/non-functional requirements, impact analysis, constraints, and system relationships
- Note: design.md, todo.md, dev-result.md, review.md, fix-result.md, verify.md are created by their respective skills (task-design, task-todo, task-dev, task-review, task-fix, task-verify)
- **Serena MCP**: Utilizes Serena MCP for file creation and template generation when available

### /task-req {task_name} [--team]
- Reads raw customer requests from init.md
- Analyzes and structures the information into req.md
- Creates a draft requirements document from ambiguous requests
- **`--team` option**: Deploys a market/tech research agent and an impact analysis agent in parallel; team lead integrates results into req.md
- **Serena MCP**: Utilizes Serena MCP for requirements analysis and document generation when available

### /task-design {task_name} [--team]
- Reads req.md to understand task scope
- Analyzes existing project structure to maintain consistency
- Creates comprehensive design.md covering architecture, components, file structure, data design, API design, error handling, testing strategy, and performance/security considerations
- **`--team` option**: Deploys data design, API/interface design, and security/performance agents in parallel; team lead integrates results into design.md
- **Serena MCP**: Utilizes Serena MCP for design document creation, analysis, and validation when available

### /task-todo {task_name} [--team]
- Reads req.md and design.md to understand technical requirements
- Reads effort estimation template from `templates/todo-template.md`
- Creates structured todo.md with implementation order, task breakdown, deliverables, priorities, and checkpoints
- Performs comprehensive effort estimation for manual implementation by intermediate-level programmers
- Includes risk factors, buffers, and realistic time estimates for each task
- Considers dependencies and development efficiency
- **`--team` option**: Deploys a task decomposition agent and an effort estimation agent in parallel; team lead integrates results into todo.md
- **Serena MCP**: Utilizes Serena MCP for task analysis, effort estimation, and document generation when available

### /task-dev {task_name} [--team]
- Reads design.md and todo.md to understand implementation requirements
- Reads report template from `templates/dev-result-template.md`
- Implements tasks sequentially following the todo list
- Maintains code quality, follows existing patterns, includes appropriate tests
- Reports progress after each task completion
- Creates dev-result.md with implementation overview, changed files, technical details, and completion report
- **`--team` option**: Analyzes todo.md dependencies and assigns independent tasks to parallel agents; file-level work splitting prevents concurrent edit conflicts
- **Serena MCP**: Utilizes Serena MCP for code generation, implementation, testing, and validation when available

### /task-review {task_name} [--team]
- Reads req.md, design.md, todo.md, and dev-result.md to understand full context
- Reads review template from `templates/review-template.md`
- Verifies actual code against requirements, design, and todo completion status
- Evaluates code quality (readability, maintainability, security, error handling, tests)
- Creates review.md with overall judgment (no fix needed / fix recommended / fix required) and detailed findings
- **`--team` option**: Deploys requirements/design consistency, code quality, and security/robustness reviewers in parallel; team lead deduplicates and prioritizes findings
- **Serena MCP**: Utilizes Serena MCP for code analysis and review when available

### /task-fix {task_name} [--team]
- Reads review.md and design.md to understand required fixes
- Reads fix report template from `templates/fix-result-template.md`
- Implements code fixes based on review feedback while maintaining design consistency
- Creates fix-result.md with fix details, changed files, and verification results
- **`--team` option**: Assigns independent fixes to parallel agents by file; sequential fixes handled by team lead to avoid conflicts
- **Serena MCP**: Utilizes Serena MCP for code fixes and validation when available

### /task-verify {task_name} [--team]
- Reads req.md, design.md, and dev-result.md for full context
- Optionally reads review.md and fix-result.md if they exist
- Reads verify template from `templates/verify-template.md`
- Analyzes actual implementation code to generate concrete verification steps
- Creates verify.md with bite-sized, checkbox-based manual verification procedures
- Prioritizes quick-win steps first to lower psychological barriers
- Includes exact commands, URLs, test data, and expected results
- **`--team` option**: Deploys happy-path, edge-case/error, and non-functional/regression verification designers in parallel; team lead integrates into Quick Win-first ordering
- **Serena MCP**: Utilizes Serena MCP for code analysis and verification procedure generation when available

## Agent Teams オプション

7つのスキル（task-init を除く全スキル）は `--team` オプションに対応しています。

### 使用方法

```bash
/task-dev my-task --team
/task-review my-task --team
```

### 有効化方法

Agent Teams 機能を使用するには、`~/.claude/settings.json` に以下を追加してください:

```json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  }
}
```

### コストに関する注意

Agent Teams はトークン消費が大幅に増加します。チームメイトの生成・管理に伴い、通常の2〜5倍のトークンを消費する可能性があります。

### スキル実行コンテキストについて

8 スキル全てが **メイン会話のコンテキスト**で実行されます（`context: fork` は使用していません）。これは Agent Teams を成立させるために必要な設計上の選択です:

- `context: fork` でフォークされたサブエージェントには、チームメイト spawn に必要な `Agent` ツールが引き継がれません（Claude Code 仕様: 「subagent は別の subagent を spawn できない」）
- そのため、Agent Teams を Skills 経由で利用するには、スキル本体をメイン会話で実行する必要があります
- トレードオフとして、スキル実行中の中間出力（ファイル読込・分析等）はメイン会話のコンテキストウィンドウを消費します。Opus 4.7 1M context モデルを使用していれば実用上問題は小さい想定です

### 環境変数の判定ルール

`--team` が指定された場合、スキルは Bash ツールで以下のコマンドを実行して環境変数を確認します:

```bash
printenv CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS || echo "__UNSET__"
```

出力値の判定:

| 出力値 | 扱い |
|--------|------|
| `1` | 有効 |
| `true`（大文字小文字問わず） | 有効 |
| `__UNSET__` | 無効（未設定） |
| 空文字列 | 無効（空値） |
| 上記以外（例: `0`, `false`, `no` 等） | 無効（明示的に無効化） |

### Agent Teams 実行成立条件

Agent Teams が `有効` と記録されるためには、以下の **3 条件すべて** を満たす必要があります:

1. `--team` 引数が指定されていること
2. 環境変数 `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` が有効値（`1` または `true`）であること
3. `ToolSearch` で `TeamCreate` が利用可能と確認でき、かつチームメイトが少なくとも 1 体実際に稼働（応答）したこと

### Agent Teams ツールのロード手順

環境変数が有効と確認された場合、スキルは以下の手順で Agent Teams ツールをロードします:

```
ToolSearch query="select:TeamCreate,TeamDelete,SendMessage,TaskStop" max_results=10
```

ToolSearch 結果の判定:

| 結果 | 扱い |
|------|------|
| `TeamCreate` が `<functions>` ブロックに含まれる | チーム生成へ進む |
| `TeamCreate` が含まれない、または `<functions>` ブロックが空 | ツール利用不可 — フォールバック |
| ToolSearch 自体がエラー終了 | ツール利用不可 — フォールバック |

### フォールバック動作

以下のいずれかの場合、スキルは対応するメッセージを **必ず** 表示してから通常モードにフォールバックします（省略・要約禁止）:

**環境変数が未設定または無効な場合:**

「⚠️ Agent Teams が有効化されていません。`~/.claude/settings.json` の `env` フィールドに `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` を設定してください。今回は通常モードで実行します。」

**ツールが利用できない場合（ToolSearch で TeamCreate が取得不可、または TeamCreate 後にチームメイトが spawn できない場合）:**

「⚠️ Agent Teams ツール（TeamCreate 等）が現在の環境で利用できないため、Agent Teams モードを起動できません。今回は通常モードで実行します。」

**重要**: スキルは「黙ってフォールバックする」ことを禁止しています。どの理由でフォールバックする場合も、必ず対応するメッセージを表示します。

**`--team` 未指定時の動作**:

`--team` が指定されていない場合、スキルは Agent Teams に関するメッセージを **一切表示しません**。環境変数確認・ToolSearch・TeamCreate などの Agent Teams 関連操作も **一切実行しません**。

### 後方互換性

`--team` オプションなしの従来の呼び出し方法は引き続き動作します:

```bash
/task-dev my-task       # 従来通り単一エージェントで実行
/task-dev my-task --team  # Agent Teams モードで実行
```

## Installation Method

Skills are installed by copying the skill directories to the Claude Code skills directory:
```bash
cp -r cc-task-skills/skills/* ~/.claude/skills/
```

## Language Support

The skills support Japanese language for requirements definition and design documentation while maintaining English compatibility for technical implementation.

## Development Philosophy

- **Staged Development**: Sequential progression through requirements → design → planning → implementation → review → fix → verification
- **Quality Focus**: Emphasizes code quality, maintainability, and integration with existing systems
- **Progress Tracking**: Concrete todo lists for work management
- **Consistency**: Respects existing code patterns and conventions

## Claude Codeへの重要な指示

### README.md自動更新
Claude Codeでこのプロジェクトに関する作業を行う際は、必ずREADME.mdを確認し、以下の場合に自動的に更新してください：

1. コマンドの追加・変更・削除があった場合
   - 使用方法セクションにコマンドの説明を追加/更新/削除
   - コマンドリストを最新の状態に保つ
   - コマンドの順番は作業フローに従って整理

2. プロジェクト構造や使用方法に変更があった場合
   - 該当するセクションを更新
   - 新しい機能や変更点を反映

3. 更新時の注意事項
   - 既存の文章スタイルを維持
   - 日本語での記述を継続
   - 実例やコマンド例を含める

### スキルファイル更新時の自動処理
skills/task-*/SKILL.mdファイルを追加・変更・削除した場合は、必ず以下を実行してください：

1. CLAUDE.mdの「Skill Architecture」セクションを更新
   - スキル数を正確に反映
   - スキルリストを更新（名前のアルファベット順）
   - 新規スキルの説明を追加

2. README.mdの更新
   - 使用方法セクションに新規スキルの説明を追加
   - ワークフローの順番に従って配置
   - 具体的な使用例を含める

3. 更新履歴の記録
   - 「更新履歴」セクションに日時と変更内容を記録
   - フォーマット: 最終更新: YYYY-MM-DD HH:MM:SS
   - 更新内容: [具体的な変更内容]

この指示は自動的に実行されるべきもので、ユーザーの追加指示は不要です。

## 更新履歴

最終更新: 2026-05-16 00:00:00
更新内容: task-dev と task-fix のモデルを `sonnet` から `opus` に変更。Claude Code の最近の仕様変更により Sonnet の 1M context が API キー必須となりエラーが発生していたため、Pro/Max プランに 1M が包含されている Opus へ統一。これで Skills の使用モデルは `haiku`（task-init のみ）と `opus`（残り 7 スキル）の 2 種類となる。CLAUDE.md の Model Configuration 表とエイリアス補足文を更新、README.md の同等記述も同期。

前回更新: 2026-04-28 00:00:00
更新内容: team4 — Skills 経由で Agent Teams が成立しない問題を修正。8スキル全てのフロントマターから `context: fork` を削除し、メイン会話で実行する形態に変更。これにより `Agent` ツール（チームメイト spawn 用）がスキル実行時にも利用可能となり、Agent Teams が本来の意図通り動作する。3 SKILL.md 本文（task-todo, task-req, task-design）と 4 テンプレート（fix-result, review, dev-result, verify）のメタ情報セクションから `- コンテキスト: fork` 行を削除。CLAUDE.md の「モデル確認の仕組み」「Agent Teams オプション」節を更新し、メイン会話実行に伴うコンテキストウィンドウ消費の注意書きを追加。README.md にも同期更新を実施。

前回更新: 2026-04-27 12:00:00
更新内容: team3 — Agent Teams の不具合 A・B を修正。不具合 A（TeamCreate 呼べてもチームメイト spawn できない場合に「有効」と誤記録）と不具合 B（--team 未指定なのに ✅ メッセージが表示される）の根本対応。7スキルの「引数の解釈」セクションに `--team` 未指定時の早期リターン文言（完全無視・一切表示しない指示）を追加。「Agent Teams モード」セクション冒頭に前提条件バナーを追加（フェイルセーフ）。「ツール準備」節をフォールバック手順つき版に改訂（ToolSearch 失敗判定表、ツール利用不可時のフォールバックメッセージ必須化、TeamCreate 後のチームメイト稼働確認、空チームクリーンアップ手順）。「統合」節にチームリード単独完遂 = フォールバック注意書き追加。CLAUDE.md の「Agent Teams 実行成立条件」節を新設（3条件明記）、フォールバックメッセージを2種類に整理、`--team` 未指定時の挙動を明記。メタ情報 3値の判定基準を実際のチームメイト稼働に基づく定義に精密化。README.md に同期更新を実施。

前回更新: 2026-04-27 00:00:00
更新内容: --team オプション時の Agent Teams 動作を修正。7スキルの「前提条件の確認」セクションに Bash による環境変数確認手順（printenv + __UNSET__ フォールバック）、判定ルール表、有効/無効時の挙動、TeamCreate ToolSearch ロード手順を追記。フォールバック表示を必須化（省略禁止）。メタ情報 Agent Teams フィールドを3値（有効/無効（指定なし）/無効（フォールバック））に統一。5テンプレートファイルのメタ情報を3値表記に更新。CLAUDE.md・README.mdに環境変数判定ルール・ToolSearch手順・3値表記を反映。

前回更新: 2026-03-15 00:00:00
更新内容: Agent Teams有効化方法をexportコマンドから~/.claude/settings.jsonのenvフィールドに変更。フォールバックメッセージを「今回は通常モードで実行します。」に修正。README.md・CLAUDE.md・7つのSKILL.mdを更新。

前回更新: 2026-03-15 00:00:00
更新内容: Agent Teams オプション（--team）対応。7スキル（task-init除く）にargument-hint、引数パースセクション、Agent Teamsセクションを追加。$ARGUMENTS→$ARGUMENTS[0]への置換。テンプレートファイルのメタ情報にAgent Teams行を追加。CLAUDE.md・README.mdにAgent Teams使用方法を追記。

前回更新: 2026-03-15 00:00:00
更新内容: 全スキルにパス解決ルールを追加。タスクファイルがプロジェクトルート配下に正しく作成されるよう、pwdで絶対パスを取得して使用する仕組みを導入。

前回更新: 2026-03-13 00:00:00
更新内容: プロジェクト名を「Claude Code Task Commands」から「CC Task Skills」に変更。リポジトリ名をcc-task-skillsに変更。README.md・CLAUDE.mdの名称・URL・インストールコマンドを更新。

前回更新: 2026-03-13 00:00:00
更新内容: task-verify（手動検証手順書生成）を新規追加。開発完了後にコピペで実行可能な検証手順をチェックボックス形式で生成するスキル。スキル数を7→8に拡張。

前々回更新: 2026-03-12 00:00:00
更新内容: .claude/commands/形式から.claude/skills/形式への全面移行。モデルIDをエイリアス（haiku, opus, sonnet）に変更。報告書テンプレートをサポートファイル（templates/）に分離。メタ情報自己申告の仕組みを導入。disable-model-invocationを全スキルに追加。

前々回更新: 2026-03-01 00:00:00
更新内容: task-dev.mdから不要な「専門エージェント（Subagent）の活用」セクションを削除。ロール説明を「開発マネージャー」から「開発者」に変更。README.mdからサブエージェント言及を削除。

前々回更新: 2026-02-28 00:00:00
更新内容: task-review.md（コードレビュー）と task-fix.md（修正実行）を新規追加。task-dev.md から確認エージェントを分離し、レビューと修正を独立した専用コマンドとして実装。コマンド数を5→7に拡張。

前々回更新: 2026-02-24 00:00:00
更新内容: 全コマンド（task-init, task-req, task-design, task-todo, task-dev）のフロントマターに `context: fork` を追加。各コマンドが独立したフォークコンテキストで実行されるようになり、前コマンドの実行履歴によるコンテキスト圧迫を防止。

前々回更新: 2026-02-18 00:00:00
更新内容: task-devコマンドの使用モデルをOpus 4.6からSonnet 4.6に変更。コストと精度のバランスを最適化。
