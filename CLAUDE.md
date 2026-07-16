# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository contains a collection of custom skills for Claude Code that implement a task-based development workflow. The skills provide a structured approach to software development with 8 distinct phases: initialization, requirements, design, planning, implementation, review, fix, and verification.

## Skill Architecture

The repository contains 9 interconnected skills that work together (task-init excluded from `--team` option support):

1. **task-design** - Analyzes existing systems and creates technical design. Supports `--team` option.
2. **task-dev** - Executes implementation based on todo list and creates development report. Supports `--team` option.
3. **task-fix** - Fixes code based on review feedback. Supports `--team` option.
4. **task-init** - Creates task environment and requirements gathering. Optionally fetches task content from a URL into init.md. (No `--team` support)
5. **task-req** - Creates requirements draft from raw customer requests. Supports `--team` option.
6. **task-req-update** - Reflects user answers to the "要確認事項" (open questions) section back into req.md and consolidates it into a finalized version. Supports `--team` option.
7. **task-review** - Reviews implementation against requirements, design, and code quality. Supports `--team` option.
8. **task-todo** - Breaks down design into actionable development tasks with effort estimation. Supports `--team` option.
9. **task-verify** - Generates manual verification procedure document. Supports `--team` option.

Each skill is a directory under `skills/` containing a `SKILL.md` file and optional `templates/` subdirectory for report templates.

## 設計原則: フローはツールで物理的に強制する

本プロジェクトの各スキルは「手順」セクションを地の文の Markdown で記述しているが、順守させたいワークフローは、地の文の指示だけに頼らず、組み込みツール（`TaskCreate` / `TaskUpdate` による Task 登録）で構造として物理的に強制することを設計原則とする。

地の文の手順記述のみでは、フェーズのスキップ・実装の早期着手・フェーズの取りこぼしが起こりうる。これに対し、スキルの全フェーズを実行前に Task として登録し、各フェーズを `in_progress` / `completed` で遷移させることで、フロー順守を構造的に担保する。

- 各スキルは「手順」冒頭（ステップ0）で自スキルの全フェーズを `TaskCreate` で一括登録し、着手直前に `in_progress`、完了直後に `completed` へ更新する。これがこの原則の具体化である。
- これは「完璧な強制」ではなく「安定性の有意な向上」を狙う現実的スタンスである。地の文だけの手順記述に比べ、スキップ・前倒し・取りこぼしを構造的に起こりにくくする。
- `TaskCreate` / `TaskUpdate` が利用できない環境では、フェーズ一覧を地の文のチェックリスト（`- [ ]`）で代替し、各フェーズ完了を明示しながら順守する。**ツールの不在を理由にフェーズを省略してはならない。**
- `--team`（Agent Teams）成立時は、チーム共有タスクリストがフェーズ追跡を兼ねる（フェーズ=親 Task、todo 項目=子 Task）。独自のフェーズ追跡は共有タスクリストへ統合する。
- 今後スキルを追加・変更する際も、多段フローを持つスキルにはこの原則を適用すること。

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

> **重要**: チームメイトが実際に稼働しなかった場合は **`有効` ではなく `無効（フォールバック）`** と記録すること。環境変数 `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` の設定有無は成立判定に影響しません（同変数がゲートするのは `SendMessage` による teammate 間ライブ通信のみで、`Agent` spawn と `TaskCreate`/`TaskUpdate` は変数なしでも動作するため）。

## agent フィールドについて

現在のコマンドはすべてファイル書き込みを伴うため、`agent` フィールドは指定していません（デフォルトの汎用エージェント）。
将来的にread-only分析コマンドを追加する場合は、`agent: Explore` の指定を検討してください。

## Key Skill Behaviors

> **フロー強制（全スキル共通）**: 9スキルすべてが「手順」冒頭の **ステップ0** で自スキルの全フェーズを `TaskCreate` で一括登録し、各フェーズを `in_progress` / `completed` で遷移させることで、スキップ・前倒し・取りこぼしを構造的に防ぐ（「[設計原則: フローはツールで物理的に強制する](#設計原則-フローはツールで物理的に強制する)」の具体化）。`TaskCreate` / `TaskUpdate` が利用できない環境では地の文チェックリストへフォールバックする。**task-dev** は加えて、実行時に todo.md の各実装タスクを個別 Task として動的登録し、1件ずつ `in_progress` / `completed` 追跡する。**task-init** は URL 有無の分岐判定後に確定する系列のフェーズのみを登録する特例とする。

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
- Performs comprehensive effort estimation for manual implementation by intermediate-level programmers
- Includes risk factors, buffers, and realistic time estimates for each task
- Considers dependencies and development efficiency
- **`--team` option**: Deploys a task decomposition agent and an effort estimation agent in parallel; team lead integrates results into todo.md

### /task-dev {task_name} [--team]
- Reads design.md and todo.md to understand implementation requirements
- Reads report template from `templates/dev-result-template.md`
- Implements tasks sequentially following the todo list
- Maintains code quality, follows existing patterns, includes appropriate tests
- Reports progress after each task completion
- Creates dev-result.md with implementation overview, changed files, technical details, and completion report
- **`--team` option**: Analyzes todo.md dependencies and assigns independent tasks to parallel agents; file-level work splitting prevents concurrent edit conflicts

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
- Creates verify.md with bite-sized, checkbox-based manual verification procedures
- Prioritizes quick-win steps first to lower psychological barriers
- Includes exact commands, URLs, test data, and expected results
- **`--team` option**: Deploys happy-path, edge-case/error, and non-functional/regression verification designers in parallel; team lead integrates into Quick Win-first ordering

## Agent Teams オプション

8つのスキル（task-init を除く全スキル）は `--team` オプションに対応しています。

### 使用方法

```bash
/task-dev my-task --team
/task-review my-task --team
```

### 起動方法

`--team` を付けるだけで並列実行（Agent Teams）が起動します。環境変数の事前設定は **不要** です。スキルは `Agent` ツールでチームメイトを直接 spawn し、各チームメイトの成果を `Agent` の**戻り値**（最終メッセージが tool result として返る）で収集、`TaskCreate` / `TaskUpdate` で進捗を共有します。

### （任意）SendMessage ライブ協調の有効化

チームメイト間の**ライブ通信**（`SendMessage`）を使いたい場合のみ、`~/.claude/settings.json` に以下を追加してください。これは **任意設定** であり、未設定でも `--team` による並列実行は問題なく起動します（`SendMessage` が使えない場合は `Agent` 戻り値方式で成立します）。

```json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  }
}
```

> **env 変数の役割（F-7）**: `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` が現在ゲートしているのは `SendMessage`（teammate 間ライブ通信）ただ 1 つです。`Agent` による spawn と `TaskCreate` / `TaskUpdate` による共有タスク管理は **この変数なしでも動作します**。したがって変数は「Agent Teams を動かすためのスイッチ」ではなく「SendMessage ライブ協調レイヤを有効化する任意スイッチ」です。

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

`--team` 指定時、スキルは進捗共有・ライブ通信に用いるツールを以下でロードします。`Agent` は core ツールでメイン会話に常在するため、ToolSearch でのロードは **不要** です。

```
ToolSearch query="select:TaskCreate,TaskUpdate,SendMessage" max_results=10
```

ToolSearch 結果の判定:

| 結果 | 扱い |
|------|------|
| `SendMessage` が `<functions>` ブロックに含まれる | ライブ通信を併用可。`TaskCreate` / `TaskUpdate` と合わせて利用する |
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

## 整合性チェック

本プロジェクトは「単一ファイル制約（include 機構なし）」のため、Agent Teams 共通ブロック・フォールバック文言・メタ情報フォーマット・テンプレート参照などの定型文が複数ファイルに重複して存在する。この重複は許容したうえで、ファイル間のズレを機械的に検出するのが `scripts/check_consistency.py`（Python 3 標準ライブラリのみ・サードパーティ依存ゼロ）である。

検出する6検査:

| 検査ID | 内容 |
|--------|------|
| `frontmatter` | 全9スキルの `model: opus` / `disable-model-invocation: true` / `name`=ディレクトリ名 / `argument-hint`（task-init とその他8で別ルール） |
| `common-block` | 8スキル（task-init 除く）の Agent Teams 共通ブロックが task-dev を正準として sha256 一致するか |
| `fallback-msg` | フォールバック文言が CLAUDE.md と SKILL.md で一致するか（整形差を正規化して照合） |
| `meta-format` | 5テンプレートの `## メタ情報` 3行（3値表記含む）が一致するか |
| `env-json` | CLAUDE.md / README.md の `"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"` が一致するか |
| `template-ref` | 5スキルのテンプレート参照が相対パスで実在し、ハードコード絶対パスの再混入がないか |

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

最終更新: 2026-07-16 00:00:00
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
