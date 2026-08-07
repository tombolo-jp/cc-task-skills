# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository contains a collection of custom skills for Claude Code that implement a task-based development workflow. The skills provide a structured approach to software development with 8 distinct phases: initialization, requirements, design, planning, implementation, review, fix, and verification.

## Skill Architecture

The repository contains 9 interconnected skills that work together (task-init excluded from `--team` option support):

1. **task-design** - Analyzes existing systems and creates technical design. Supports `--team` option.
2. **task-dev** - Executes implementation based on todo list and creates development report. Supports `--team` option. **Also accepts a comma-separated list of task names** for bulk sequential implementation (delegating each task to an isolated subagent and committing per task); `--team` is ignored in that mode.
3. **task-fix** - Fixes code based on review feedback. Supports `--team` option.
4. **task-init** - Creates task environment and requirements gathering. Optionally fetches task content from a URL into init.md. (No `--team` support)
5. **task-req** - Creates requirements draft from raw customer requests. Supports `--team` option.
6. **task-req-update** - Reflects user answers to the "要確認事項" (open questions) section back into req.md and consolidates it into a finalized version. Supports `--team` option.
7. **task-review** - Reviews implementation against requirements, design, and code quality. Supports `--team` option.
8. **task-todo** - Breaks down design into actionable development tasks with effort estimation. Supports `--team` option.
9. **task-verify** - Generates a concise manual verification procedure document, consolidating automation-recommended checkpoints into an appendix section at the end. Supports `--team` option.

Each skill is a directory under `skills/` containing a `SKILL.md` file and optional `templates/` subdirectory for report templates.

## 設計原則: フローは Task ツールで明示的に追跡する

本プロジェクトの各スキルは「手順」セクションを地の文の Markdown で記述しているが、順守させたいワークフローは、手順の説明文に紛れさせず、**着手前に登録する Task** として明示的に追跡することを設計原則とする。Task ツールが利用できない環境では、構造化チェックリストの宣言へフォールバックする。

地の文の手順記述のみでは、フェーズのスキップ・実装の早期着手・フェーズの取りこぼしが起こりうる。これに対し、スキルの全フェーズを着手前に登録し、各フェーズの着手時に `in_progress`、完了時に `completed` へ遷移させることで、進捗と未達を常に可視化する。

- 各スキルは「手順」冒頭（ステップ0）で進捗管理用の Task ツールをロードし、自スキルの全フェーズを Task として登録して状態遷移させる。これがこの原則の具体化である。登録は省略不可（成果物の必須要素）とし、スキップ・前倒し・状態遷移の省略を禁止事項として明記する。
- **ツールによる追跡はハーネス UI と連動する**。ライブタスク表示・スピナーに進行中フェーズが現れるため、応答本文へチェックリストを毎回再掲する必要がなくなり、記述も出力も簡潔になる。
- **フォールバックにより可用性変動へ耐える**。ツールのロード可否はステップ0 で1回だけ判定し、取得できなければチェックリスト宣言方式で同じフェーズ集合を追跡する。判定はフェーズごとに繰り返さない。フォールバックしたことを告知するメッセージは出さない（チェックリスト自体が進捗表示を兼ねるため、利用者に不利益がない）。
- これは「完璧な強制」ではなく「安定性の有意な向上」を狙う現実的スタンスである。ツールを主経路に置いても、登録そのものを行うか否かは最終的に LLM に依存する。それでも地の文だけの手順記述に比べ、スキップ・前倒し・取りこぼしを構造的に起こりにくくする。
- `--team`（Agent Teams）成立時も、チームリードが自身の Task 一覧で全フェーズを追跡する。チームメイトへ委任した作業は `Agent` の戻り値で完了を確認してから `completed` へ遷移させる。
- 今後スキルを追加・変更する際も、多段フローを持つスキルにはこの原則を適用すること。

> **失効した方針（2026-07-22 〜 2026-08-06）**: 「進捗追跡の記述にツール固有名を持ち込まない（役割語で記述する）」という方針を置いていたが、**撤回する**。主経路をツールに置く以上、ロード対象と呼び出し規約を特定するためにツール名の明示は避けられないためである。

> **経緯（訂正）**: 2026-07-22 の改訂時、本原則は「フローは構造化チェックリストで明示的に追跡する」へ全面移行し、その理由を「Claude Code 側の仕様変更により Task ツールが提供されなくなり、主経路が恒久的に閉塞した」と記録していた。これは**事実誤認である**。当時観測された取得不可は特定バージョン（v2.1.217 / v2.1.218）における一時的な不具合を踏んだ可能性が高く、恒久的な仕様変更ではなかった。v2.1.223 では進捗管理用の4ツールがいずれも取得可能であることを実測で確認したため、Task 方式を主経路へ戻し、チェックリスト方式をフォールバックへ再配置した。

この原則の各スキルへの反映状況と整合性は、`scripts/check_consistency.py`（後述「整合性チェック」）で機械的に検証する。

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

**全9スキルは frontmatter に `model` を指定しない。** スキル実行時のモデルは、呼び出し時点の**セッションモデルを継承**する。利用者は `/model` でモデルを切り替えてからスキルを実行することで、Opus / Sonnet / Fable を自由に選択できる。

```bash
/model sonnet     # 以降のスキル実行は Sonnet で走る
/task-design my-task
```

### なぜ `model` を指定しないのか

- **frontmatter は静的に解決される。** `$ARGUMENTS` の置換はスキル本文にのみ適用されるため、`--model sonnet` のような**引数によるモデル指定は仕様上不可能**である。スキル本体から自身の実行モデルを変更する手段も存在しない。
- **`model` を書くとセッション設定を上書きしてしまう。** frontmatter の `model` はセッションの `/model` 設定より優先され、スキル実行中だけ強制的に上書きされる（終了後にセッションモデルへ復帰）。したがって `model` を書いたままでは、利用者がどのモデルを選んでいても無視される。

以上より、利用者にモデル選択を委ねる手段は「`model` を指定しない（＝継承）」以外に存在しない。**今後スキルを追加する際も `model` を指定しないこと**（`scripts/check_consistency.py` の `frontmatter` 検査が model の再混入を検出する）。

### 補足: 精度とコストの考え方

各スキルは高精度な設計・レビュー・実装を要求するため、**Opus 系の使用を推奨**する。ただしこれは利用者の判断に委ねる方針であり、スキル側では強制しない。軽量モデル（Haiku 等）のセッションでスキルを実行すると、生成物の品質が落ちうる点には留意すること。

> **経緯（失効済み）**: 過去には「Claude Code で Sonnet の 1M context を使うには API キーが必須」という理由で全スキルを `opus` に固定していた。この制約は Sonnet 5 のリリース（2026-06-30 / Claude Code v2.1.197）で解消済みであり、現在 `sonnet` エイリアスは 1M context をネイティブに持ち追加課金なしで利用できる。この経緯は現行の設計判断の根拠ではない。

## モデル確認の仕組み

各コマンドは、出力する報告書の末尾に「メタ情報」セクションを含めます。
スキル本体が自己申告する形で、実際に使用されたモデル名と実行日時が記録されます。
スキル側でモデルを固定しない（セッションモデルを継承する）方針のため、生成物がどのモデルで作成されたかはこの自己申告が唯一の記録となります。

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
| `--team` 指定あり、かつ ① `Agent` ツールでチームメイトが少なくとも 1 体実際に稼働、の条件を満たす | `有効` |
| `--team` 指定なし | `無効（指定なし）` |
| `--team` 指定あり、かつ `Agent` ツール利用不可/チームメイト spawn 失敗のいずれか | `無効（フォールバック）` |

> **重要**: チームメイトが実際に稼働しなかった場合は **`有効` ではなく `無効（フォールバック）`** と記録すること。環境変数 `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` の設定有無は成立判定に影響しません（同変数がゲートするのは `SendMessage` による teammate 間ライブ通信のみで、`Agent` spawn は変数なしでも動作するため）。

## agent フィールドについて

現在のコマンドはすべてファイル書き込みを伴うため、`agent` フィールドは指定していません（デフォルトの汎用エージェント）。
将来的にread-only分析コマンドを追加する場合は、`agent: Explore` の指定を検討してください。

## Key Skill Behaviors

> **フロー強制（全スキル共通）**: 9スキルすべてが「手順」冒頭の **ステップ0** で自スキルの全フェーズを Task として登録し、着手時に `in_progress`・完了時に `completed` へ遷移させることで、スキップ・前倒し・取りこぼしを構造的に防ぐ（Task ツールが利用できない場合はチェックリスト宣言へフォールバックする。「[設計原則: フローは Task ツールで明示的に追跡する](#設計原則-フローは-task-ツールで明示的に追跡する)」の具体化）。登録は省略不可（成果物の必須要素）。**task-dev** は加えて、実行時に todo.md の各実装タスクを Task として動的登録し、1件ずつ着手・完了を明示する。**task-init** は URL 有無の分岐判定後に確定する系列のフェーズのみを登録する特例とする。

### /task-init {task_name} [URL]
- Creates `.claude/tasks/{task_name}/` directory structure
- Creates init.md for capturing raw customer requests
- Generates templated req.md with sections for overview, background, functional/non-functional requirements, impact analysis, constraints, and system relationships
- **URL argument (optional, 2nd positional)**: When a URL is provided (e.g., a Backlog/GitHub/Jira ticket or any web page), fetches the page and transcribes its **body and all comments verbatim** into init.md, saves any attachments to the `attachments/` subdirectory, and appends a **summary** section at the end of init.md
  - **Fetch method**: prefers MCP (service-specific MCP detected via ToolSearch by URL domain), falling back to a **browser-first chain** (claude-in-chrome → chrome-devtools → Playwright → WebFetch)
  - **No fetch method available**: returns an error and exits **without creating init.md or the task directory** (the fetch-method decision happens before `mkdir`)
  - **Partial fetch**: if some content (attachments/comments) cannot be obtained due to the method's limits, processing continues and the missing items are explicitly noted inside init.md
  - **URL quoting**: single quotes are recommended (URLs contain `?`/`&`/`#`); the skill strips surrounding quotes if present
- Note: design.md, todo.md, dev-result.md, review.md, fix-result.md, verify.md are created by their respective skills (task-design, task-todo, task-dev, task-review, task-fix, task-verify)

### /task-req {task_name} [--team]
- Reads raw customer requests from init.md
- Analyzes and structures the information into req.md
- Creates a draft requirements document from ambiguous requests
- **要確認事項セクション**: Consolidates items needing confirmation into a "要確認事項" section at the end of req.md — plain (non-numbered) bullets written as self-contained, one-question-per-item prompts, keeping inline "（要確認）" markers in the body traceable to the list; section order is fixed as 要確認事項 → メタ情報 (metadata last)
- **`--team` option**: Deploys a market/tech research agent and an impact analysis agent in parallel; team lead integrates results into req.md

### /task-req-update {task_name} [--team]
- Reads req.md and parses the "要確認事項" section at its end
- Determines each item's resolution status by whether the user added an indented child element (reply) beneath it
- Reflects resolved items' answers into the relevant body sections (replacing "（要確認）" markers with confirmed content) and removes those items from the list
- Consolidates req.md into just the information needed for detailed design (task-design), conservatively preserving confirmed/functional/non-functional requirements and constraints
- Leaves unresolved items in place; deletes the entire "要確認事項" section once all items are resolved
- Reports the number of unresolved items and the re-run path, enabling an "answer → re-run" loop (idempotent). Directly updates req.md (no dedicated report file / template)
- **`--team` option**: Deploys an answer-reflection agent and a consolidation agent in parallel; team lead judges unresolved items and finalizes req.md

### /task-design {task_name} [--team]
- Reads req.md to understand task scope
- Analyzes existing project structure to maintain consistency
- Creates comprehensive design.md covering architecture, components, file structure, data design, API design, error handling, testing strategy, and performance/security considerations
- **`--team` option**: Deploys data design, API/interface design, and security/performance agents in parallel; team lead integrates results into design.md

### /task-todo {task_name} [--team]
- Reads req.md and design.md to understand technical requirements
- Reads effort estimation template from `templates/todo-template.md`
- Creates structured todo.md with implementation order, task breakdown, deliverables, priorities, and checkpoints
- Performs effort estimation for manual implementation by a developer already familiar with the codebase (design reading, stakeholder coordination, and calendar lead time are excluded from effort)
- **Three-layer estimate**: §0 pre-implementation spikes (blockers resolved in 0.5–1h each) / §A implementation effort (writing code + verification) / §B ancillary work (environment setup, release, documentation)
- **Mandatory sanity check (step 3)**: computes lines-of-code ÷ implementation hours; an estimate below 30 lines/h is rejected as inflated and sent back to step 2
- Converts open-ended uncertainty into spikes rather than unbounded buffers; buffer is ±30% on §A, while §B is presented as a raw lower–upper range with no coefficient
- Keeps task count to 8–12 by merging work on the same file or class; avoids anchoring on any pre-existing estimate found in design.md
- **`--team` option**: Deploys a decomposition/roll-up agent and a **reduction reviewer** (asymmetric roles — the reviewer's job is to cut effort and to reject estimates failing the sanity check); team lead integrates results into todo.md

### /task-dev {task_name}[,{task_name}...] [--team]
- Reads design.md and todo.md to understand implementation requirements
- Reads report template from `templates/dev-result-template.md`
- Implements tasks sequentially following the todo list
- Maintains code quality, follows existing patterns, includes appropriate tests
- Reports progress after each task completion
- Creates dev-result.md with implementation overview, changed files, technical details, and completion report
- **`--team` option**: Analyzes todo.md dependencies and assigns independent tasks to parallel agents; file-level work splitting prevents concurrent edit conflicts
- **Comma-separated multi-task mode (task-dev only)**: The 1st argument accepts `task1,task2,task3` to implement several tasks in one invocation. Whether the specifier contains a comma is evaluated **before** the `--team` branch, and it selects the execution mode:
  - **Parsing**: separator is `,` only; whitespace around commas, empty elements (`t1,,t2` / trailing comma), and task names outside `^[A-Za-z0-9._-]+$` are **errors** (immediate exit, nothing written). Duplicates are de-duplicated with a warning. A specifier without a comma keeps the legacy single-task behavior byte-for-byte
  - **Pre-flight checks**: aborts entirely if not a git repository or if the working tree is dirty (the uncommitted file list is shown); per task, missing `design.md` / `todo.md` → skip (deliverable missing), existing `dev-result.md` → skip (already implemented). The target count is displayed without asking for confirmation
  - **Delegation**: each task's implementation is delegated to an independent `general-purpose` subagent (synchronous, sequential — never parallel) so context does not accumulate across tasks. The subagent returns a fixed-format `STATUS` / `FILES` / `SUMMARY` payload; a malformed return is treated as a failure
  - **Commit per task**: stages only the files the subagent reported (`git add -- <paths>`; `git add -A` is prohibited) and commits with the task name as the message. No push, no branch operations, commits land on the branch active at start-up
  - **`--team` exclusivity**: with a comma-separated specifier, `--team` is ignored with a warning (a subagent cannot spawn further subagents). Single-task invocations keep full `--team` support
  - **Failure handling / idempotency**: a failed task aborts the run; already-committed tasks stay committed and are auto-skipped on re-run. A per-task result summary is always printed (success or abort)

### /task-review {task_name} [--team]
- Reads req.md, design.md, todo.md, and dev-result.md to understand full context
- Reads review template from `templates/review-template.md`
- Verifies actual code against requirements, design, and todo completion status
- Evaluates code quality (readability, maintainability, security, error handling, tests)
- Creates review.md with overall judgment (no fix needed / fix recommended / fix required) and detailed findings
- **`--team` option**: Deploys requirements/design consistency, code quality, and security/robustness reviewers in parallel; team lead deduplicates and prioritizes findings

### /task-fix {task_name} [--team]
- Reads review.md and design.md to understand required fixes
- Reads fix report template from `templates/fix-result-template.md`
- Implements code fixes based on review feedback while maintaining design consistency
- Creates fix-result.md with fix details, changed files, and verification results
- **`--team` option**: Assigns independent fixes to parallel agents by file; sequential fixes handled by team lead to avoid conflicts

### /task-verify {task_name} [--team]
- Reads req.md, design.md, and dev-result.md for full context
- Optionally reads review.md and fix-result.md if they exist
- Reads verify template from `templates/verify-template.md`
- Analyzes actual implementation code to generate concrete verification steps
- Creates verify.md with concise, checkbox-based manual verification procedures written **one item per line** (`- [ ] <操作> → <期待結果>`; the `→` part is omitted when the expected result is obvious from the operation itself)
- Prioritizes quick-win steps first to lower psychological barriers
- Includes exact commands, URLs, test data, and expected results
- **Estimated time (⏱) appears once at the top of the document** as a total; per-section time estimates and per-section explanatory paragraphs are not emitted
- **Automation-recommended areas** (environment setup, edge cases/errors, non-functional, regression) are kept short in the body; anything needing detail is moved to the trailing **「付録: 自動化推奨の確認観点」** section (no checkboxes, not split into a separate file)
- **`--team` option**: Deploys a happy-path verification designer, a peripheral-verification/automation-recommendation designer, and a **reduction reviewer** (asymmetric roles — the reviewer's job is to cut duplicated steps, self-evident items, and anything better covered by automated tests); team lead integrates into Quick Win-first ordering

## Agent Teams オプション

8つのスキル（task-init を除く全スキル）は `--team` オプションに対応しています。

### 使用方法

```bash
/task-dev my-task --team
/task-review my-task --team
```

### 起動方法

`--team` を付けるだけで並列実行（Agent Teams）が起動します。環境変数の事前設定は **不要** です。スキルは `Agent` ツールでチームメイトを直接 spawn し、各チームメイトの成果を `Agent` の**戻り値**（最終メッセージが tool result として返る）で収集、進捗はチームリードの Task 一覧で追跡します。

### （任意）SendMessage ライブ協調の有効化

チームメイト間の**ライブ通信**（`SendMessage`）を使いたい場合のみ、`~/.claude/settings.json` に以下を追加してください。これは **任意設定** であり、未設定でも `--team` による並列実行は問題なく起動します（`SendMessage` が使えない場合は `Agent` 戻り値方式で成立します）。

```json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  }
}
```

> **env 変数の役割（F-7）**: `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` が現在ゲートしているのは `SendMessage`（teammate 間ライブ通信）ただ 1 つです。`Agent` による spawn と、チームリードの Task による進捗追跡は **この変数なしでも動作します**。したがって変数は「Agent Teams を動かすためのスイッチ」ではなく「SendMessage ライブ協調レイヤを有効化する任意スイッチ」です。

### コストに関する注意

Agent Teams はトークン消費が大幅に増加します。チームメイトの生成・管理に伴い、通常の2〜5倍のトークンを消費する可能性があります。

### スキル実行コンテキストについて

8 スキル全てが **メイン会話のコンテキスト**で実行されます（`context: fork` は使用していません）。これは Agent Teams を成立させるために必要な設計上の選択です:

- `context: fork` でフォークされたサブエージェントには、チームメイト spawn に必要な `Agent` ツールが引き継がれません（Claude Code 仕様: 「subagent は別の subagent を spawn できない」）
- そのため、Agent Teams を Skills 経由で利用するには、スキル本体をメイン会話で実行する必要があります
- トレードオフとして、スキル実行中の中間出力（ファイル読込・分析等）はメイン会話のコンテキストウィンドウを消費します。Opus 4.7 1M context モデルを使用していれば実用上問題は小さい想定です

### Agent Teams 実行成立条件

Agent Teams が `有効` と記録されるためには、以下の **2 条件すべて** を満たす必要があります:

1. `--team` 引数が指定されていること
2. `Agent` ツールで spawn したチームメイトが少なくとも 1 体実際に稼働（応答）したこと

> 環境変数 `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` は成立条件に **含めません**（F-7。同変数がゲートするのは `SendMessage` のみであり、並列実行の中核は変数なしで動作するため）。

### 協調ツールのロード手順

`--team` 指定時、スキルはライブ通信に用いるツールを以下でロードします。`Agent` は core ツールでメイン会話に常在するため、ToolSearch でのロードは **不要** です。進捗追跡用の Task ツールはステップ0 でロード済みのため、ここでは指定しません。

```
ToolSearch query="select:SendMessage" max_results=10
```

ToolSearch 結果の判定:

| 結果 | 扱い |
|------|------|
| `SendMessage` が `<functions>` ブロックに含まれる | ライブ通信を併用可。チームリードの Task による進捗追跡と合わせて利用する |
| `SendMessage` が含まれない（env 変数無効） | ライブ通信は使わず、`Agent` の戻り値方式で続行する（フォールバックしない） |
| ToolSearch 自体がエラー終了 | `Agent` 戻り値方式で続行する（フォールバックしない） |

> `Agent` による spawn 自体は上記いずれの場合でも実行可能です。`SendMessage` の可否は成立判定に影響しません。

### フォールバック動作

`--team` 指定時に **`Agent` ツールが利用不可、またはチームメイトが 1 体も稼働しなかった場合**、スキルは以下のメッセージを **必ず** 表示してから通常モードにフォールバックします（省略・要約禁止）:

「⚠️ Agent Teams（チームメイトの起動）が現在の環境で利用できないため、Agent Teams モードを起動できません。今回は通常モードで実行します。」

**重要**: スキルは「黙ってフォールバックする」ことを禁止しています。フォールバックする場合は必ず上記メッセージを表示します。

**`--team` 未指定時の動作**:

`--team` が指定されていない場合、スキルは Agent Teams に関するメッセージを **一切表示しません**。ToolSearch・チームメイト spawn などの Agent Teams 関連操作も **一切実行しません**。

### 後方互換性

`--team` オプションなしの従来の呼び出し方法は引き続き動作します:

```bash
/task-dev my-task       # 従来通り単一エージェントで実行
/task-dev my-task --team  # Agent Teams モードで実行
```

`task-dev` のカンマ区切り指定（複数タスクモード）では、コンテキスト分離を優先するため `--team` は利用できません。同時に指定された場合は警告を表示のうえ `--team` を無視し、複数タスクモードで続行します。

```bash
/task-dev task1,task2,task3         # 複数タスクを逐次実装（タスクごとにコミット）
/task-dev task1,task2 --team        # --team は無視され、複数タスクモードで実行
```

## 整合性チェック

本プロジェクトは「単一ファイル制約（include 機構なし）」のため、Agent Teams 共通ブロック・フォールバック文言・メタ情報フォーマット・テンプレート参照などの定型文が複数ファイルに重複して存在する。この重複は許容したうえで、ファイル間のズレを機械的に検出するのが `scripts/check_consistency.py`（Python 3 標準ライブラリのみ・サードパーティ依存ゼロ）である。

検出する7検査:

| 検査ID | 内容 |
|--------|------|
| `frontmatter` | 全9スキルの `model` 不在 / `disable-model-invocation: true` / `name`=ディレクトリ名 / `argument-hint`（既定は `<task_name> [--team]`。固有の引数を持つスキルのみ `ARGUMENT_HINT_OVERRIDES` で例外化する。現在の例外は **task-init**（URL 用）と **task-dev**（カンマ区切りの複数タスク用）の2件） |
| `common-block` | 8スキル（task-init 除く）の Agent Teams 共通ブロックが task-dev を正準として sha256 一致するか |
| `fallback-msg` | フォールバック文言が CLAUDE.md と SKILL.md で一致するか（整形差を正規化して照合） |
| `meta-format` | 5テンプレートの `## メタ情報` 3行（3値表記含む）が一致するか |
| `env-json` | CLAUDE.md / README.md の `"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"` が一致するか |
| `template-ref` | 5スキルのテンプレート参照が相対パスで実在し、ハードコード絶対パスの再混入がないか |
| `flow-checklist` | 廃止済みの旧タスク管理ツール名・旧チーム生成 API 名が SKILL.md・CLAUDE.md（更新履歴節を除く）・README.md・テンプレートへ再混入していないか、および全9スキルに Task 方式＋フォールバックの記述を伴う `### ステップ0` が存在するか |

実行方法:

```bash
python3 scripts/check_consistency.py        # 不一致のみ表示
python3 scripts/check_consistency.py -v     # 全検査の結果を表示
bash scripts/test/run_consistency_tests.sh  # 検査自体の回帰テスト（fixture 異常系）
```

終了コード: `0`=整合 / `1`=不整合検出 / `2`=実行エラー（対象ファイル欠落・パース不能等）。

**ローカルフック（任意・推奨）**: リポジトリ同梱の pre-commit フックを有効化すると、対象ファイル（`skills/**`・`CLAUDE.md`・`README.md`・templates）を変更したコミット時に自動でチェックが走る。

```bash
git config core.hooksPath scripts/hooks
```

対象ファイルを変更しないコミットは即スキップされる（高速パス）。緊急時は `git commit --no-verify` でバイパスできる。

## Installation Method

Skills are installed by copying the skill directories to the Claude Code skills directory:
```bash
cp -r cc-task-skills/skills/* ~/.claude/skills/
```

> **開発・コントリビュート時**: スキル定義やドキュメントを編集する場合は、前述「整合性チェック」のローカルフックを有効化しておくと定型文のズレを早期に検出できる。
> ```bash
> git config core.hooksPath scripts/hooks
> ```

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

最終更新: 2026-08-06 22:30:00
更新内容: 進捗管理機構を**構造化チェックリスト宣言方式から Task ツール方式へ回帰**（タスク名 `task_tools`、設計書 `.claude/tasks/task_tools/design.md`）。**(1) 背景と経緯の訂正**: 2026-07-22 の改訂で「Claude Code 側の仕様変更により組み込みのタスク登録／更新ツールが提供されなくなり、主経路が恒久的に閉塞した」と記録してチェックリスト方式へ全面移行したが、**これは事実誤認だった**。当時観測された取得不可は v2.1.217 / v2.1.218 における一時的な不具合を踏んだ可能性が高く、v2.1.223 では `TaskCreate` / `TaskUpdate` / `TaskList` / `TaskGet` の4ツールがいずれも `ToolSearch` で取得可能であることを実測（着手前スパイクで確認）。よって Task 方式を主経路へ戻し、チェックリスト方式をフォールバックへ再配置した。**(2) 2層構成**: 進捗管理を「方式決定レイヤ」と「フェーズ実行レイヤ」に分離。方式決定は**スキル実行あたり1回・ステップ0 冒頭のみ**で行い（フェーズごとの再判定を禁止）、以降は決定済みの方式に従うだけとする。取得できなければ**無告知で**チェックリスト方式へフォールバックする（旧実装で「Task ツールが使えないため…」という異常系文言が正常動作中に毎回表示されていた問題の再発防止）。**(3) 全9スキル改訂**: ステップ0 を「全フェーズを Task として登録する」形式へ書換（ToolSearch のロード手順・判定表・Task 方式／チェックリスト方式それぞれの説明・省略不可の明記・禁止事項の3項目）。標準形7スキル（task-req / task-req-update / task-design / task-todo / task-review / task-fix / task-verify）は**フェーズ列挙のみをスキル固有として残し、定型文部分を sha256 でバイト一致**させた（23〜25行 → 44〜46行）。task-dev はステップ0 の単一／複数2系列を維持しつつ「該当する側のみを登録」へ、todo 動的追加を `TaskCreate`（`subject` = `[todo <i>/<N>] <タスク名>`、複数タスクモードは `[task <i>/<N>] <TASK> を実装する`）へ、サブエージェント委譲プロンプトの禁止事項へ「Task ツールを使用しないこと」を追加（タスクリストはセッション単位で共有されるため、メイン会話の進捗表示を汚染する）。task-init は `--team` 非対応のため `--team` 段落を除いた版とし、URL 未指定4フェーズ／指定7フェーズの2系列を維持、取得手段ゼロ時の中断をフェーズ2 `in_progress` のまま・後続 `pending` のまま（`deleted` は「不要になった」を意味し失敗を表さないため不使用）へ改訂。**(4) Agent Teams 共通ブロック**: 3行のみ改訂（進捗追跡の主体をステップ0 で確定した方式へ、旧チーム生成／破棄 API の注記をツール名から役割語へ言い換え）。task-dev を正準として7スキルへバイトコピー（`common-block` PASS）。成立2条件・spawn 失敗時フォールバック文言②・`select:SendMessage`・メタ情報3行/3値表記・env-json 記述は**一切変更なし**。**(5) 廃止語の自己衝突の解消**: `TeamCreate` / `TeamDelete` は「廃止済み」でありながら共通ブロック内に実文字列として存在していたため（8スキル全て）、禁止語へ追加すると**注記行自身が検査に引っかかる**。当該注記からツール名を除去し役割語（「旧来のチーム生成／破棄 API」）へ言い換えることで解決した（検査の除外規則を増やさない）。**(6) 設計原則の改訂**: CLAUDE.md の設計原則節を「フローは構造化チェックリストで明示的に追跡する」→「**フローは Task ツールで明示的に追跡する**」へ全面改稿し、ハーネス UI 連動による記述・出力の簡潔化とフォールバックによる可用性耐性を明記。2026-07-22 に新設した「進捗追跡の記述にツール固有名を持ち込まない」方針は、主経路をツールに置く以上ツール名の明示が避けられないため**撤回**し失効注記で保存。旧経緯の「恒久的に閉塞した」記述も事実誤認として訂正した。**(7) 整合性チェック追従**: `flow-checklist` の禁止語を `Task(?:Create|Update)` → `TodoWrite|TeamCreate|TeamDelete` へ反転、必須語を `["チェックリスト", "省略不可"]` → `["Task", "チェックリスト", "省略不可"]` へ拡張（主経路とフォールバックの双方が記述されていることを機械的に保証）。検査ID・`CHECKS` の7件構成・走査対象・`HISTORY_HEADING` 除外・`_extract_step0_section` は不変。回帰テストはケース(7) の注入文字列を `TaskUpdate` → `TodoWrite` へ差し替え、ケース(10)「ステップ0 の Task 記述欠落」を新規追加し 10→**11ケース**（新ケースは step0 節を**スライスした範囲内でのみ**置換し、`Task` の消し残しを assert する。全文置換にすると `common-block` も同時に落ちてテストの意図が曖昧になるため）。**(8) スパイクによる裏取り**: 新 step0 はコードフェンスと表を含むため、`_extract_step0_section`（「次の `###` / `##` 見出しまで」で節を切る）が抽出範囲を誤らないかを **task-design 1スキルのみ**で先に検証し、7スキル分をまとめて壊すリスクを排除した（結果は成功）。**(9) 後方互換**: frontmatter・引数仕様・入力/出力ファイル・生成物のフォーマット・メタ情報3行/3値表記はいずれも不変。**(10) 検証**: `python3 scripts/check_consistency.py -v` で全7検査 PASS（exit 0）、`bash scripts/test/run_consistency_tests.sh` で 11/11 PASS（exit 0）、標準形7スキルの step0 定型文が sha256 一致することを確認。

前回更新: 2026-07-31 00:00:00
更新内容: `task-verify` が生成する手動検証手順書（verify.md）の**分量過多を解消**（タスク名 `verify`、設計書 `.claude/tasks/verify/design.md`）。**(1) 背景**: 本スキルの対象は「腰が重くて検証を先送りしがちな人」であるにもかかわらず、生成される verify.md が長大になり、**分量そのものが検証の先送りを招く**という本末転倒が起きていた。原因は「1ステップ = 1アクション」原則による項目の細分化、`✅ 期待結果:` を第2行へ強制する2行形式、セクションごとの説明段落と ⏱ 所要時間、および自動化で担保すべき領域（環境準備・異常系・非機能・回帰）を手動手順として本文へ展開していたことにある。**(2) 1行形式への移行**: 2行形式を撤回し `- [ ] <操作> → <期待結果>` の**1行形式**を採用。期待結果が操作文から自明な場合（成否が二値で失敗すれば必ず目に付く／判定を伴わない準備・遷移操作／操作文に判定対象が含まれ同語反復になる）は `→` 以降を省略してよいと規定し、「正しく表示される」等の曖昧語しか書けない期待結果は矢印ごと省く方針を明文化した。1項目の情報が1行に収まるため視線の上下往復が減り、チェックボックス総数＝手動実行件数が一致して進捗の実感が正確になる。**(3) ⏱ の冒頭1回化と説明段落の廃止**: 所要時間は文書冒頭に全体の合計として1回だけ記載する方式へ変更し、セクション別の ⏱ と説明段落を全廃。全項目がチェックボックスである以上、未チェック項目の有無で判定でき情報を持たない `## 検証完了チェック` セクションも廃止した。**(4) 周辺カテゴリの統合と付録退避**: 旧「4. 異常系・エッジケース」「5. 非機能要件」「6. 回帰確認」を `## 周辺確認（異常系・非機能・回帰）` の1セクションへ統合（見出しの括弧書きで範囲情報を回収し、説明段落の行数をゼロにする）。詳述が必要な観点は**完全削除も別ファイル分離もせず**、末尾へ新設した `## 付録: 自動化推奨の確認観点`（チェックボックスなし）へ退避する。本文へ残すか付録へ退避するかは「人の目でしか判定できないもの／今回の変更で壊れやすい既存機能／合否判定に直結し他に確認手段がないもの」は本文、「自動テストで代替可能／境界値の網羅的列挙／今回の変更に固有でない恒常的な運用観点」は付録、という判断基準表で規定した。あわせて既存の不整合（SKILL.md 6カテゴリ vs テンプレート5セクションで非機能の受け皿がない）も解消。**(5) verify-template.md 全面改訂**（77→44行）: セクション別の説明文プレースホルダ全6箇所・セクション単位 ⏱ 全6箇所・`✅ 期待結果:` の2行目・`## 検証完了チェック`・`## 機能検証: [機能名2]` を削除し、`## 付録: 自動化推奨の確認観点` とコードブロック併用時のインデント例示を追加。問題テーブルは維持（4列目のみ `該当ステップ`→`該当箇所`）。**`## メタ情報` の見出し＋直後3行はバイト単位で不変**（`meta-format` 検査 PASS）。**(6) SKILL.md 改訂（C-1〜C-5）**: 「重要な設計思想」を簡潔さ最優先・1項目1行・重複排除・削ってはいけないもの（人の目でしか判定できない確認と合否判定に直結する手順）を軸に全面改稿、ステップ0 のフェーズ宣言へ「重複・省略可能な手順を削り1行形式に整える」を追加して6→7項目化、ステップ3 を「主軸=正常系（手厚く）／周辺=4カテゴリ（簡潔に）」の2層構成＋本文・付録の判断基準表へ改訂、ステップ5 の必須ルールを1行形式・⏱ 冒頭1回・説明段落禁止・付録退避へ差し替え。**Agent Teams 共通ブロックは1文字も変更していない**（sha256 不変。C-1 による +2行で位置のみ 40〜95行 → 42〜97行へ移動）。**(7) `--team` 3担当の非対称化**: 「正常系／異常系／非機能・回帰」の対称3分割では指摘が加算方向にしか出ずリードが全員の成果を足すだけになるため、「**正常系検証設計担当／周辺検証・自動化推奨担当／削減レビュア**」へ再定義。削減レビュアには担当間にまたがる重複手順の洗い出し、自明な期待結果・他項目から必然的に確認される項目の削除提案、自動テストで担保すべき項目の付録退避提案を担わせ、「減らすことが仕事」と依頼プロンプトへ明記させる。「チームメイトへの依頼時の禁止事項」節を新設し、「網羅的に洗い出してください」「エッジケースをすべて列挙してください」といった**網羅性バイアスを注入する指示を禁止**。統合時は削減レビュアの指摘を既定で採用とし、不採用は合否判定に直結する場合と人の目でしか判定できない場合に限る。これは `task-todo` の削減レビュア導入（2026-07-22）と同じ設計思想だが、verify.md 自体の簡潔化が目的のため**不採用理由の生成物への記載は求めない**点のみ異なる。**(8) 後方互換**: frontmatter（`argument-hint` 含む）・引数仕様・入力ファイル・生成先パス `.claude/tasks/{task_name}/verify.md` はいずれも不変。**(9) 未変更**: Agent Teams 共通ブロック、成立2条件、フォールバック時の必須表示（文言・発火条件とも現行のまま）、`env-json`、他8スキルの SKILL.md、他4テンプレート。`scripts/check_consistency.py` および回帰テストは改修不要（task-verify 固有 fixture が存在せず、検査ロジック・検査数とも不変）。最終 `python3 scripts/check_consistency.py` で全7検査 PASS（exit 0）を確認。

前回更新: 2026-07-24 00:16:59
更新内容: `task-dev` に **カンマ区切りによる複数タスク一括実行機能** を追加（タスク名 `bulk`、設計書 `.claude/tasks/bulk/design.md`）。**(1) 背景**: 従来 `task-dev` は単一タスクしか取れず、複数タスクを実装するには人手で N 回起動する必要があった。同一セッションで連続実装するとタスクをまたいでコンテキスト（読み込んだファイル・中間出力）が蓄積し、後半のタスクほど品質が落ちる。**(2) 方式**: `/clear` はモデルから呼び出せず `context: fork` は Agent Teams 成立要件と衝突するため、コンテキスト分離は **`Agent` ツールによるサブエージェント委譲** で実現した。メイン会話に残るのは各タスクの戻り値（数十行の固定フォーマット）のみとなり、タスク数に対してコンテキストが線形累積しない。**(3) SKILL.md 改訂**（177→409行）: 「引数の解釈」節へ `### 実行モードの判定【共通ブロックより先に評価】` を新設し、パース規則 R-1〜R-8（区切りは `,` のみ／カンマ前後の空白・空要素・`^[A-Za-z0-9._-]+$` 外の文字はエラー／重複は先頭1件／複数指定時は `--team` を無視）とエラー・警告文言を規定。カンマの有無によるモード判定を `--team` 判定より上位に置き、複数タスクモードでは共通ブロックを「`--team` を含まない場合」として評価させる前処理規則で整合させた。ステップ0 のフェーズ宣言を単一／複数の2系列へ拡張、ステップ1〜4 に「単一タスクモード」の条件を明示（文言は不変＝後方互換）、**ステップ5（複数タスクモードの実行手順）を新設**（5-1 事前検証 V-1〜V-5 ／ 5-2 件数表示 ／ 5-3 サブエージェント委譲・戻り値契約 A-1〜A-5・コミット規則 C-1〜C-8 と git 操作の安全境界表 ／ 5-4 エラー分類 E-1〜E-12 ／ 5-5 サマリ）。「完了後」節をモード別に分割し FR-7 のサマリ表を追加。**(4) 安全策**: 本スキル群で初めてリポジトリ状態を変更する機能のため、着手前のワーキングツリー清浄性チェックで中断する仕様とし、ステージングは**サブエージェントが申告したファイルのみ**（`git add -A` / `git add .` / `git commit -a` を明示的に禁止列挙）、`git push`・ブランチ操作・`git reset --hard` 等の破壊的操作を禁止。サブエージェント側にも git 状態変更操作と他タスクディレクトリへの書き込みを禁じた。中断後の再実行は完了済みタスクが `dev-result.md` の存在で自動スキップされ冪等に再開できる。**(5) 整合性チェック追従**: `frontmatter` 検査の `argument-hint` 期待値を三項演算子から `ARGUMENT_HINT_OVERRIDES` dict へ変更（`ARGUMENT_HINT_INIT` は dict へ吸収し削除）。task-dev の期待値は `<task_name>[,<task_name>...] [--team]`。回帰テストに異常系 fixture 1件（task-dev の argument-hint を既定値へ差し戻すと `[frontmatter]` が exit 1 になること＝例外が実際に効いていることの検証）を追加し 9→10 ケースへ。**(6) 実測による裏取り**: `common-block` の保護範囲が SKILL.md 29〜84 行であることを着手前スパイクで実測し、編集を「引数の解釈」節前半と `#### 役割分担` 以降の2領域に限定したため、**他8スキルへの波及はゼロ**（`common-block` sha256 不変）。あわせて `_extract_blockquote_messages` が `> ⚠️` 行を集合として収集し包含判定するのみと判明したが、設計方針どおり新設の警告文はコードフェンス記述とした。**(7) 未変更**: Agent Teams 共通ブロック、成立2条件、フォールバック文言、`env-json`、`dev-result-template.md`、他8スキルの SKILL.md。最終 `python3 scripts/check_consistency.py` で全7検査 PASS（exit 0）・回帰テスト 10/10 PASS を確認。

前回更新: 2026-07-22 23:15:47
更新内容: `task-todo` の工数見積もりが構造的に過大化する問題を修正。**(1) 事象**: 実運用中のプロジェクトで、新規コード約500行・実装9h 相当のタスクに対し **102h（12.8人日）** という見積もりが出力された（4.9行/h）。同一プロジェクトの過去4件（9.5h / 17.5h / 29h / 31.5h）は妥当な水準であり、`--team` の有無とも相関しないことから、スキル全体の欠陥ではなく特定条件下での暴発と特定した。**(2) 5つの原因**: ①前提条件が「中級プログラマ（実務経験3-5年）」固定で、設計読解・関係者調整・レビュー対応といった「コードを書かない工数」を正当化していた ②リスク→バッファの指示が加算方向のみで（旧規定「不確実性が高い場合は ±50〜100%」）、減算する検算が存在しなかった ③合計工数の妥当性を検出する仕組みが皆無で、積み上げ式のため個々のタスクが妥当に見えれば破綻に気づけない ④タスク粒度の規定がなく28タスクに細分化され、各タスクの切り上げだけで下限が積み上がった ⑤`--team` の2担当（タスク分解／工数見積もり）がともに「漏れを見つける」役で、上方向にしか圧力がかからずリードは両者を加算するだけだった。加えて design.md に既存の見積もりが記載されていた場合、それを「検証・補正する」立場に固定されて指摘が加算方向にしか出ないアンカリングも確認した。**(3) SKILL.md 改訂**: 前提条件を「このコードベースを熟知した開発者」へ変更し、計上しないもの（設計書の読解／既存コード調査／関係者調整＝ブロッカーとして別管理／カレンダー上のリードタイム）を表で明示、レビュー対応は実装工数の15%を上限と規定。ステップ2 に 2-1（アンカリング回避：既存見積もりは自分で積み上げた後に照合し、自分の積み上げを正とする）・2-2（タスク粒度8〜12件、20件超で統合、同一ファイル／同一クラスは1タスク）・2-3（不確実性は青天井バッファではなく30分〜1時間のスパイクへ変換し二択に落とす）を新設。**ステップ3「コード量サニティチェック」を新設**（`新規・変更コード行数 ÷ 実装工数 = ?行/h` を必須計算。既存パターン流用80〜150行/h・新規性が高い40〜80行/h を基準とし、**30行/h 未満は過大としてステップ2へ差し戻し**、150行/h 超は過小として設計の読み落としを確認。結果は todo.md へ記載必須）。以降のステップを繰り下げ（テンプレート読み込み→4、ToDoリスト作成→5）、ステップ0 のフェーズ宣言も6→7項目へ。「ToDoリスト構成」に **3層構成（§0 事前スパイク／§A 実装工数／§B 付帯工程）を必須化**し、バッファ規定を「§A は ±30%（設計未確定なら ±50%）、§B は係数を掛けず下限〜上限をそのまま提示（二値で決まるものに係数は無意味）、§0 で判定済みの項目はバッファに含めない」へ全面改訂（旧規定 ±50〜100% は廃止注記つきで経緯を保存）。**(4) Agent Teams の役割を非対称化**: 「タスク分解担当／工数見積もり担当」を「**分解・積み上げ担当／削減レビュア**」へ変更。削減レビュアには既存コードの流用可能性の洗い出し、サニティチェックの実施と**差し戻し権限**、青天井バッファのスパイク変換提案を担わせ、「減らすことが仕事」と依頼プロンプトに明記させる。あわせて「チームメイトへの依頼時の禁止事項」節を新設し、「リスクを厳しく評価してください」等の**上方バイアスを注入する指示を禁止**（今回の暴発でリードが実際に出していた指示）。統合時は削減レビュアの指摘を不採用とする場合に理由を todo.md へ残すことを義務化。**(5) テンプレート全面改訂**: `todo-template.md` を22行→175行へ拡張。従来はリスク要因／バッファ計算／最終見積もりの末尾断片のみだったものを、前提条件・見積もりの構成・実コードでの裏取り・工数サマリー・**サニティチェック記入欄**・§0/§A/§B の3層・優先度（ブロッカー区分を新設）・リスク要因・バッファ・最終見積もり・提示にあたっての推奨まで含む todo.md 全体の骨格とした。`## メタ情報` の3行（3値表記）は不変（`meta-format` 検査 PASS）。**(6) 検証**: 改訂後のルールで問題の事例を再計算すると、初版はサニティチェック（4.9行/h）とタスク粒度（28件）とアンカリング回避の3点で停止し、改訂版（実装9h／約500行＝55行/h・9タスク）は「新規性が高いコード 40〜80行/h」の範囲に収まって通過することを確認。**(7) 未変更**: Agent Teams 共通ブロック（`#### 役割分担` の直前までが検査範囲のため `common-block` 検査 PASS）、成立2条件、フォールバック文言、`env-json`、他8スキル。最終 `python3 scripts/check_consistency.py` で全7検査 PASS（exit 0）を確認。

前回更新: 2026-07-22 00:00:00
更新内容: フロー強制機構をハーネス側のタスク管理ツールへの依存から切り離し、**構造化チェックリスト宣言方式**へ全面移行（タスク名 `tool`、設計書 `.claude/tasks/tool/design.md`）。**(1) 原因**: Claude Code v2.1.217 実測で、ステップ0 が依存していた組み込みのタスク登録／更新ツールがハーネス側から提供されなくなっていることを確認（deferred tools 一覧に不在・ToolSearch でも取得不可。`SendMessage` と `Agent` spawn は現存）。Skills 側の不具合ではなくハーネス仕様変更であり、スキルから復活させる手段は存在しない。結果として全スキルが毎回フォールバック経路（地の文チェックリスト）で動作し、「Task ツールが使えないため…」という異常系文言が正常動作中に毎回表示されていた。**(2) 対応方針**: 要件「Task ツールを利用可能にする」は実現不可能なため「フロー強制機構を現行仕様下で確実に機能する形へ復旧する」と再解釈し、例外経路だったチェックリスト方式を正式な主経路へ昇格。存在しないツールへの参照・可用性判定・二段分岐を全スキルから撤去した（ステップ0 が3手順→1手順に短縮）。**(3) 全9スキル改訂**: ステップ0 を「全フェーズをチェックリストとして宣言する」形式へ書換（宣言は省略不可の成果物必須要素、禁止事項として宣言省略・スキップ／前倒し・完了マーク省略を明記）。task-dev の todo 動的登録は「チェックリスト項目として動的追加」へ、task-init の特例（URL 有無の分岐判定後に確定系列のみ宣言・取得手段ゼロ時は未完のまま中断）も同旨で書換。task-init の URL フェッチ手段検出 ToolSearch（Task 登録と無関係）は変更なし。**(4) Agent Teams 共通ブロック**: 進捗共有をチームリードのチェックリスト追跡へ変更、ロード対象を `select:SendMessage` へ縮小。task-dev を正準として8スキルへバイトコピー（`common-block` 検査 PASS）。成立2条件・spawn 失敗時フォールバック文言②・メタ情報3行/3値表記・env-json 記述は**一切変更なし**。**(5) 設計原則の改訂**: CLAUDE.md の設計原則節を「フローはツールで物理的に強制する」→「**フローは構造化チェックリストで明示的に追跡する**」へ全面改稿。旧原則は失効注記方式で経緯を保存し、ツールによる物理的強制に比べ強制力が下がる（順守が LLM 依存になる）点も明記。進捗追跡の記述にツール固有名を持ち込まない方針を新設し、将来ツールが再登場しても本文改修なしで共存できるようにした。**(6) 整合性チェック追従**: `check_consistency.py` に新検査 `flow-checklist` を追加（6→7検査）。廃止済みツール名の再混入検出（CLAUDE.md は更新履歴節以降を除外）と、全9スキルのステップ0 がチェックリスト宣言方式であることの構造確認を行う。回帰テストに異常系 fixture 2件（ツール名再混入 / ステップ0 節欠落）を追加。最終 `python3 scripts/check_consistency.py` で全7検査 PASS（exit 0）・回帰テスト 9/9 PASS を確認。

前回更新: 2026-07-16 00:00:00
更新内容: 全9スキルの frontmatter から `model: opus` を削除し、**セッションモデル継承**方式へ変更。利用者が `/model` で Opus / Sonnet / Fable を自由に選択できるようにした。**(1) 判断根拠**: frontmatter は静的に解決され `$ARGUMENTS` 置換の対象外のため、引数によるモデル指定は仕様上不可能。かつ frontmatter の `model` はセッションの `/model` 設定より優先されるため、`model` を書いたままでは利用者の選択が無視される。したがって「`model` を指定しない」が利用者にモデル選択を委ねる唯一の手段。**(2) 旧根拠の失効**: 「Sonnet の 1M context は API キー必須」（2026-05-16 に opus 統一を決めた理由）は Sonnet 5 リリース（2026-06-30 / Claude Code v2.1.197）で解消済み。現在 `sonnet` は 1M context をネイティブに持ち追加課金不要。**(3) 整合性チェック追従**: `check_consistency.py` の `frontmatter` 検査を「`model` が `opus` であること」から「`model` が存在しないこと」へ反転（6検査の構成は不変）。回帰テスト fixture も `model: opus` への書き換えから `model` 再混入へ変更。**(4) ドキュメント同期**: CLAUDE.md の「Model Configuration」節をモデル表からセッションモデル継承の方針説明へ全面改稿（旧根拠は失効注記つきで保存）、「モデル確認の仕組み」の説明を調整。README.md に「使用するモデルの選択」節を新設（`/model` の使い方・Opus 推奨・メタ情報での確認）。**(5) 未変更**: メタ情報セクションの自己申告フォーマット（3行・3値表記）、Agent Teams 機構、テンプレート5件。最終 `python3 scripts/check_consistency.py` で全6検査 PASS（exit 0）・回帰テスト 7/7 PASS を確認。

前回更新: 2026-07-10 17:20:00
更新内容: 要確認事項の運用改善と `task-req-update` スキルの新設（タスク名 `req`、設計書 `.claude/tasks/req/design.md`）。要件定義フローに「要確認事項へのユーザー回答→本文反映」の対話ループを導入。**(1) task-req 改修**: 「更新時の注意点」を改修し、本文に簡易マーカー「（要確認）」を残しつつ確認事項の実体を req.md 末尾「要確認事項」セクションへ集約する規約（FR-1-1〜FR-1-5: 数字なし箇条書き／インデント返信前提／本文マーカーとの対応／セクション順 `要確認事項`→`メタ情報`）を追加。ステップ0 フェーズ4に要確認事項集約を内包（フェーズ数不変）。**(2) task-req-update 新設**: `skills/task-req-update/SKILL.md` を新規作成（テンプレート非保有）。要確認事項の各項目の直下にユーザーがインデント子要素で回答した内容を本文へ反映し、解決済み項目を削除、未解決は残置、全解決で「要確認事項」セクション自体を削除する冪等的な差分更新スキル。Agent Teams 共通ブロックは task-dev から sha256 一致で複製、役割分担は「返信反映担当／整理・確定担当」。**(3) 整合性チェック追従**: `check_consistency.py` の `TEAM_SKILLS` に `task-req-update` を追加（7→8、`ALL_SKILLS` は自動的に 9 件へ派生）。検査サマリの表示件数（frontmatter 全9・common-block 8・fallback-msg 8）を実数へ更新。6検査の構成・`CANONICAL_SKILL`・`TEMPLATE_FILES` は不変。**(4) ドキュメント同期**: CLAUDE.md（スキル数 8→9・一覧にアルファベット順で task-req-update 挿入・Model Configuration 表・Key Skill Behaviors の task-req 追記と task-req-update 節新設・Agent Teams 対応 7→8・整合性チェック節の件数）と README.md（使用方法にワークフロー順で task-req-update 追記・Agent Teams 対応一覧・使用例）を更新。最終 `python3 scripts/check_consistency.py` で全6検査 PASS（exit 0）・回帰テスト全 PASS を確認。

前回更新: 2026-06-17 14:00:10
更新内容: Agent Teams 機構を現行 Claude Code 仕様へ追従させる改修（タスク名 `team`、設計書 `.claude/tasks/team/design.md`）。最近の仕様変更で `TeamCreate` / `TeamDelete` が廃止され `--team` が常にフォールバックしていた問題を根治。**(1) 廃止 API 全廃**: `TeamCreate` / `TeamDelete` 依存を全スキル・全ドキュメントから削除し、チーム生成を `Agent` ツールの直接 spawn へ移行（`Agent` は core ツールでメイン会話に常在しロード不要）。成果収集は `Agent` の戻り値を主経路とする。**(2) env ハードゲート撤廃**: 実機検証（F-7）で `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` がゲートするのは `SendMessage`（teammate 間ライブ通信）のみと判明。`Agent` spawn と `TaskCreate` / `TaskUpdate` は変数なしで動作するため、env 変数を成立条件から除外し「SendMessage ライブ協調を使いたい場合の任意設定」へ格下げ。これにより `--team` だけで並列実行が起動する。**(3) 成立条件 3→2**: ①`--team` 指定 ②チームメイト 1 体以上稼働。env 変数・TeamCreate 条件を削除。**(4) 共通ブロック簡素化**: 環境変数判定表・ToolSearch（TeamCreate）判定・空チームクリーンアップ・二重フォールバックを撤廃し約半減。ロード対象を `select:TaskCreate,TaskUpdate,SendMessage` へ変更。**(5) フォールバック整理**: 文言①（env 設定依頼）を廃止、文言②を「⚠️ Agent Teams（チームメイトの起動）が現在の環境で利用できないため、Agent Teams モードを起動できません。今回は通常モードで実行します。」へ更新。発火条件を「`Agent` 不可 または spawn 失敗」のみへ限定。**(6) 整合性チェック追従**: `env-table` 検査を削除し 7→6 検査へ。`fallback-msg` 文言を更新、`env-json` は任意設定の記述として維持。メタ情報 3 値の文字列は不変（判定条件のみ再定義）。CLAUDE.md・README.md・7 SKILL.md・`check_consistency.py`・回帰テストを同期。

前回更新: 2026-05-28 01:26:00
更新内容: GitHub Actions による CI（`.github/workflows/consistency.yml`）を削除し、整合性チェックをローカル pre-commit フック（`git config core.hooksPath scripts/hooks`）に一本化する方針へ変更。判断理由: 個人パブリックリポジトリであり、ローカルフックが有効化済みのため二重実行が冗長と判断。`scripts/check_consistency.py` と `scripts/test/run_consistency_tests.sh` 本体は従来どおり維持（フックおよび手動実行で使用）。CLAUDE.md「整合性チェック」節の CI 項を削除、README.md の CI 項を削除しローカルフックに整合性担保を集約する旨を追記。空になった `.github/` ディレクトリも削除。削除後 `python3 scripts/check_consistency.py` で全7検査 PASS（exit 0）・回帰テスト 8/8 PASS を確認。

前回更新: 2026-05-27 23:41:20
更新内容: ワークフロー順守強化（FR-1 / FR-2 / FR-3）を実装。**FR-1（フロー強制）**: 全8スキルの「手順」冒頭に「ステップ0: 全フェーズを Task に登録する」ブロックを追加。各スキルは自身の全フェーズを `TaskCreate` で一括登録し `in_progress` / `completed` 遷移で順守を構造的に強制する。Task ツール不在時は地の文チェックリストへフォールバック。task-dev は加えて todo.md の各実装タスクを個別 Task として動的登録。task-init は URL 有無分岐後に確定系列フェーズのみ登録する特例（取得手段ゼロ時はフェーズ2を in_progress のまま中断・後続 pending でエラー終了）。Agent Teams 最優先分岐ロジックは未変更（後方互換）。**FR-2（設計原則明文化）**: CLAUDE.md の Skill Architecture 直後に「設計原則: フローはツールで物理的に強制する」節を新設。「完璧な強制ではなく安定性の有意な向上」を狙う現実的スタンスと Task 不在時フォールバック方針を明記。**FR-3（整合性チェック）**: `scripts/check_consistency.py`（Python 3 標準ライブラリのみ・サードパーティ依存ゼロ）を新規追加。frontmatter / common-block / fallback-msg / env-table / meta-format / env-json / template-ref の7検査で重複定型文のズレを検出（exit 0=整合 / 1=不整合 / 2=実行エラー）。`scripts/hooks/pre-commit`（`core.hooksPath` 参照・対象無変更時は高速スキップ・`--no-verify` バイパス可）、`.github/workflows/consistency.yml`（CI・初期 informational）、`scripts/test/run_consistency_tests.sh`（7検査の異常系 fixture 回帰テスト）を配置。CLAUDE.md（Key Skill Behaviors 冒頭にフロー強制注記・「整合性チェック」節・Installation Method にフック有効化）と README.md（使用方法のフロー強制注記・インストール手順・「整合性チェック」節）を同期。Agent Teams（script-dev: FR-3 / skills-dev: FR-1 / team-lead: FR-2・ドキュメント）で並行実装し、最終 `python3 scripts/check_consistency.py` で全7検査 PASS（exit 0）・回帰テスト 8/8 PASS を確認。

前回更新: 2026-05-27 12:30:00
更新内容: 既知の軽微な不整合を2件修正。(1) 5スキル（task-dev / task-fix / task-review / task-todo / task-verify）のテンプレート参照を `~/.claude/skills/task-xxx/templates/...` のハードコード絶対パスから、スキルのベースディレクトリ（起動時に `Base directory for this skill` として提示されるパス）配下の相対参照 `templates/...` に変更。インストール先非依存となり、リポジトリ内での参照解決の妥当性も向上。(2) task-todo の todo-template.md にメタ情報セクションを追加し、他4テンプレート（dev-result / fix-result / review / verify）と形式を統一（task-todo は SKILL.md 本文にもメタ情報出力指示があるため、todo.md 自体へのメタ情報出力は従来から保証済み。今回はテンプレート間の形式不統一を解消）。

前回更新: 2026-05-26 00:00:00
更新内容: task-init に URL からのタスク概要自動取得機能を追加。第2引数に URL（任意）を受け取り、本文＋コメントを改変せず全文転記、添付を `attachments/` サブディレクトリに保存、init.md 末尾に要約セクションを付与する。取得は MCP 優先（URL ドメインから ToolSearch で特化 MCP を検出）→ ブラウザ優先フォールバック（claude-in-chrome → chrome-devtools → Playwright → WebFetch）。取得手段が一つも無い場合は mkdir 前にエラー終了し init.md・ディレクトリを作成しない。部分取得時は取得分で続行し未取得項目を init.md に明記。URL はシングルクォート推奨（前後クォートは除去）。これに伴い task-init のモデルを `haiku` → `opus` に変更（全8スキルが opus に統一、haiku 不使用）。SKILL.md 本文を URL 有無分岐フローに再構成、frontmatter に `argument-hint` 追加・`allowed-tools` 行削除。CLAUDE.md の Skill Architecture / Model Configuration 表 / エイリアス補足文 / Key Skill Behaviors を更新。README.md の task-init 節とファイル構造図を同期更新。

前回更新: 2026-05-16 00:00:00
更新内容: Serena MCP 対応を全スキルから削除。7つの SKILL.md（task-design, task-dev, task-fix, task-req, task-review, task-todo, task-verify）から `## Serena MCP対応` セクションを削除。CLAUDE.md の `## Serena MCP Integration` 節および各スキル説明の `- **Serena MCP**:` 行を削除。Skills 側で MCP 提供元に依存する記述を排除し、ツール非依存のシンプルな構成に統一。

前回更新: 2026-05-16 00:00:00
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
