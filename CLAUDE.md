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
| task-dev | **Sonnet** | `sonnet` | Balance of cost and precision for implementation |
| task-review | **Opus** | `opus` | High-precision review required |
| task-fix | **Sonnet** | `sonnet` | Balance of cost and precision for fixes |
| task-verify | **Opus** | `opus` | High-precision verification procedure generation |

Model aliases (`haiku`, `sonnet`, `opus`) are used instead of full model IDs. This ensures automatic resolution to the latest model version when Anthropic updates models.

## モデル確認の仕組み

各コマンドは、出力する報告書の末尾に「メタ情報」セクションを含めます。
サブエージェントが自己申告する形で、実際に使用されたモデル名と実行日時が記録されます。
これにより、`context: fork` で起動されたサブエージェントのモデルをユーザーが確認できます。

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

### フォールバック動作

`--team` が指定されたが環境変数が未設定の場合、以下のメッセージを表示して通常モードにフォールバックします:

「⚠️ Agent Teams が有効化されていません。`~/.claude/settings.json` の `env` フィールドに `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` を設定してください。今回は通常モードで実行します。」

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

最終更新: 2026-03-15 00:00:00
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
