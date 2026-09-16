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
| `scripts/check_consistency.py` | ファイル間のズレの機械的検査（9検査） |
| `scripts/measure_weight.py` | 常時ロード／条件付きロードの分量計測 |

**規範を変更する場合は `CLAUDE.md` と該当 `SKILL.md` を更新すること。** `docs/` は根拠の保管場所であり、ここだけを直しても挙動は変わらない。

## Skill Architecture

The repository contains 6 interconnected skills that work together (only task-init is excluded from `--team` option support):

1. **task-design** - Analyzes existing systems and creates technical design, **then breaks it down into an implementation task list (`T-nnn`) with effort estimation in the same run**. Supports `--team` option.
2. **task-dev** - Creates (or reuses) a branch named after the task, executes implementation based on the design's implementation task list, **then automatically runs a review → fix → re-review closed loop (max 2 rounds; the 2nd round runs only when must-fix findings remain) inside the same invocation**, creates the development report, and finally commits (and, when enabled, pushes) the result. Review is **always delegated to a separate-context subagent** (regardless of `--team`) so that the agent which wrote the code never judges it from its own context; fixing is always single-agent. Review findings, the loop log, and the exit summary are **appended to `dev-result.md`** (no separate review/fix report files). Supports `--team` option (**review phase only** — 1 reviewer without it, 3 in parallel with it). **Also accepts a comma-separated list of task names** for bulk sequential implementation (delegating each task to an isolated subagent and committing per task); `--team` is ignored in that mode.
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

> **Task ツールの提供はモデル依存でゲートされる。** Claude Code 2.1.233 以降、しきい値以上のモデルでは進捗管理用の4ツールが既定で無効である。主経路を実際に通すには `~/.claude/settings.json` へ `"CLAUDE_CODE_ENABLE_TODO_TOOLS": "1"` が必要（README.md「インストール」の「共通の設定」と同一内容）。リモートフラグはロールアウト状況で変わりうるため、**ステップ0 の2方式分岐は今後も維持すること**。判定ロジックの実測結果・本原則の改訂履歴は [`docs/design-principles.md`](docs/design-principles.md) にある。なおこの env 変数は Agent Teams の `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` とは**無関係**である。

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
- **切り出す単位はフェーズ境界と一致させる。** 現行の4ファイルは、`agent-teams.md`（`--team` 指定時のみ）・`phase-tracking.md`（ステップ0 で必ず）・`task-dev` の `review-contract.md`（レビュー・修正フェーズ着手直前。複数タスクモードでは実装委譲の直前にも）・`task-dev` の `git-ops.md`（ステップG＝git 前提の確定の着手時。両モードで必ず）である。フェーズ境界と無関係な分割は、読み込み忘れを招くため行わない。
- **「読まれない参照」は規約の消失と同じである。** 本体から切り出した以上、参照が消えればその規約は永久に読まれない。`scripts/check_consistency.py` の `reference-file` 検査が、実在・スキル間の sha256 一致・**SKILL.md 本文からの参照の存在**の3点を機械的に担保する。
- **重複配置は維持する。** 参照ファイルはスキルごとに同一内容で置く（`skills/*` をそのままコピーする既存のインストール手順を変えないため、および skills ルートへ SKILL.md を持たないディレクトリを作らないため）。重複そのものは従来どおり許容し、ズレは検査が担保する。
- **逐語ブロックは要約して本体へ戻さない。** 委譲プロンプトの逐語ブロック（`review-contract.md` の 5-6-2）を記憶や要約から再構成すると、隔離規約と却下監査が「構造」から「指示」へ退化する。参照ファイルを読まずに委譲することを禁止事項とする。

## 設計原則: 識別子とエラー列挙は削らず、増やさない

**既存の安定識別子（`T-nnn` / `R-nnn` / `V-nnn` / `E-n` 等）とエラー表の行は、削除しない。** 代わりに**新規追加へ条件を課す**ことで、これ以上の増殖を防ぐ。

2026-09-16 に「成果物へ書かれるか他ファイルから参照される ID だけを残す」という整理を検討し、測定のうえ**却下した**。根拠:

- **ID の文字列コストは無視できる。** 全 SKILL.md・参照ファイル・テンプレートを通じてユニーク ID は約 300 件、うち1回しか出現しないものが約 84 件。すべて削っても節約は 1 KB に満たない（`python3 scripts/measure_weight.py -v` で再計測できる）。
- **エラー表は同一原則の実例ではない。** `task-dev` 5-17 の各行は「継続 / 中断 / 正常終了 / 条件付きコミット」という**異なる帰結**を持つ。fail-safe 原則1文へ畳むと、この帰結の differentiation が失われる。失われるのは「レビュー未実施のコードをコミットしてよいか」の判定そのものであり、危険側への丸めになる。
- **冗長な散文は実際にはほとんど無い。** 同一ファイル内で 35 字以上が重複している箇所は全スキル合計で 1 千字未満（仕様全体の 0.2% 程度）であり、その大半は**委譲プロンプトの逐語ブロック**（各プロンプトが単独で完結する必要があるため、意図的な重複）である。
- **欠番は監査可能性そのものである。** `E-14` / `E-29` / `E-30` / `E-34`、degrade 梯子の `D-1` などの欠番は、過去の成果物に残る記録の意味を保存している。再定義も詰め直しも行わない。

**したがって、分量の削減は「識別子や行を削る」ではなく「常時ロードを減らす」で行う**（「[設計原則: 規約は必要なフェーズで読み込む](#設計原則-規約は必要なフェーズで読み込む)」）。

**新規追加の条件（今後の増殖を防ぐ規律）**:

- **新しい ID を導入してよいのは、それが ① 成果物へ書き出されるか、② 定義した節の外から参照されるか、③ 閉じた語彙の要素である場合に限る。** 節内でしか使わない説明のための通し番号は付けない。
- **新しいエラー行を足してよいのは、既存のどの行とも「全体（継続 / 中断 / 正常終了）」または「記録先」が異なる場合に限る。** 同じ帰結の事象は既存行の事象欄へ書き足す。
- **新しい名前空間（`XX-n`）を作る前に、既存の名前空間へ収まらないかを確認する。** 現在 37 の名前空間があり、これ以上の増加は参照時の解決コストに見合わない。

## 設計原則: レビューは構造的に隔離する

同一実行内で実装とレビューを行うスキル（現時点では `task-dev`）は、**レビューを必ず別コンテキストのサブエージェントへ委譲する**ことを設計原則とする。実装時に「この設計で要件を満たす」と結論した主体が、レビュー時に「満たしていない」と言うのは直前の自分の結論の否認であり、**過少指摘（危険側）が構造的に優勢**になる。被害は「要件未充足・脆弱性を含んだ実装が、レビュー済みという記録つきでコミットされること」である。

この隔離は「実装時の判断を思い出さないでください」という**指示では成立しない**。委譲プロンプトへ埋め込んでよい項目を限定列挙し、**実装担当の自己申告である `dev-result.md` を渡さない**ことで、隔離を指示ではなく**構造**にする。隔離の実現手段は **`name` を付けない同期 `Agent` 委譲**（`run_in_background: false`。成果を戻り値で受領する）であり、成果が戻り値で返らない経路（`name` 付きのバックグラウンド spawn）を委譲に用いない。レビュー対象は「変更ファイルのパスの配列」と、`git diff --unified=0` から機械的に得られる**変更行範囲**（観点④⑤の重点範囲）としてのみ渡し、**差分本文**・実装意図・変更理由・前周の却下理由は渡さない。同型の対処は `task-verify` のスキップ判定（SK-1〜SK-3）で先行して採っている。

- **委譲は `--team` の有無と独立である。** `--team` は「並列体数と分割粒度のプロファイル選択」にすぎず、委譲そのものは常に必須である。自己レビューが許されるのは degrade 梯子の最終段のみで、その場合は必ず告知し成果物へ記録する。
- **「委譲の不成立」も終了保証の対象に含める。** 隔離した先から成果が返らなければ、レビューは実施されていない。`findings` が空であることを「指摘0件」と解釈してよいのは**全担当が成果を返したときだけ**であり、1体でも `null` なら未確認範囲として記録し、全滅なら終了区分を `レビュー未実施（委譲不成立）` とする。**「何も検査されなかった」を「問題なし」と書かないこと**が、この原則の実効性を決める。
- **外部の証拠源を持たないループには終了保証を機械的に置く。** 同一入力に対する同一モデルの再判断には新情報が入らないため、指摘へ安定識別子を採番し、散文を除いた署名で停滞を判定し、ループ上限を設ける（`task-dev` は**最大2周**で、2周目は修正必須が残った場合にのみ回す）。
- **ツール層の型保証を失う経路では、検証をスキル本体が持つ。** 戻り値は「応答末尾の ```json フェンス」を契約とし、スキル本体が必須キー・語彙・型を検証する（`RV-1`〜`RV-6`）。語彙外の値は**危険側へ倒さない向き**へ丸め（例: 語彙外の `priority` は `高`）、丸めた事実を成果物へ記録する。形式逸脱は1回だけ再委譲し、なお不合格なら「未検査」として扱う（`E-36`）。
- **収束は品質を意味しない。** 指摘が0件になったことを品質の証明として扱わない。本当の合否判定は動的検証（`task-verify`）が持つ。
- **同一モデルの盲点は隔離しても共有される。** 本原則が防げるのは一貫性バイアスのみであり、モデル固有の知識欠落は防げない。これは設計上の受容事項として利用者へも案内する。

## 設計原則: git 操作は設定で明示された範囲だけ行う

`task-dev` は**タスク名からブランチを作成し、コミットし、設定と実行環境に応じて push する**。これは「本スキル群は遠隔操作とブランチ操作を行わない」という従来の禁止を、**無効化ではなく条件付き許可へ置き換える**変更である（論証・実測・改訂履歴は [`docs/design-principles.md`](docs/design-principles.md)）。規約の逐語本文は `skills/task-dev/references/git-ops.md`（`GB-1`〜`GB-23`）が持ち、**ステップG の着手時にのみ読み込む**。

- **ブランチ作成は `task-dev` に置き、`task-init` / `task-design` には置かない。** `task-design` は工数見積もりを兼ねており、**見積もりだけ提出して実装に着手しないケースが常態的にある**。ブランチは「実装に着手した」という事実に結び付けるべきであり、その事実が確定するのは `task-dev` の実行時である。結果として要件定義・設計の成果物は起点ブランチ側に残り、実装のみが `feature/<task>` に載る。**この分裂は許容する**。
- **制御はプロジェクト単位の設定ファイル2層（`.claude/task-skills.local.json` → `.claude/task-skills.json`）だけで行い、利用者向けの環境変数は設けない。** マージはキー単位。**設定に明示されたキーは、実行環境の判別よりも常に優先される**（判別結果が設定を上書きすることは一切ない）。スキルは設定ファイルを**書き換えない**。
- **`push` の既定値だけは実行環境の判別から決め、判別は3値（クラウド / ローカル / 判別不能）とする。2値へ丸めない。** 判別に使う環境変数は公開仕様ではないため、**判別不能なら push せず、未 push のコミットが残ることを警告する**。将来その信号が廃止されても「黙って成果が消える」ではなく「警告が出て手動 push を促される」へ劣化する。**この劣化の方向性を壊す変更を加えないこと。**
- **破壊的・不可逆な操作の禁止は維持する。** force push（`--force` / `--force-with-lease`）・`git reset` / `git checkout -- <path>` / `git restore` / `git clean`・`git rebase` / `git merge` / `git tag` / `git config`・履歴の書き換え・**決定した1ブランチ以外への push** は引き続き禁止である。既存ブランチを再利用する際に**起点ブランチを自動マージしない**のも同じ理由（衝突解決という重い判断を暗黙に持ち込まないため）。
- **サブエージェントの git 禁止事項は一切緩めない。** ブランチ作成・コミット・push は**すべてメイン会話の責務**であり、実装・レビュー・修正の委譲先は従来どおり git の状態を変更しない。
- **コミットしてよい3経路（`C-11a` / `C-11b-1` / `C-11b-2`）は両モード共通である。** 単一タスクモードがコミットするようになっても、**未解消の修正必須を残したままコミットしない**という原則は変わらない。「レビュー済みという記録つきで欠陥がコミットされること」を防ぐのが本スキルの目的そのものであるためである。
- **複数タスクモードでは自動ブランチ作成を行わない**（`task1,task2,task3` は1つのブランチ名に対応しない）。警告のうえ起動時のブランチへタスクごとにコミットする。`commit` / `push` の設定は有効である。
- **黙って分岐しない。** 実際に使うブランチ名・起点・コミットと push の有無・その判断根拠を、**作業開始前に必ず表示する**。`CLAUDE_CODE_BASE_REF`（セッションの指定ブランチ）が取得でき、作成するブランチと異なる場合は、推測ではなくその値を明示して報告する。

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

`task-dev` additionally reads a **project-level settings file** (never per task, never created or rewritten by the skills):

```
.claude/task-skills.local.json   # 個人の環境ごとの設定（最優先。.gitignore への登録を推奨）
.claude/task-skills.json         # コミットして共有する、チーム共通の設定
```

Keys are `branch.create` / `branch.prefix` / `commit` / `push`, merged **key by key** with the local layer winning. `push` alone falls back to a 3-valued execution-environment detection when no layer declares it. 規約の正本は `skills/task-dev/references/git-ops.md`（`GB-1`〜`GB-23`）である。

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

> **フロー強制（全スキル共通）**: 6スキルすべてが「手順」冒頭の **ステップ0** で `references/phase-tracking.md`（共通の判定手順）を読み込んだうえで、自スキルの全フェーズを Task として登録し、着手時に `in_progress`・完了時に `completed` へ遷移させることで、スキップ・前倒し・取りこぼしを構造的に防ぐ（Task ツールが利用できない場合はチェックリスト宣言へフォールバックする。「[設計原則: フローは Task ツールで明示的に追跡する](#設計原則-フローは-task-ツールで明示的に追跡する)」の具体化）。登録は省略不可（成果物の必須要素）。**task-dev** は単一タスクモードで14フェーズ（`--team` 非依存）、複数タスクモードで8フェーズを登録し、加えて実行時に design.md の実装タスク一覧（`T-nnn`。todo.md が存在する場合はその項目も）を Task として動的登録して1件ずつ着手・完了を明示し、さらにレビューパス1周ごとに `[review pass i/3]`（修正必須があれば `[fix pass i/3]` も）を動的追加する（パス内の個別 `R-nnn` は Task 化しない）。**task-init** は URL 有無の分岐判定後に確定する系列のフェーズのみを登録する特例とする。**task-verify** は既定モードで18フェーズ（`--manual` は7、`--run-only` は12）を登録したうえで、確認パス1周ごとに Task を動的追加する（各パス内の個別項目は Task 化しない）。

各スキルの引数・分岐・終了条件・記録要件の詳細は **[`docs/skill-behaviors.md`](docs/skill-behaviors.md)** にある（正本は各 `skills/<skill>/SKILL.md`）。

| スキル | 起動 | 要点 |
|---|---|---|
| `task-init` | `/task-init {task_name} [URL]` | タスクディレクトリと init.md / req.md（空テンプレート）を作成。URL 指定時は本文と全コメントを逐語転記し添付を `files/` へ保存する。取得手段ゼロなら**ディレクトリごと作らずエラー終了** |
| `task-req` | `/task-req {task_name} [--team]` | init.md から req.md を起こす。末尾の「要確認事項」は**回答で設計・実装の分岐が変わる問いだけ**に絞る（包含が先・除外語彙 `X-1`〜`X-6`・判定不能は残す）。0件なら節ごと出力しない |
| `task-req-update` | `/task-req-update {task_name} [--team]` | 「要確認事項」への回答を本文へ反映し確定版へ整理。未解決項目は残し、全解決で節を削除。冪等（回答 → 再実行のループ） |
| `task-design` | `/task-design {task_name} [--team]` | §1〜§11 の設計 ＋ §12 実装タスク一覧（`T-nnn`）＋ §13 工数見積もりを1回で完結。**設計確定線**より上は見積もり中 read-only。行数 ÷ 実装時間 < 30 行/h の見積もりは差し戻し（上限2周） |
| `task-dev` | `/task-dev {task_name}[,...] [--team]` | **ステップG** で設定を解決し `feature/<task_name>` を作成・切替（既定）。`T-nnn` 順に実装し、続けて**レビュー → 修正 → 再レビューを最大2周**（レビューは常に別コンテキストへ委譲）。**権限の切替線**の手前と奥で書き込み権限が変わる。**ステップC** でコミットし、`push` が真なら `git push -u origin <branch>`（force push は行わない）。カンマ区切りで複数タスクを逐次実装しタスクごとにコミット（この場合ブランチは作成しない） |
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

## 分量の計測

「重厚すぎる」という議論を印象ではなく数値で行うために、`scripts/measure_weight.py`（Python 3 標準ライブラリのみ）を置く。**スキル1回の実行で常時ロードされる行数**（SKILL.md 本体）と、**該当フェーズに入って初めて読み込まれる行数**（`references/` / `templates/`）を分けて表示する。合否判定は持たない（常に exit 0）。

```bash
python3 scripts/measure_weight.py        # スキル別の内訳
python3 scripts/measure_weight.py -v     # 識別子・重複の統計も表示
```

スキルへ記述を追加する際は、**それが「常時」列に乗るのか「条件付き」列に乗るのか**を意識すること。特定のオプションやフェーズでしか使わない規約は `references/` へ置く。

## Installation Method

導入方法は2通りあり、**スキル定義はどちらでも無改変で動作しなければならない**。

1. **プラグイン**（推奨。クラウドセッション対応）: リポジトリ直下がマーケットプレイス `tombolo-jp` 兼プラグイン `cc-task-skills` を兼ねる。
2. **個人スキルへコピー**（従来どおり）:
   ```bash
   cp -r cc-task-skills/skills/* ~/.claude/skills/
   ```

> **開発・コントリビュート時**: スキル定義やドキュメントを編集する場合は、前述「整合性チェック」のローカルフックを有効化しておくと定型文のズレを早期に検出できる。
> ```bash
> git config core.hooksPath scripts/hooks
> ```

### プラグイン配布構成: 今後の改修で守る点

`.claude-plugin/plugin.json` と `.claude-plugin/marketplace.json` は `scripts/check_consistency.py` の検査対象外である（9検査はいずれもハードコードされたファイル一覧のみを読み、ディレクトリ走査もグロブも行わない）。**機械的な担保が無いため、以下は規範として守ること。**

- **`plugin.json` に `skills` フィールドを書かない。** `<プラグインルート>/skills` の自動検出は「`skills` が宣言されていないこと」を条件に行われる。宣言すると自動検出が無効化され、明示したパスだけが対象になる。`commands` / `agents` / `hooks` も同様。
- **両 JSON のスキーマは strict であり、未定義キーの追加は検証エラーになる。** `plugin.json` で使えるメタ情報は `name`（必須）/ `version` / `description` / `author` / `homepage` / `repository` / `license` / `keywords` に限られる。`author` と `owner` は文字列ではなく `{name, email?, url?}` のオブジェクトである。
- **`version` は両ファイルに書かない。** 更新はコミット SHA で判定させる方針のため、`claude plugin validate` が出す version 未指定の警告1件は**意図的に許容する**。この警告を消す目的で version を追加しないこと。
- **スキル本文にインストール先依存の絶対パスを書かない。** 参照ファイル・テンプレートの解決は、ハーネスがスキル本文の先頭へ自動付加する `Base directory for this skill: <スキル自身のディレクトリの絶対パス>` からの相対解決を使う。この行は**個人スキル経路とプラグイン経路の両方で付加される**ため、現行の記述がそのまま両対応になっている。
- **`${CLAUDE_PLUGIN_ROOT}` を使わない。** 展開されるのはプラグイン経路のみで、個人スキル経路では未展開の文字列がそのまま残る。なお `${CLAUDE_SKILL_DIR}` という変数は**存在しない**（代替にならない）。
- **frontmatter の `name` はディレクトリ名と一致させ続ける**（`frontmatter` 検査が強制）。プラグイン経路のコマンド正式名は `cc-task-skills:<ディレクトリ名>` だが、短縮形 `/<name>` での起動はこの一致によって成立している。一致が崩れると短縮形が死に、スキル本文が案内する `/task-design` 等のコマンド名がすべて不正になる。
- **ルートの `CLAUDE.md` は利用者のセッションへは読み込まれない**（`claude plugin validate` が明示的に警告する）。本ファイルは本リポジトリを編集するとき専用であり、利用者へ届けたい規範はスキル本文か `references/` に置くこと。
- **スキルを追加・削除した場合は `marketplace.json` の説明文と README のスキル一覧も更新する。**

## Language Support

The skills support Japanese language for requirements definition and design documentation while maintaining English compatibility for technical implementation.

## Development Philosophy

- **Staged Development**: Sequential progression through requirements → design (with task breakdown and estimation) → implementation (with the review → fix → re-review loop) → verification
- **Quality Focus**: Emphasizes code quality, maintainability, and integration with existing systems
- **Minimal Commentary**: Generated code carries only comments that cannot be recovered by reading the code; comment density is capped at the surrounding file's existing level, and implementation intent is recorded in `dev-result.md` rather than defended in comments
- **Structural Isolation of Review**: The agent that wrote the code never judges it from its own context; review is delegated to a separate context and the implementer's own account is not passed along
- **Task-named Branches**: implementation lands on `feature/<task_name>`, created at the moment implementation actually starts (`task-dev`), never earlier; commits and pushes are controlled by a project-level settings file, and the detection that decides the `push` default degrades toward *warning the user*, never toward a silent push or a silent loss
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
