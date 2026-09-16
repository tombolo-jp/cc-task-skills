# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository contains a collection of custom skills for Claude Code that implement a task-based development workflow. The skills provide a structured approach to software development with 5 distinct phases: initialization, requirements, design (which now covers task breakdown and effort estimation as well), implementation (which now covers review and fix as a closed loop inside the same run), and verification (the verification phase covers both procedure generation and automated execution).

## リポジトリの文書構成

| ファイル | 役割 |
|---|---|
| `CLAUDE.md`（本ファイル） | **規範の正本**。設計原則・禁止事項・スキル横断の決定事項。全セッションで常時ロードされるため、論証と履歴は持たない |
| `skills/<skill>/SKILL.md` | 各スキルの**仕様の正本**。常時ロードされるのは起動されたスキルの分のみ |
| `skills/<skill>/references/*.md` | SKILL.md から切り出した規約。**該当フェーズに着手した時点でのみ読み込む**（「[設計原則: 規約は必要なフェーズで読み込む](#設計原則-規約は必要なフェーズで読み込む)」） |
| `skills/<skill>/templates/*.md` | 生成物のテンプレート。生成の直前に読み込む |
| `docs/design-principles.md` | 設計原則の**論証・実測結果・改訂履歴**。規範そのものではない |
| `docs/skill-behaviors.md` | スキル別の挙動仕様（引数・分岐・終了条件・記録要件）の詳細 |
| `docs/agent-teams.md` | Agent Teams の使い方・コスト・実行コンテキスト |
| `README.md` | 利用者向けドキュメント |

**規範を変更する場合は `CLAUDE.md` と該当 `SKILL.md` を更新すること。** `docs/` は根拠の保管場所であり、ここだけを直しても挙動は変わらない。

## Skill Architecture

The repository contains 6 interconnected skills that work together (only task-init is excluded from `--team` option support):

1. **task-design** - Analyzes existing systems and creates technical design, **then breaks it down into an implementation task list (`T-nnn`) with effort estimation in the same run**. Supports `--team` option.
2. **task-dev** - Executes implementation based on the design's implementation task list, **then automatically runs a review → fix → re-review closed loop (max 2 rounds; the 2nd round runs only when must-fix findings remain) inside the same invocation**, and creates the development report. Review is **always delegated to a separate-context subagent** (regardless of `--team`) so that the agent which wrote the code never judges it from its own context; fixing is always single-agent. Review findings, the loop log, and the exit summary are **appended to `dev-result.md`** (no separate review/fix report files). Supports `--team` option (**review phase only** — 1 reviewer without it, 3 in parallel with it). **Also accepts a comma-separated list of task names** for bulk sequential implementation (delegating each task to an isolated subagent and committing per task); `--team` is ignored in that mode.
3. **task-init** - Creates task environment and requirements gathering. Optionally fetches task content from a URL into init.md. (No `--team` support)
4. **task-req** - Creates requirements draft from raw customer requests. Supports `--team` option.
5. **task-req-update** - Reflects user answers to the "要確認事項" (open questions) section back into req.md and consolidates it into a finalized version. Supports `--team` option.
6. **task-verify** - Generates a verification procedure document **and, by default, executes it**. The generation phase emits **detailed, automation-ready test cases** (machine-readable preamble block, stable `V-nnn` identifiers, mandatory expected results); the automatic-execution phase runs those checkbox items, records required fixes in `verify-result.md`, and loops fix → re-verify (max 3 rounds). `--manual` switches to the concise human-oriented format and **generates only**; `--run-only` **executes only**. Supports `--team` option (**generation phase only**).

Each skill is a directory under `skills/` containing a `SKILL.md` file and optional `templates/` subdirectory for report templates.

## 設計原則: フローは Task ツールで明示的に追跡する

本プロジェクトの各スキルは「手順」セクションを地の文の Markdown で記述しているが、順守させたいワークフローは、手順の説明文に紛れさせず、**着手前に登録する Task** として明示的に追跡することを設計原則とする。Task ツールが利用できない環境では、構造化チェックリストの宣言へフォールバックする。

地の文の手順記述のみでは、フェーズのスキップ・実装の早期着手・フェーズの取りこぼしが起こりうる。これに対し、スキルの全フェーズを着手前に登録し、各フェーズの着手時に `in_progress`、完了時に `completed` へ遷移させることで、進捗と未達を常に可視化する。

- 各スキルは「手順」冒頭（ステップ0）で進捗管理用の Task ツールをロードし、自スキルの全フェーズを Task として登録して状態遷移させる。これがこの原則の具体化である。登録は省略不可（成果物の必須要素）とし、スキップ・前倒し・状態遷移の省略を禁止事項として明記する。**ツールのロード手順・2方式の判定表・禁止事項は全6スキル共通のため `skills/<skill>/references/phase-tracking.md` へ切り出し**、SKILL.md のステップ0 はポインタと**そのスキル固有のフェーズ一覧**だけを持つ。
- **ツールによる追跡はハーネス UI と連動する**。ライブタスク表示・スピナーに進行中フェーズが現れるため、応答本文へチェックリストを毎回再掲する必要がなくなり、記述も出力も簡潔になる。
- **フォールバックにより可用性変動へ耐える**。ツールのロード可否はステップ0 で1回だけ判定し、取得できなければチェックリスト宣言方式で同じフェーズ集合を追跡する。判定はフェーズごとに繰り返さない。フォールバックしたことを告知するメッセージは出さない（チェックリスト自体が進捗表示を兼ねるため、利用者に不利益がない）。
- これは「完璧な強制」ではなく「安定性の有意な向上」を狙う現実的スタンスである。ツールを主経路に置いても、登録そのものを行うか否かは最終的に LLM に依存する。それでも地の文だけの手順記述に比べ、スキップ・前倒し・取りこぼしを構造的に起こりにくくする。
- `--team`（Agent Teams）成立時も、チームリードが自身の Task 一覧で全フェーズを追跡する。チームメイトへ委任した作業は `Agent` の戻り値で完了を確認してから `completed` へ遷移させる。
- 今後スキルを追加・変更する際も、多段フローを持つスキルにはこの原則を適用すること。

> **Task ツールの提供はモデル依存でゲートされる。** Claude Code 2.1.233 以降、しきい値以上のモデルでは進捗管理用の4ツールが既定で無効である。主経路を実際に通すには `~/.claude/settings.json` へ `"CLAUDE_CODE_ENABLE_TODO_TOOLS": "1"` が必要（README.md「インストール」手順3と同一内容）。リモートフラグはロールアウト状況で変わりうるため、**ステップ0 の2方式分岐は今後も維持すること**。判定ロジックの実測結果・本原則の改訂履歴は [`docs/design-principles.md`](docs/design-principles.md) にある。なおこの env 変数は Agent Teams の `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` とは**無関係**である。

この原則の各スキルへの反映状況と整合性は、`scripts/check_consistency.py`（後述「整合性チェック」）で機械的に検証する。

## 設計原則: Dynamic Workflows を使用しない

**全6スキルにおいて `Workflow` ツール（Dynamic Workflows）を使用しない。** 委譲は `name` を付けない同期 `Agent` 委譲（`run_in_background: false`。成果を戻り値で受領する）で行う。

- **理由は「実装完了後の差分を検証するために Dynamic Workflows を用いるのは重すぎる」ため。** `Workflow` は多段のファンアウトと大規模な並列度を前提とした実行基盤であり、スキル1回あたりのトークン消費と実行時間が実用上許容しがたい水準になった。委譲体数を 1〜3 体に抑えるなら、同一メッセージ内へ複数の `Agent` 呼び出しを並べるだけで並列実行は成立する。
- **失うのはツール層の型保証だけであり、構造的隔離は失わない。** 隔離を成立させているのは「別コンテキストの主体が判定すること」と「`dev-result.md` を渡さないこと」の2点であり、どちらも同期 `Agent` 委譲で完全に成立する。`Workflow` が提供していたのは**戻り値の型保証**であって隔離ではない。型保証の代替は「[設計原則: レビューは構造的に隔離する](#設計原則-レビューは構造的に隔離する)」の `RV-1`〜`RV-6`（スキル本体による検証・fail-safe 側への丸め・形式逸脱時の1回だけの再委譲）が担う。
- **廃止した識別子は欠番として残す。** `task-dev` の degrade 梯子は `D-1` を欠番とし、`D-2`（同期 `Agent` 委譲）を主経路へ格上げした。`D-1` を再定義すると、過去タスクの `dev-result.md` に残る `degrade: D-1 → D-2` の記録が別の意味になり監査可能性が壊れるためである。
- **この方針は `scripts/check_consistency.py` の `no-workflow` 検査（後述「整合性チェック」）が機械的に担保する。** 検査は**ランタイム固有の API 名**（`export const meta` / `resumeFromRunId` / `scriptPath` / `agent(` / `parallel(` / `pipeline(` / `phase(`）を禁止語彙とし、**単語 `Workflow` そのものは禁止しない**（禁止すると本節のような方針記述自体が検出され、検査が成立しない）。禁止語彙を字面として列挙せざるをえない行には、行内へ許可マーカーを置いて除外する。 <!-- allow-workflow-mention -->

## 設計原則: 規約は必要なフェーズで読み込む

**分量の大きい定型文・規約は SKILL.md 本体に置かず、`skills/<skill>/references/*.md` へ切り出し、そのフェーズに着手する時点で Read する。** SKILL.md 本体には「いつ読むか」を指す数行のポインタだけを残す。

- **常時ロードされる行数がスキルの実効的なコストである。** 指定していないオプション（`--team`）の規約や、まだ到達していないフェーズ（レビュー委譲の戻り値契約）を実装中のコンテキストへ載せることは、変更が触れる実コードを読むために使えたはずの予算を先に消費する。読解を削らずに仕様の常駐量を削るのが本原則である。
- **切り出す単位はフェーズ境界と一致させる。** 現行の3ファイルは、`agent-teams.md`（`--team` 指定時のみ）・`phase-tracking.md`（ステップ0 で必ず）・`task-dev` の `review-contract.md`（レビュー・修正フェーズ着手直前。複数タスクモードでは実装委譲の直前にも）である。フェーズ境界と無関係な分割は、読み込み忘れを招くため行わない。
- **「読まれない参照」は規約の消失と同じである。** 本体から切り出した以上、参照が消えればその規約は永久に読まれない。`scripts/check_consistency.py` の `reference-file` 検査が、実在・スキル間の sha256 一致・**SKILL.md 本文からの参照の存在**の3点を機械的に担保する。
- **重複配置は維持する。** 参照ファイルはスキルごとに同一内容で置く（`skills/*` をそのままコピーする既存のインストール手順を変えないため、および skills ルートへ SKILL.md を持たないディレクトリを作らないため）。重複そのものは従来どおり許容し、ズレは検査が担保する。
- **逐語ブロックは要約して本体へ戻さない。** 委譲プロンプトの逐語ブロック（`review-contract.md` の 5-6-2）を記憶や要約から再構成すると、隔離規約と却下監査が「構造」から「指示」へ退化する。参照ファイルを読まずに委譲することを禁止事項とする。

## 設計原則: レビューは構造的に隔離する

同一実行内で実装とレビューを行うスキル（現時点では `task-dev`）は、**レビューを必ず別コンテキストのサブエージェントへ委譲する**ことを設計原則とする。実装時に「この設計で要件を満たす」と結論した主体が、レビュー時に「満たしていない」と言うのは直前の自分の結論の否認であり、**過少指摘（危険側）が構造的に優勢**になる。被害は「要件未充足・脆弱性を含んだ実装が、レビュー済みという記録つきでコミットされること」である。

この隔離は「実装時の判断を思い出さないでください」という**指示では成立しない**。委譲プロンプトへ埋め込んでよい項目を限定列挙し、**実装担当の自己申告である `dev-result.md` を渡さない**ことで、隔離を指示ではなく**構造**にする。隔離の実現手段は **`name` を付けない同期 `Agent` 委譲**（`run_in_background: false`。成果を戻り値で受領する）であり、成果が戻り値で返らない経路（`name` 付きのバックグラウンド spawn）を委譲に用いない。レビュー対象は「変更ファイルのパスの配列」と、`git diff --unified=0` から機械的に得られる**変更行範囲**（観点④⑤の重点範囲）としてのみ渡し、**差分本文**・実装意図・変更理由・前周の却下理由は渡さない。同型の対処は `task-verify` のスキップ判定（SK-1〜SK-3）で先行して採っている。

- **委譲は `--team` の有無と独立である。** `--team` は「並列体数と分割粒度のプロファイル選択」にすぎず、委譲そのものは常に必須である。自己レビューが許されるのは degrade 梯子の最終段のみで、その場合は必ず告知し成果物へ記録する。
- **「委譲の不成立」も終了保証の対象に含める。** 隔離した先から成果が返らなければ、レビューは実施されていない。`findings` が空であることを「指摘0件」と解釈してよいのは**全担当が成果を返したときだけ**であり、1体でも `null` なら未確認範囲として記録し、全滅なら終了区分を `レビュー未実施（委譲不成立）` とする。**「何も検査されなかった」を「問題なし」と書かないこと**が、この原則の実効性を決める。
- **外部の証拠源を持たないループには終了保証を機械的に置く。** 同一入力に対する同一モデルの再判断には新情報が入らないため、指摘へ安定識別子を採番し、散文を除いた署名で停滞を判定し、ループ上限を設ける（`task-dev` は**最大2周**で、2周目は修正必須が残った場合にのみ回す）。
- **ツール層の型保証を失う経路では、検証をスキル本体が持つ。** 戻り値は「応答末尾の ```json フェンス」を契約とし、スキル本体が必須キー・語彙・型を検証する（`RV-1`〜`RV-6`）。語彙外の値は**危険側へ倒さない向き**へ丸め（例: 語彙外の `priority` は `高`）、丸めた事実を成果物へ記録する。形式逸脱は1回だけ再委譲し、なお不合格なら「未検査」として扱う（`E-36`）。
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

> **精度とコスト**: 各スキルは高精度な設計・レビュー・実装を要求するため **Opus 系の使用を推奨**するが、強制はしない。軽量モデルのセッションでは生成物の品質が落ちうる。`model` 固定をやめた経緯は [`docs/design-principles.md`](docs/design-principles.md) にある。

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
| `--team` 指定あり、かつ ① `Agent` ツールで委譲した担当が少なくとも 1 体実際に稼働（成果を返した）、の条件を満たす | `有効` |
| `--team` 指定なし | `無効（指定なし）` |
| `--team` 指定あり、かつ 委譲した担当が 1 体も稼働しなかった（`Agent` が利用不可、または全ての委譲から成果を受領できなかった） | `無効（フォールバック）` |

> **重要**: 委譲した担当が実際に稼働しなかった場合は **`有効` ではなく `無効（フォールバック）`** と記録すること。環境変数 `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` の設定有無は成立判定に影響しません（同変数がゲートするのは `SendMessage` による teammate 間ライブ通信のみで、`Agent` spawn は変数なしでも動作するため）。

## agent フィールドについて

現在のコマンドはすべてファイル書き込みを伴うため、`agent` フィールドは指定していません（デフォルトの汎用エージェント）。
将来的にread-only分析コマンドを追加する場合は、`agent: Explore` の指定を検討してください。

## Key Skill Behaviors

> **フロー強制（全スキル共通）**: 6スキルすべてが「手順」冒頭の **ステップ0** で `references/phase-tracking.md`（共通の判定手順）を読み込んだうえで、自スキルの全フェーズを Task として登録し、着手時に `in_progress`・完了時に `completed` へ遷移させることで、スキップ・前倒し・取りこぼしを構造的に防ぐ（Task ツールが利用できない場合はチェックリスト宣言へフォールバックする。「[設計原則: フローは Task ツールで明示的に追跡する](#設計原則-フローは-task-ツールで明示的に追跡する)」の具体化）。登録は省略不可（成果物の必須要素）。**task-dev** は単一タスクモードで12フェーズ（`--team` 非依存）、複数タスクモードで7フェーズを登録し、加えて実行時に design.md の実装タスク一覧（`T-nnn`。todo.md が存在する場合はその項目も）を Task として動的登録して1件ずつ着手・完了を明示し、さらにレビューパス1周ごとに `[review pass i/3]`（修正必須があれば `[fix pass i/3]` も）を動的追加する（パス内の個別 `R-nnn` は Task 化しない）。**task-init** は URL 有無の分岐判定後に確定する系列のフェーズのみを登録する特例とする。**task-verify** は既定モードで18フェーズ（`--manual` は7、`--run-only` は12）を登録したうえで、確認パス1周ごとに Task を動的追加する（各パス内の個別項目は Task 化しない）。

各スキルの引数・分岐・終了条件・記録要件の詳細は **[`docs/skill-behaviors.md`](docs/skill-behaviors.md)** にある（正本は各 `skills/<skill>/SKILL.md`）。

| スキル | 起動 | 要点 |
|---|---|---|
| `task-init` | `/task-init {task_name} [URL]` | タスクディレクトリと init.md / req.md（空テンプレート）を作成。URL 指定時は本文と全コメントを逐語転記し添付を `files/` へ保存する。取得手段ゼロなら**ディレクトリごと作らずエラー終了** |
| `task-req` | `/task-req {task_name} [--team]` | init.md から req.md を起こす。末尾の「要確認事項」は**回答で設計・実装の分岐が変わる問いだけ**に絞る（包含が先・除外語彙 `X-1`〜`X-6`・判定不能は残す）。0件なら節ごと出力しない |
| `task-req-update` | `/task-req-update {task_name} [--team]` | 「要確認事項」への回答を本文へ反映し確定版へ整理。未解決項目は残し、全解決で節を削除。冪等（回答 → 再実行のループ） |
| `task-design` | `/task-design {task_name} [--team]` | §1〜§11 の設計 ＋ §12 実装タスク一覧（`T-nnn`）＋ §13 工数見積もりを1回で完結。**設計確定線**より上は見積もり中 read-only。行数 ÷ 実装時間 < 30 行/h の見積もりは差し戻し（上限2周） |
| `task-dev` | `/task-dev {task_name}[,...] [--team]` | `T-nnn` 順に実装し、続けて**レビュー → 修正 → 再レビューを最大2周**（レビューは常に別コンテキストへ委譲）。**権限の切替線**の手前と奥で書き込み権限が変わる。カンマ区切りで複数タスクを逐次実装しタスクごとにコミット |
| `task-verify` | `/task-verify {task_name} [--manual] [--run-only] [--team]` | 検証手順書を生成し、既定では**そのまま自動実行**（上限5周）。`--manual` は人間向け簡潔版の生成のみ、`--run-only` は実行のみ。**コミットは一切しない** |

## Agent Teams オプション

5つのスキル（task-init を除く全スキル）は `--team` オプションに対応する。`--team` を付けるだけで並列実行が起動し、環境変数の事前設定は **不要**。使い方・コスト・実行コンテキスト・後方互換性の詳細は **[`docs/agent-teams.md`](docs/agent-teams.md)** にある。委譲規約の逐語本文は各スキルの `references/agent-teams.md` が持つ（`--team` 指定時にのみ読み込まれる）。

> **`task-dev` における `--team` の適用範囲**: 実装フェーズ（依存関係のないタスクの並行実装）と**レビューフェーズのみ**に適用される。`--team` は「**並列体数と観点分割のプロファイル選択**」を意味し、レビューは **`name` なしの同期 `Agent` 委譲**で行う（無効: **1体**が観点①〜⑤すべて / 有効: **3体**を同一メッセージ内で並列起動し、①要件整合＋②設計整合＋③実装タスクの完了状況 / ④コード品質 / ⑤セキュリティ・堅牢性 に分割）。**修正フェーズは適用対象外**（単一エージェントが逐次実行）。並列化すると共有資源が競合し、どの修正がどの指摘に対応したのかが失われて終了保証が成立しないためである。なお**レビューの委譲そのものは `--team` とは独立**しており、`--team` 未指定でも必ず1体以上へ委譲される（**`--team` 未指定時の委譲は Agent Teams の成立判定に含めない**）。

**成果の返り方は spawn の形態によって決まる。** `name` を**付けない**同期委譲（`run_in_background: false`）は最終メッセージが tool result として**戻り値で返る**。`name` を**付けた** spawn は**バックグラウンド実行**となり成果は tool result では返らない（受け取る手段は `SendMessage` だけ）。したがって**成果物を受領する委譲では `name` を付けない同期委譲を既定**とし、**`name` 付き spawn へは決してフォールバックしない**。

### Agent Teams 実行成立条件

Agent Teams が `有効` と記録されるためには、以下の **2 条件すべて** を満たす必要があります:

1. `--team` 引数が指定されていること
2. `Agent` ツールで委譲した担当が少なくとも 1 体実際に稼働（成果を返した）こと

> 環境変数 `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` は成立条件に **含めません**（F-7。同変数がゲートするのは `SendMessage` のみであり、`Agent` spawn は変数なしで動作するため）。

### フォールバック動作

`--team` 指定時に **`Agent` ツールが利用不可、またはチームメイトが 1 体も稼働しなかった場合**、スキルは以下のメッセージを **必ず** 表示してから通常モードにフォールバックします（省略・要約禁止）:

「⚠️ Agent Teams（チームメイトの起動）が現在の環境で利用できないため、Agent Teams モードを起動できません。今回は通常モードで実行します。」

**重要**: スキルは「黙ってフォールバックする」ことを禁止しています。フォールバックする場合は必ず上記メッセージを表示します。

**`--team` 未指定時の動作**:

`--team` が指定されていない場合、スキルは Agent Teams に関するメッセージを **一切表示しません**。ToolSearch・チームメイト spawn などの Agent Teams 関連操作も **一切実行しません**。

### （任意）SendMessage ライブ協調の有効化

チームメイト間の**ライブ通信**（`SendMessage`）を使いたい場合のみ、`~/.claude/settings.json` に以下を追加してください。これは **任意設定** であり、未設定でも `--team` による並列実行は問題なく起動します（`SendMessage` が使えない場合は `name` を付けない同期委譲の戻り値方式で成立します）。

```json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  }
}
```

> **env 変数の役割（F-7）**: `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` が現在ゲートしているのは `SendMessage`（teammate 間ライブ通信）ただ 1 つです。`Agent` による spawn と、チームリードの Task による進捗追跡は **この変数なしでも動作します**。したがって変数は「Agent Teams を動かすためのスイッチ」ではなく「SendMessage ライブ協調レイヤを有効化する任意スイッチ」です。

## 整合性チェック

Agent Teams 共通ブロック・フォールバック文言・メタ情報フォーマット・テンプレート参照などの定型文は、複数ファイルに重複して存在する。この重複は許容したうえで、ファイル間のズレを機械的に検出するのが `scripts/check_consistency.py`（Python 3 標準ライブラリのみ・サードパーティ依存ゼロ）である。

> **「単一ファイル制約（include 機構なし）」という旧前提は撤回する（2026-09-16）。** 本リポジトリはすでに `templates/*-template.md` を実行時に相対パスで Read しており、include 機構は存在し稼働していた。分量の大きい定型文は `references/` 配下へ切り出し、**そのフェーズに入って初めて読み込む**構成（progressive disclosure）へ移行済みである。詳細は「[設計原則: 規約は必要なフェーズで読み込む](#設計原則-規約は必要なフェーズで読み込む)」を参照。

検出する9検査:

| 検査ID | 内容 |
|--------|------|
| `frontmatter` | 全6スキルの `model` 不在 / `disable-model-invocation: true` / `name`=ディレクトリ名 / `argument-hint`（既定は `<task_name> [--team]`。固有の引数を持つスキルのみ `ARGUMENT_HINT_OVERRIDES` で例外化する。現在の例外は **task-init**（URL 用）・**task-dev**（カンマ区切りの複数タスク用）・**task-verify**（`--manual` / `--run-only` 用）の3件） |
| `common-block` | 5スキル（task-init 除く）の Agent Teams 共通ブロックが task-dev を正準として sha256 一致するか |
| `fallback-msg` | フォールバック文言が CLAUDE.md と SKILL.md で一致するか（整形差を正規化して照合） |
| `meta-format` | 4テンプレートの `## メタ情報` 3行（3値表記含む）が一致するか |
| `env-json` | CLAUDE.md / README.md の `"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"` が一致するか |
| `template-ref` | 3スキル4テンプレートの参照が相対パスで実在し、ハードコード絶対パスの再混入がないか |
| `no-workflow` | Dynamic Workflows のランタイム固有 API 名（`export const meta` / `resumeFromRunId` / `scriptPath` / `agent(` / `parallel(` / `pipeline(` / `phase(`）が、全6 SKILL.md・4テンプレート・`CLAUDE.md`・`README.md` へ再混入していないか（走査対象には `references/*.md` と `docs/*.md` も含む。`CLAUDE.md` は `## 更新履歴` 以降を歴史的記録として除外）。**単語 `Workflow` そのものは禁止しない**（禁止すると「Dynamic Workflows を使用しない」という方針記述自体が検出され、検査が成立しないため）。禁止語彙を字面として列挙せざるをえない行（本検査自体の説明行）は、行内へ許可マーカー `&lt;!-- allow-workflow-mention --&gt;` を置くと除外される | <!-- allow-workflow-mention -->
| `reference-file` | 参照ファイル（`references/*.md`）が実在し、複数スキルへ同一内容で置かれるもの（`agent-teams.md` / `phase-tracking.md`）が正準と sha256 一致し、かつ**各 SKILL.md 本文から相対パスで参照されている**か（参照を失うと、本体から切り出した規約が永久に読まれなくなるため）。ハードコード絶対パスの再混入も検出する |
| `flow-checklist` | （走査対象に `references/*.md`・`docs/*.md` を含む）廃止済みの旧タスク管理ツール名・旧チーム生成 API 名・**旧検証実行スキルのスラッシュ起動名**（task-verify へ統合済み）・**旧レビュースキルと旧修正スキルのスラッシュ起動名**（task-dev へ統合済み）が SKILL.md・CLAUDE.md（更新履歴節を除く）・README.md・テンプレートへ再混入していないか、および全6スキルに Task 方式＋フォールバックの記述を伴う `### ステップ0` が存在するか |

実行方法:

```bash
python3 scripts/check_consistency.py        # 不一致のみ表示
python3 scripts/check_consistency.py -v     # 全検査の結果を表示
bash scripts/test/run_consistency_tests.sh  # 検査自体の回帰テスト（fixture 異常系・22ケース）
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
- **Minimal Commentary**: Generated code carries only comments that cannot be recovered by reading the code; comment density is capped at the surrounding file's existing level, and implementation intent is recorded in `dev-result.md` rather than defended in comments
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
