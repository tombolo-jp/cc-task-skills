# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository contains a collection of custom skills for Claude Code that implement a task-based development workflow. The skills provide a structured approach to software development with 5 distinct phases: initialization, requirements, design (which now covers task breakdown and effort estimation as well), implementation (which now covers review and fix as a closed loop inside the same run), and verification (the verification phase covers both procedure generation and automated execution).

## Skill Architecture

The repository contains 6 interconnected skills that work together (only task-init is excluded from `--team` option support):

1. **task-design** - Analyzes existing systems and creates technical design, **then breaks it down into an implementation task list (`T-nnn`) with effort estimation in the same run**. Supports `--team` option.
2. **task-dev** - Executes implementation based on the design's implementation task list, **then automatically runs a review → fix → re-review closed loop (max 3 rounds) inside the same invocation**, and creates the development report. Review is **always delegated to a separate-context subagent** (regardless of `--team`) so that the agent which wrote the code never judges it from its own context; fixing is always single-agent. Review findings, the loop log, and the exit summary are **appended to `dev-result.md`** (no separate review/fix report files). Supports `--team` option (**review phase only** — 3 reviewers in parallel). **Also accepts a comma-separated list of task names** for bulk sequential implementation (delegating each task to an isolated subagent and committing per task); `--team` is ignored in that mode.
3. **task-init** - Creates task environment and requirements gathering. Optionally fetches task content from a URL into init.md. (No `--team` support)
4. **task-req** - Creates requirements draft from raw customer requests. Supports `--team` option.
5. **task-req-update** - Reflects user answers to the "要確認事項" (open questions) section back into req.md and consolidates it into a finalized version. Supports `--team` option.
6. **task-verify** - Generates a verification procedure document **and, by default, executes it**. The generation phase emits **detailed, automation-ready test cases** (machine-readable preamble block, stable `V-nnn` identifiers, mandatory expected results); the automatic-execution phase runs those checkbox items, records required fixes in `verify-result.md`, and loops fix → re-verify (max 5 rounds). `--manual` switches to the concise human-oriented format and **generates only**; `--run-only` **executes only**. Supports `--team` option (**generation phase only**).

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

### 前提: Task ツールの提供はモデル依存でゲートされる（2026-08-16 追記）

**Claude Code 2.1.233 以降、進捗管理用の4ツールは一定バージョン以上のモデルでは既定で無効**である。したがって本原則の主経路を実際に通すには、`~/.claude/settings.json` へ次の env 設定が必要になる（README.md「インストール」手順3と同一内容）。

```json
{
  "env": {
    "CLAUDE_CODE_ENABLE_TODO_TOOLS": "1"
  }
}
```

判定ロジックの実測結果（CLI バイナリの解析による）:

| バージョン | Task ツールの `isEnabled` | 既定の挙動 |
|---|---|---|
| 〜2.1.232 | `CLAUDE_CODE_ENABLE_TASKS !== false` かつリモートのキルスイッチに載っていないこと | **有効** |
| 2.1.233〜 | 上記に加え、モデルがしきい値表（Opus 4.8 / Sonnet 5 / Fable 5 / Mythos 5）**以上**なら、リモートのオプトインフラグ（既定 false）か `CLAUDE_CODE_ENABLE_TODO_TOOLS` が必要 | しきい値以上のモデルでは**無効** |

- **決定要因はモデルであってバージョンではない**、という理解は 2.1.233 以降に限って正しい。2.1.232 までは Opus 5 でも Task ツールは提供されていた。
- リモートフラグはロールアウト状況で変わりうるため、**env 設定なしで有効な時期と無効な時期が混在する**。ステップ0 の2方式分岐（Task 方式 / チェックリスト方式）は今後も維持すること。
- この env 変数は Agent Teams の `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` とは**無関係**である（前者は進捗管理の主経路、後者は `SendMessage` ライブ通信の任意スイッチ）。

> **経緯（訂正）**: 2026-07-22 の改訂時、本原則は「フローは構造化チェックリストで明示的に追跡する」へ全面移行し、その理由を「Claude Code 側の仕様変更により Task ツールが提供されなくなり、主経路が恒久的に閉塞した」と記録していた。これは**事実誤認である**。当時観測された取得不可は特定バージョン（v2.1.217 / v2.1.218）における一時的な不具合を踏んだ可能性が高く、恒久的な仕様変更ではなかった。v2.1.223 では進捗管理用の4ツールがいずれも取得可能であることを実測で確認したため、Task 方式を主経路へ戻し、チェックリスト方式をフォールバックへ再配置した。

この原則の各スキルへの反映状況と整合性は、`scripts/check_consistency.py`（後述「整合性チェック」）で機械的に検証する。

## 設計原則: レビューは構造的に隔離する

同一実行内で実装とレビューを行うスキル（現時点では `task-dev`）は、**レビューを必ず別コンテキストのサブエージェントへ委譲する**ことを設計原則とする。実装時に「この設計で要件を満たす」と結論した主体が、レビュー時に「満たしていない」と言うのは直前の自分の結論の否認であり、**過少指摘（危険側）が構造的に優勢**になる。被害は「要件未充足・脆弱性を含んだ実装が、レビュー済みという記録つきでコミットされること」である。

この隔離は「実装時の判断を思い出さないでください」という**指示では成立しない**。委譲プロンプトへ埋め込んでよい項目を限定列挙し、**実装担当の自己申告である `dev-result.md` を渡さない**ことで、隔離を指示ではなく**構造**にする。レビュー対象は「変更ファイルのパスの配列」としてのみ渡し、差分・実装意図・変更理由・前周の却下理由は渡さない。同型の対処は `task-verify` のスキップ判定（SK-1〜SK-3）で先行して採っている。

- **委譲は `--team` の有無と独立である。** `--team` はレビュー担当を1体から3体へ増やす並列化のスイッチにすぎず、委譲そのものは常に必須である。自己レビューが許されるのは委譲失敗時の degrade 経路のみで、その場合は必ず告知し成果物へ記録する。
- **外部の証拠源を持たないループには終了保証を機械的に置く。** 同一入力に対する同一モデルの再判断には新情報が入らないため、指摘へ安定識別子を採番し、散文を除いた署名で停滞を判定し、ループ上限を設ける。
- **収束は品質を意味しない。** 指摘が0件になったことを品質の証明として扱わない。本当の合否判定は動的検証（`task-verify`）が持つ。
- **同一モデルの盲点は隔離しても共有される。** 本原則が防げるのは一貫性バイアスのみであり、モデル固有の知識欠落は防げない。これは設計上の受容事項として利用者へも案内する。

## Task Management Structure

Each task follows a standardized directory structure:
```
.claude/tasks/{task_name}/
├── init.md         # Raw customer requests
├── req.md          # Requirements definition
├── design.md       # Technical design + §12 implementation task list + §13 effort estimate
├── dev-result.md   # Development completion report + review findings + fix / loop log
├── verify.md       # Verification procedure
└── verify-result.md # Verification execution result (created by task-verify)
```

**Important**: Task files are always created under the **project root's** `.claude/tasks/`, not `~/.claude/tasks/`. Each skill resolves the project root via `pwd` at the beginning of execution and uses absolute paths for all file operations.

> **Backward compatibility**: tasks created with older versions of these skills also contain a `todo.md`. `task-dev` still reads it whenever it exists; design.md takes precedence when the two disagree.

> **Backward compatibility**: tasks created before the review/fix merge also contain a `review.md` and a `fix-result.md`. Those are past execution records, not inputs: `task-dev` **never reads, rewrites, or deletes them** (it only announces once that they exist), and `task-verify` treats them as an optional extra input that exists only in such older tasks.

## Model Configuration

**全6スキルは frontmatter に `model` を指定しない。** スキル実行時のモデルは、呼び出し時点の**セッションモデルを継承**する。利用者は `/model` でモデルを切り替えてからスキルを実行することで、Opus / Sonnet / Fable を自由に選択できる。

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

> **フロー強制（全スキル共通）**: 6スキルすべてが「手順」冒頭の **ステップ0** で自スキルの全フェーズを Task として登録し、着手時に `in_progress`・完了時に `completed` へ遷移させることで、スキップ・前倒し・取りこぼしを構造的に防ぐ（Task ツールが利用できない場合はチェックリスト宣言へフォールバックする。「[設計原則: フローは Task ツールで明示的に追跡する](#設計原則-フローは-task-ツールで明示的に追跡する)」の具体化）。登録は省略不可（成果物の必須要素）。**task-dev** は単一タスクモードで12フェーズ（`--team` 非依存）、複数タスクモードで7フェーズを登録し、加えて実行時に design.md の実装タスク一覧（`T-nnn`。todo.md が存在する場合はその項目も）を Task として動的登録して1件ずつ着手・完了を明示し、さらにレビューパス1周ごとに `[review pass i/3]`（修正必須があれば `[fix pass i/3]` も）を動的追加する（パス内の個別 `R-nnn` は Task 化しない）。**task-init** は URL 有無の分岐判定後に確定する系列のフェーズのみを登録する特例とする。**task-verify** は既定モードで18フェーズ（`--manual` は7、`--run-only` は12）を登録したうえで、確認パス1周ごとに Task を動的追加する（各パス内の個別項目は Task 化しない）。

### /task-init {task_name} [URL]
- Creates `.claude/tasks/{task_name}/` directory structure
- Creates init.md for capturing raw customer requests
- Generates templated req.md with sections for overview, background, functional/non-functional requirements, impact analysis, constraints, and system relationships
- **URL argument (optional, 2nd positional)**: When a URL is provided (e.g., a Backlog/GitHub/Jira ticket or any web page), fetches the page and transcribes its **body and all comments verbatim** into init.md, saves any attachments to the `attachments/` subdirectory, and appends a **summary** section at the end of init.md
  - **Fetch method**: prefers MCP (service-specific MCP detected via ToolSearch by URL domain), falling back to a **browser-first chain** (claude-in-chrome → chrome-devtools → Playwright → WebFetch)
  - **No fetch method available**: returns an error and exits **without creating init.md or the task directory** (the fetch-method decision happens before `mkdir`)
  - **Partial fetch**: if some content (attachments/comments) cannot be obtained due to the method's limits, processing continues and the missing items are explicitly noted inside init.md
  - **URL quoting**: single quotes are recommended (URLs contain `?`/`&`/`#`); the skill strips surrounding quotes if present
- Note: design.md, dev-result.md, verify.md, verify-result.md are created by their respective skills (task-design, task-dev, task-verify)

### /task-req {task_name} [--team]
- Reads raw customer requests from init.md
- Analyzes and structures the information into req.md
- Creates a draft requirements document from ambiguous requests
- **要確認事項セクション**: Consolidates items needing confirmation into a "要確認事項" section at the end of req.md — plain (non-numbered) bullets written as self-contained, one-question-per-item prompts, keeping inline "（要確認）" markers in the body traceable to the list; section order is fixed as 要確認事項 → メタ情報 (metadata last). **A content filter keeps only questions whose answer changes a design or implementation branch**: inclusion comes first (the branch test — can you write, concretely and in two or more places, how design.md §1–§11 or the §12 task list would differ per answer?), then a closed exclusion vocabulary (`X-1` schedule / `X-2` commercial & cost / `X-3` staffing & process / `X-4` interpersonal communication / `X-5` meta questions / `X-6` answerable from the codebase yourself), with **anything undecidable kept** (fail-safe points the opposite way from `task-verify`'s skip decision). Excluded items get **no inline marker and no fallback section**, and the exclusion count is never reported; if zero items remain, **the 要確認事項 section itself is not emitted** and メタ情報 becomes the last section
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
- Reads the design template from `templates/design-template.md`
- Creates comprehensive design.md covering architecture, components, file structure, data design, API design, error handling, testing strategy, and performance/security considerations
- **Also produces the implementation task list and the effort estimate in the same run.** The generated design.md is split by a **設計確定線 (design freeze line)**: §1–§11 are design sections, §12 is `## 12. 実装タスク一覧`, §13 is `## 13. 工数見積もり`, and `## メタ情報` is always last
- **`## 12. 実装タスク一覧`** is the single section downstream skills parse. Every item carries a stable `` `T-nnn` `` identifier (3-digit zero-padded, numbering order = implementation order, gaps allowed, duplicates prohibited, IDs never reused) plus 対象 / 作業 / 依存 / 完了条件 / 見積もり (注意点 optional). **task-dev never rewrites these checkboxes** — progress lives in dev-result.md
- **`## 4. ファイル構造` must record estimated line counts** per file; their total is the input to the sanity check
- Performs effort estimation for manual implementation by a developer already familiar with the codebase (design reading, stakeholder coordination, and calendar lead time are excluded from effort; review handling is capped at 15% of implementation effort)
- **Three-layer estimate**: §0 pre-implementation spikes (blockers resolved in 0.5–1h each) / §A implementation effort (writing code + verification) / §B ancillary work (environment setup, release, documentation). **§13-5 (§A) holds the roll-up only** — the task detail lives solely in §12, so nothing is written twice
- **Mandatory sanity check (step 5-3)**: computes lines-of-code ÷ implementation hours; an estimate below 30 lines/h is rejected as inflated and sent back to step 5-1. **Rework is capped at 2 rounds**, with early abort when the §A total is unchanged; on reaching the cap the estimate is adopted as-is and flagged in §13-3 for the user to judge
- Converts open-ended uncertainty into spikes rather than unbounded buffers; buffer is ±30% on §A, while §B is presented as a raw lower–upper range with no coefficient
- Keeps task count to 8–12 by merging work on the same file or class; **anchoring avoidance** is enforced structurally by the freeze line — design sections are read-only during estimation, and any pre-existing estimate is compared only after building one's own roll-up
- **`--team` option**: runs in **two sequential phases** — phase 1 deploys data design, API/interface design, and security/performance agents in parallel to fix §1–§11; phase 2 then deploys a decomposition/roll-up agent and a **reduction reviewer** (asymmetric roles — the reviewer's job is to cut effort and to reject estimates failing the sanity check). Team lead integrates results into design.md; rejected reduction findings must be justified in §13-9

### /task-dev {task_name}[,{task_name}...] [--team]
- Reads design.md to understand implementation requirements (**todo.md is read only when it exists**, for backward compatibility with tasks created before the merge)
- Reads report template from `templates/dev-result-template.md`
- Implements tasks sequentially following the design's implementation task list (`T-nnn`)
- Maintains code quality, follows existing patterns, includes appropriate tests
- Reports progress after each task completion
- Creates dev-result.md with implementation overview, changed files, technical details, and completion report
- **Input resolution (5 branches)**: design.md missing → skip; design.md with §12 and no todo.md → proceed on design.md alone; design.md **without** §12 and no todo.md → **append `## 12. 実装タスク一覧` to design.md first** (announced to the user, never silently), then implement; when todo.md exists it is **always read together with design.md**, and design.md wins on conflict. Progress tasks are registered as `[T-nnn]` for design-derived items and `[todo i/N]` for todo.md-derived ones
- **Argument parsing (`AP-1`〜`AP-8`), evaluated before the `--team` branch**: the only known flag is `--team`; **an unknown flag is an error** (`--tema` / `--no-review` must not silently fall through, because this skill now rewrites repository code during the fix phase). The error exits **before** the step-0 phase registration so that no unexecuted phase is left on the progress list. **There is no option that skips the review** — `--no-review` / `--review-only` equivalents do not exist and the loop always runs
- **The "permission switch line"** separates the two phases at "the last `T-nnn` is done and the implementation sections of `dev-result.md` are written": before it, `dev-result.md` is created/overwritten wholesale, code may change freely within the `T-nnn` scope, and `--team` parallelizes implementation; after it, `dev-result.md` is **append-only** (plus the limited edits W-3 / W-6 allow), code may change **only where an unresolved `R-nnn` (fix-required) points**, and the judgment's inputs are restricted to req.md / design.md / the target file paths / the review checkpoints. In multi-task mode the line is drawn **per task**, right after the implementation delegation returns `STATUS: success` and before that task's commit
- **Review–fix loop (max 3 rounds, same invocation)**:
  - **Review is always delegated** to a synchronous `general-purpose` subagent (`RI-1`), with or without `--team`. Self-review is allowed only on the degrade path (spawn failure / two malformed returns), and the degrade must be announced verbatim and recorded in `dev-result.md` — never silently
  - **The delegation prompt is a closed list of 11 items (`RP-1`〜`RP-11`)**. **`dev-result.md` is never passed** — it is the implementer's own account, and reading it suppresses findings. Changed files are passed as **paths only** (no diffs, no implementation intent); from round 2 the only carried-over context is `R-nnn` / a one-line summary / resolved-or-not. Rejection reasons, priority-change reasons, and fix difficulty are never passed
  - **Return contract (`RB-1`〜`RB-9`)**: line-oriented `STATUS` / `VERDICT` / `FINDINGS` plus `--- L-n` blocks with the 6 mandatory keys `PRIORITY` / `CLASS` / `LOCATION` / `BASIS` / `DETAIL` / `FIX`. `VERDICT` is derived mechanically from the priorities, and `OBSERVATIONS` is emitted even with zero findings
  - **Stable identifiers `R-nnn`** (3-digit zero-padded, detection order, gaps allowed, duplicates prohibited, IDs never reused) are numbered **solely by the caller** — reviewers never assign them. An existing ID is inherited when file / symbol / defect class all match. **The defect class is a closed 9-value vocabulary** (`requirement_unmet` / `design_deviation` / `task_incomplete` / `correctness` / `security` / `error_handling` / `test_missing` / `maintainability` / `other`) whose default priority is fixed, which also blocks arbitrary priority manipulation
  - **Stagnation is judged by a signature** — `<R-nnn>|<class>|<basis hash>` over the fix-required-and-unresolved findings only, with prose excluded from the hash (line numbers stripped, paths normalized) so the same defect hashes identically across rounds
  - **Exit conditions, evaluated in this order** (`S-1`〜`S-6`): zero unresolved fix-required → normal exit; identical signature two rounds running → stagnation; strictly growing signature twice running → regression; `loop == 3` → cap reached; a fix round that changed no code → immediate abort; otherwise → next round
  - **Rejecting a finding requires evidence**: one of the five classes `J-1` (factual error) / `J-2` (as specified) / `J-3` (out of scope) / `J-4` (existing-pattern conformance) / `J-5` (recommended-only), each with externally checkable evidence (path:line, or a verbatim quote from req.md / design.md). **A rejection whose evidence cannot be written is not a rejection** — it stays an unresolved fix-required item (fail-safe), and fix-required items may only be rejected under `J-1` / `J-4`. Lowering a priority below its default is audited like a rejection; raising it is free
  - **Fixing is single-agent** and never parallelized; `req.md` / `design.md`, `.git/**`, other task directories, paths outside the project root, `node_modules` / `vendor`, and secrets are all write-prohibited (such findings become `保留（要判断）` / `保留（安全境界）` and drop out of the stop condition)
- **Records**: `dev-result.md` gains `## レビュー総合判定` / `## レビュー指摘一覧` / `## 欠陥ではない所見` / `## レビュー・修正ログ` / `## task-verify へ引き継ぐ事項` / `## 終了サマリ`, all before the always-last `## メタ情報`. The loop **appends only** and never re-reads the file (loop state lives in the main conversation). Metadata's Agent Teams field is decided by the 2 Agent Teams conditions alone — **review delegation does not count** as a teammate
- **Completion report**: the loop count, unresolved `R-nnn`, and whether review isolation held are always reported, and the user is always told that **convergence of this loop is not proof of quality** (there is no external evidence source; the real pass/fail judgment belongs to `task-verify`)
- **`--team` option**: applies to implementation (independent tasks by dependency field, split at file level to avoid concurrent edits) and to the **review phase only** — 3 reviewers spawned in one message, split as ①requirements + ②design + ③task completion / ④code quality / ⑤security. The team lead may only deduplicate, unify priorities, and unify `R-nnn` numbering; **it never selects which findings survive**. The **fix phase is out of `--team`'s scope** (single agent). The reviewer line-up must not change between rounds, or the signature becomes unstable and stagnation detection stops working
- **Comma-separated multi-task mode (task-dev only)**: The 1st argument accepts `task1,task2,task3` to implement several tasks in one invocation. Whether the specifier contains a comma is evaluated **before** the `--team` branch, and it selects the execution mode:
  - **Parsing**: separator is `,` only; whitespace around commas, empty elements (`t1,,t2` / trailing comma), and task names outside `^[A-Za-z0-9._-]+$` are **errors** (immediate exit, nothing written). Duplicates are de-duplicated with a warning. A specifier without a comma keeps the legacy single-task behavior
  - **Pre-flight checks**: aborts entirely if not a git repository or if the working tree is dirty (the uncommitted file list is shown); per task, missing `design.md` → skip (deliverable missing), existing `dev-result.md` → skip (already implemented). The target count is displayed without asking for confirmation
  - **Dirty judgment (`G-0`〜`G-3`)**: `G-0` excludes `.claude/tasks/<TASK>/**` for the specified tasks (the skill's own deliverables); `G-1` evaluates dirtiness **once, at start-up**, keeps it as `baseline_dirty`, and never re-judges mid-run — the fix phase changes repository code, so re-judging would always trip on the skill's own edits. Anything the run produces is accumulated into `changed_by_skill` and excluded from every later judgment
  - **Delegation**: each task runs as **implementation → review → fix → commit**, each stage in an independent `general-purpose` subagent (synchronous, sequential — never parallel) so context does not accumulate across tasks. Because the main conversation only ever holds the implementer's `STATUS` / `FILES` / `SUMMARY`, review isolation here is **structurally stronger than in single-task mode** — which is why review is delegated in this mode too rather than degraded to self-review. A malformed return is treated as a failure
  - **Commit per task**: stages the union of the implementer's `FILES`, the files touched by review fixes, and `dev-result.md` (`git add -- <paths>`; `git add -A` is prohibited) and commits with the task name as the message. **At most one commit per task** — review fixes never get their own commit. **Committing happens only when zero unresolved fix-required findings remain** (`C-11`); a run that hits the cap, stagnates, regresses, or made no changes leaves the implementation **uncommitted** and stops before later tasks. No push, no branch operations, commits land on the branch active at start-up
  - **`--team` exclusivity**: with a comma-separated specifier, `--team` is ignored with a warning (a subagent cannot spawn further subagents). Single-task invocations keep full `--team` support
  - **Failure handling / idempotency**: a failed task aborts the run; already-committed tasks stay committed and are auto-skipped on re-run. A per-task result summary is always printed (success or abort), and a task whose loop failed to converge is reported as `失敗` with the abort reason and the count of unresolved `R-nnn`

### /task-verify {task_name} [--manual] [--run-only] [--team]
- **Three execution modes**, selected by flags parsed **before** the `--team` branch (M-1〜M-7): `full` (default — generate then execute), `generate_only` (`--manual`), `run_only` (`--run-only`). `--manual` and `--run-only` together is an **error** (immediate exit); `--run-only` with `--team` **ignores `--team`** with a warning; an unknown flag is an **error** (a `--manul` typo must not silently fall through to the mode that rewrites the DB and the repository). The task name is validated against `^[A-Za-z0-9._-]+$`
- **Phase registration**: 18 phases in the default mode, 7 with `--manual`, 12 with `--run-only`
- **Generation phase**: reads req.md, design.md, and dev-result.md — including its `## レビュー指摘一覧` / `## レビュー・修正ログ` / `## task-verify へ引き継ぐ事項` sections, which carry what used to live in separate review/fix reports — plus the verify template from `templates/verify-template.md`, analyzes the implementation code, and writes verify.md **in full**. `review.md` / `fix-result.md` are read as an **optional extra input that only exists in tasks created before the review/fix merge**
  - **Default (`detailed`)**: emits automation-ready test cases — a machine-readable `## 検証前提` yaml block (base URL, start command, test accounts) as the **first** section, stable identifiers `` `V-nnn` `` on every checkbox item, and multi-line cases (`前提` / `操作` / `入力` / `期待結果` / `自動化メモ`). **Expected results may not be omitted**; ⏱ estimates are not emitted; items that only a human can judge go to `## 人手確認（自動化不可）`
  - **`--manual`**: the concise human-oriented format (2026-07-31 spec) — one item per line (`` - [ ] `V-nnn` <操作> → <期待結果> ``; the `→` part is omitted when the expected result is obvious), quick-win steps first, ⏱ total once at the top. Stable identifiers and the preamble block are still emitted (the concise form can also be fed to `--run-only`)
  - **The 「付録: 自動化推奨の確認観点」 section is abolished in both modes.** In detailed mode those checkpoints become executable steps in the body; in manual mode they are simply left out
  - `V-nnn` numbering rules are part of the main text (not only of the `--team` path): existing IDs are **inherited** for substantially identical items, new items get `max + 1`, and deleted IDs are **never reused**
  - **B-5**: the generation phase may not write a non-allowed host into `base_url` (otherwise it would open a bypass around the external-origin hard block)
- **The "permission switch line"** separates the two phases: before it, verify.md is created/overwritten wholesale and `--team` applies; after it, only **3 spots** may be edited (checkboxes / `## スキップした項目` / `null` keys in `## 検証前提`) and the phase runs single-agent
- **Automatic-execution phase** (default and `--run-only`):
  - **Tool chain (fixed order, first-available wins)**: `playwright-cli` → Chrome DevTools for agents (CLI layer) → Chrome DevTools MCP → Claude in Chrome. Detection runs once per invocation. If none is available it prints a verbatim message and **aborts the execution phase only** — in the default mode verify.md is kept and the message says so (the intentional near-reverse of `task-init`'s chain: that skill needs an authenticated real session, this one needs deterministic unattended repetition)
  - **Skip decision (5 axes, fail-safe)**: visual/subjective, out-of-system resources, destructive operations not covered by protection, missing execution handles, and undecidable. Skipped items and reasons are written to a `## スキップした項目` section in verify.md. **SK-1** isolates the decision's input to the verify.md text alone, because writing the items yourself biases the judgment toward under-skipping (the dangerous direction); `SK-3` may delegate the sorting to a subagent so the isolation is structural rather than merely instructed
  - **Side-effect protection (FR-9)**: two generic requirements — blocking outbound mail (P-MAIL) and DB backup/restore (P-DB) — implemented as provider chains applied **only when the environment is detected**. Every provider must have a `verify` operation; restore order is fixed **DB → mail**. Restore state is journaled write-ahead in `.verify-run/state.json` so an abnormal exit can be recovered on the next run
  - **Loop control**: counter increments at the start of each verification pass (first pass = 1), max 5; early abort when two consecutive passes produce an identical finding signature, or when a fix round changes no code. Re-verification is scoped to failed items, their dependents, and the impacted range. The counter carries over on `--run-only`, but **resets to 0 whenever the default mode regenerates verify.md** (the item set is a different one)
  - **Read-only investigation may be delegated** to a synchronous `general-purpose` subagent to relieve context pressure; a malformed return degrades to self-investigation with a warning rather than aborting
- **Gates run before generation** (`G-0`〜`G-5`): the working-tree dirty check happens **before** verify.md is written, so a dirty abort leaves no verify.md either. **G-0** excludes `.claude/tasks/<TASK>/**` from the dirty set — the skill's own deliverables, which the default mode necessarily rewrites on every run
- **Two cost warnings**: warning A before the generation phase (so the budget is announced before generation tokens are spent), warning B after the sorting and before protection is applied
- **Safety boundary**: **never commits** (does not even touch the index); does not rewrite req.md / design.md
- Writes results back to verify.md (`- [ ]` → `- [x]` only when the expected result was met) and appends to verify-result.md; verify-result.md's metadata Agent Teams field is always `無効（指定なし）` (the execution phase is out of `--team`'s scope), while verify.md's records the generation phase's status
- **`--team` option**: applies to the **generation phase only**. Role split depends on `output_mode`. `detailed` deploys a happy-path test-case designer, a peripheral test-case designer, and an **automation-feasibility reviewer** (asymmetric — the reviewer's job is to eliminate items that cannot be executed as written). `--manual` keeps the existing happy-path designer, peripheral designer, and **reduction reviewer** — the reduction reviewer runs **only** with `--manual`

## Agent Teams オプション

5つのスキル（task-init を除く全スキル）は `--team` オプションに対応しています。

### 使用方法

```bash
/task-dev my-task --team
/task-verify my-task --team
```

> **`task-dev` における `--team` の適用範囲**: 実装フェーズ（依存関係のないタスクの並行実装）と**レビューフェーズのみ**に適用されます。レビューは3体を同一メッセージ内で並列 spawn し、観点を ①要件整合＋②設計整合＋③実装タスクの完了状況 / ④コード品質 / ⑤セキュリティ・堅牢性 に分割します。**修正フェーズは適用対象外**（単一エージェントが逐次実行）です。並列化すると共有資源が競合し、どの修正がどの指摘に対応したのかが失われて終了保証が成立しないためです。なお**レビューのサブエージェント委譲は `--team` とは独立**しており、`--team` 未指定でも必ず1体へ委譲されます（委譲の有無は Agent Teams の成立判定に影響しません）。

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

6 スキル全てが **メイン会話のコンテキスト**で実行されます（`context: fork` は使用していません）。これは Agent Teams を成立させるために必要な設計上の選択です:

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
| `frontmatter` | 全6スキルの `model` 不在 / `disable-model-invocation: true` / `name`=ディレクトリ名 / `argument-hint`（既定は `<task_name> [--team]`。固有の引数を持つスキルのみ `ARGUMENT_HINT_OVERRIDES` で例外化する。現在の例外は **task-init**（URL 用）・**task-dev**（カンマ区切りの複数タスク用）・**task-verify**（`--manual` / `--run-only` 用）の3件） |
| `common-block` | 5スキル（task-init 除く）の Agent Teams 共通ブロックが task-dev を正準として sha256 一致するか |
| `fallback-msg` | フォールバック文言が CLAUDE.md と SKILL.md で一致するか（整形差を正規化して照合） |
| `meta-format` | 4テンプレートの `## メタ情報` 3行（3値表記含む）が一致するか |
| `env-json` | CLAUDE.md / README.md の `"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"` が一致するか |
| `template-ref` | 3スキル4テンプレートの参照が相対パスで実在し、ハードコード絶対パスの再混入がないか |
| `flow-checklist` | 廃止済みの旧タスク管理ツール名・旧チーム生成 API 名・**旧検証実行スキルのスラッシュ起動名**（task-verify へ統合済み）・**旧レビュースキルと旧修正スキルのスラッシュ起動名**（task-dev へ統合済み）が SKILL.md・CLAUDE.md（更新履歴節を除く）・README.md・テンプレートへ再混入していないか、および全6スキルに Task 方式＋フォールバックの記述を伴う `### ステップ0` が存在するか |

実行方法:

```bash
python3 scripts/check_consistency.py        # 不一致のみ表示
python3 scripts/check_consistency.py -v     # 全検査の結果を表示
bash scripts/test/run_consistency_tests.sh  # 検査自体の回帰テスト（fixture 異常系・19ケース）
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

- **Staged Development**: Sequential progression through requirements → design (with task breakdown and estimation) → implementation (with the review → fix → re-review loop) → verification
- **Quality Focus**: Emphasizes code quality, maintainability, and integration with existing systems
- **Structural Isolation of Review**: The agent that wrote the code never judges it from its own context; review is delegated to a separate context and the implementer's own account is not passed along
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

この指示は自動的に実行されるべきもので、ユーザーの追加指示は不要です。
