# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository contains a collection of custom slash commands for Claude Code that implement a task-based development workflow. The commands provide a structured approach to software development with 7 distinct phases: initialization, requirements, design, planning, implementation, review, and fix.

## Command Architecture

The repository contains 7 interconnected slash commands that work together:

1. **task-design.md** - Analyzes existing systems and creates technical design
2. **task-dev.md** - Executes implementation based on todo list and creates development report
3. **task-fix.md** - Fixes code based on review feedback
4. **task-init.md** - Creates task environment and requirements gathering
5. **task-req.md** - Creates requirements draft from raw customer requests
6. **task-review.md** - Reviews implementation against requirements, design, and code quality
7. **task-todo.md** - Breaks down design into actionable development tasks with effort estimation

## Task Management Structure

Each task follows a standardized directory structure:
```
.claude/tasks/{task_name}/
├── init.md         # Raw customer requests
├── requirements.md  # Requirements definition
├── design.md       # Technical design
├── todo.md         # Implementation todo list with effort estimation
├── dev-result.md   # Development completion report
├── review.md       # Code review report
└── fix-result.md   # Fix completion report
```

## Model Configuration

Each command specifies an appropriate model via Frontmatter for optimal cost-performance balance:

| Command | Model | Model ID | Reason |
|---------|-------|----------|--------|
| task-init | **Haiku 4.5** | `claude-haiku-4-5-20251001` | Simple file creation, cost reduction |
| task-req | **Opus 4.6** | `claude-opus-4-6` | High-precision design required |
| task-design | **Opus 4.6** | `claude-opus-4-6` | High-precision design required |
| task-todo | **Opus 4.6** | `claude-opus-4-6` | High-precision planning and estimation |
| task-dev | **Sonnet 4.6** | `claude-sonnet-4-6` | Balance of cost and precision for implementation |
| task-review | **Opus 4.6** | `claude-opus-4-6` | High-precision review required |
| task-fix | **Sonnet 4.6** | `claude-sonnet-4-6` | Balance of cost and precision for fixes |

## Serena MCP Integration

All commands support Serena MCP (Model Context Protocol). When Serena MCP tools are available, commands will:
- Automatically detect and utilize Serena MCP capabilities
- Prioritize Serena MCP functions for document generation, analysis, and validation
- Fall back to traditional methods when Serena MCP is unavailable

## Key Command Behaviors

### /task-init {task_name}
- Creates `.claude/tasks/{task_name}/` directory structure
- Creates init.md for capturing raw customer requests
- Generates templated requirements.md with sections for overview, background, functional/non-functional requirements, impact analysis, constraints, and system relationships
- Note: design.md, todo.md, dev-result.md, review.md, fix-result.md are created by their respective commands (task-design, task-todo, task-dev, task-review, task-fix)
- **Serena MCP**: Utilizes Serena MCP for file creation and template generation when available

### /task-req {task_name}
- Reads raw customer requests from init.md
- Analyzes and structures the information into requirements.md
- Creates a draft requirements document from ambiguous requests
- **Serena MCP**: Utilizes Serena MCP for requirements analysis and document generation when available

### /task-design {task_name}
- Reads requirements.md to understand task scope
- Analyzes existing project structure to maintain consistency
- Creates comprehensive design.md covering architecture, components, file structure, data design, API design, error handling, testing strategy, and performance/security considerations
- **Serena MCP**: Utilizes Serena MCP for design document creation, analysis, and validation when available

### /task-todo {task_name}
- Reads requirements.md and design.md to understand technical requirements
- Creates structured todo.md with implementation order, task breakdown, deliverables, priorities, and checkpoints
- Performs comprehensive effort estimation for manual implementation by intermediate-level programmers
- Includes risk factors, buffers, and realistic time estimates for each task
- Considers dependencies and development efficiency
- **Serena MCP**: Utilizes Serena MCP for task analysis, effort estimation, and document generation when available

### /task-dev {task_name}
- Reads design.md and todo.md to understand implementation requirements
- Implements tasks sequentially following the todo list
- Maintains code quality, follows existing patterns, includes appropriate tests
- Reports progress after each task completion
- Creates dev-result.md with implementation overview, changed files, technical details, and completion report
- **Serena MCP**: Utilizes Serena MCP for code generation, implementation, testing, and validation when available

### /task-review {task_name}
- Reads requirements.md, design.md, todo.md, and dev-result.md to understand full context
- Verifies actual code against requirements, design, and todo completion status
- Evaluates code quality (readability, maintainability, security, error handling, tests)
- Creates review.md with overall judgment (no fix needed / fix recommended / fix required) and detailed findings
- **Serena MCP**: Utilizes Serena MCP for code analysis and review when available

### /task-fix {task_name}
- Reads review.md and design.md to understand required fixes
- Implements code fixes based on review feedback while maintaining design consistency
- Creates fix-result.md with fix details, changed files, and verification results
- **Serena MCP**: Utilizes Serena MCP for code fixes and validation when available

## Installation Method

Commands are installed by copying the .md files to the Claude Code commands directory:
```bash
cp claude-code-task-commands/*.md ~/.claude/commands/
```

## Language Support

The commands support Japanese language for requirements definition and design documentation while maintaining English compatibility for technical implementation.

## Development Philosophy

- **Staged Development**: Sequential progression through requirements → design → planning → implementation → review → fix
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

### コマンドファイル更新時の自動処理
task-*.mdファイルを追加・変更・削除した場合は、必ず以下を実行してください：

1. CLAUDE.mdの「Command Architecture」セクションを更新
   - コマンド数を正確に反映（「6 distinct phases」等の数値を更新）
   - コマンドリストを更新（ファイル名のアルファベット順）
   - 新規コマンドの説明を追加

2. README.mdの更新
   - 使用方法セクションに新規コマンドの説明を追加
   - ワークフローの順番に従って配置
   - 具体的な使用例を含める

3. 更新履歴の記録
   - 「更新履歴」セクションに日時と変更内容を記録
   - フォーマット: 最終更新: YYYY-MM-DD HH:MM:SS
   - 更新内容: [具体的な変更内容]

この指示は自動的に実行されるべきもので、ユーザーの追加指示は不要です。

## 更新履歴

最終更新: 2026-03-01 00:00:00
更新内容: task-dev.mdから不要な「専門エージェント（Subagent）の活用」セクションを削除。ロール説明を「開発マネージャー」から「開発者」に変更。README.mdからサブエージェント言及を削除。

前回更新: 2026-02-28 00:00:00
更新内容: task-review.md（コードレビュー）と task-fix.md（修正実行）を新規追加。task-dev.md から確認エージェントを分離し、レビューと修正を独立した専用コマンドとして実装。コマンド数を5→7に拡張。

前々回更新: 2026-02-24 00:00:00
更新内容: 全コマンド（task-init, task-req, task-design, task-todo, task-dev）のフロントマターに `context: fork` を追加。各コマンドが独立したフォークコンテキストで実行されるようになり、前コマンドの実行履歴によるコンテキスト圧迫を防止。

前々回更新: 2026-02-18 00:00:00
更新内容: task-devコマンドの使用モデルをOpus 4.6からSonnet 4.6に変更。コストと精度のバランスを最適化。

前々回更新: 2026-02-24 00:00:00
更新内容: 全コマンド（task-init, task-req, task-design, task-todo, task-dev）のフロントマターに `context: fork` を追加。各コマンドが独立したフォークコンテキストで実行されるようになり、前コマンドの実行履歴によるコンテキスト圧迫を防止。
