#!/usr/bin/env bash
# check_consistency.py の回帰テスト（FR-3 / design §11.2(a)）。
#
# 方針:
#   1. 正常リポジトリ（このリポジトリ自身）を --root で検査 → exit 0 を確認。
#   2. 7検査それぞれについて、リポジトリのコピーを作り該当箇所を1点だけ壊した fixture を
#      生成 → exit 1 かつ期待する検査ID（[check-id]）が出力に含まれることを確認。
#      検査によっては観点ごとに複数の fixture を持つ（例: frontmatter は model 再混入と
#      argument-hint 例外の差し戻し3件（task-dev / task-verify-run / task-verify）の計4件、
#      flow-checklist は廃止ツール名の再混入・ステップ0 節の欠落2件・ステップ0 からの
#      Task 記述欠落の4件、meta-format は3値表記崩し2件）。
#
# 依存: bash / python3 / 標準コマンドのみ（テストフレームワーク不使用）。
# CI 組込み可: このスクリプトの終了コードが 0 なら全テスト合格。

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
CHECKER="${REPO_ROOT}/scripts/check_consistency.py"

PASS_COUNT=0
FAIL_COUNT=0

# テンポラリ作業領域（終了時に必ず掃除）。
WORKDIR="$(mktemp -d "${TMPDIR:-/tmp}/cc-consistency-test.XXXXXX")"
cleanup() { rm -rf "${WORKDIR}"; }
trap cleanup EXIT

# 正常リポジトリのスナップショットを作る（.git は除外し git 解決を切る → --root 明示）。
SNAPSHOT="${WORKDIR}/snapshot"
mkdir -p "${SNAPSHOT}"
# 検査対象（skills / CLAUDE.md / README.md）のみコピー。
cp -R "${REPO_ROOT}/skills" "${SNAPSHOT}/skills"
cp "${REPO_ROOT}/CLAUDE.md" "${SNAPSHOT}/CLAUDE.md"
cp "${REPO_ROOT}/README.md" "${SNAPSHOT}/README.md"

# 期待 exit code と、FAIL 時に出力へ含まれているべき文字列を検証するヘルパ。
#   $1: テスト名
#   $2: 検査対象ルート
#   $3: 期待 exit code（0 or 1）
#   $4: （exit 1 の場合）出力に含まれているべき検査ID 文字列。例: "[frontmatter]"
run_case() {
  local name="$1" root="$2" expect_code="$3" expect_str="${4:-}"
  local out code
  set +e
  out="$(/usr/bin/python3 "${CHECKER}" --root "${root}" 2>/dev/null)"
  code=$?
  set -e

  if [[ "${code}" -ne "${expect_code}" ]]; then
    echo "✗ FAIL: ${name} — exit code ${code} (期待 ${expect_code})"
    echo "${out}" | sed 's/^/    /'
    FAIL_COUNT=$((FAIL_COUNT + 1))
    return
  fi

  if [[ -n "${expect_str}" ]]; then
    if ! grep -qF "${expect_str}" <<<"${out}"; then
      echo "✗ FAIL: ${name} — 出力に '${expect_str}' が含まれない"
      echo "${out}" | sed 's/^/    /'
      FAIL_COUNT=$((FAIL_COUNT + 1))
      return
    fi
  fi

  echo "✓ PASS: ${name}"
  PASS_COUNT=$((PASS_COUNT + 1))
}

# 壊した fixture を作る: SNAPSHOT を新しいディレクトリへ複製して返す。
make_fixture() {
  local dir="${WORKDIR}/fix-$1"
  rm -rf "${dir}"
  cp -R "${SNAPSHOT}" "${dir}"
  echo "${dir}"
}

echo "=== check_consistency.py 回帰テスト ==="
echo "リポジトリルート: ${REPO_ROOT}"
echo

# ---------------------------------------------------------------------------
# (0) 正常系: スナップショットは exit 0
# ---------------------------------------------------------------------------
run_case "正常リポジトリ → exit 0" "${SNAPSHOT}" 0

# ---------------------------------------------------------------------------
# (1) frontmatter: 削除したはずの model 指定を再混入させる
# ---------------------------------------------------------------------------
F="$(make_fixture frontmatter)"
/usr/bin/python3 - "${F}/skills/task-dev/SKILL.md" <<'PY'
import sys
p = sys.argv[1]
t = open(p, encoding="utf-8").read()
t = t.replace("disable-model-invocation: true", "model: opus\ndisable-model-invocation: true", 1)
open(p, "w", encoding="utf-8").write(t)
PY
run_case "frontmatter 異常（model 再混入）→ exit 1" "${F}" 1 "[frontmatter]"

# ---------------------------------------------------------------------------
# (2) common-block: task-review の共通ブロック内文言を1文字変える
# ---------------------------------------------------------------------------
F="$(make_fixture common-block)"
/usr/bin/python3 - "${F}/skills/task-review/SKILL.md" <<'PY'
import sys
p = sys.argv[1]
t = open(p, encoding="utf-8").read()
# 共通ブロック内に必ず存在する文言を改変（句点を変える）。
t = t.replace("今回は通常モードで実行します。", "今回は通常モードで実行します!", 1)
open(p, "w", encoding="utf-8").write(t)
PY
run_case "common-block 異常（task-review 改変）→ exit 1" "${F}" 1 "[common-block]"

# ---------------------------------------------------------------------------
# (3) fallback-msg: CLAUDE.md 側のフォールバック文言②を改変
#     （common-block を壊さないよう CLAUDE.md のみ変更）
# ---------------------------------------------------------------------------
F="$(make_fixture fallback-msg)"
/usr/bin/python3 - "${F}/CLAUDE.md" <<'PY'
import sys
p = sys.argv[1]
lines = open(p, encoding="utf-8").read().splitlines(keepends=True)
out = []
done = False
for ln in lines:
    s = ln.strip()
    if (not done and s.startswith("「⚠️")
            and "利用できないため" in s
            and "Agent Teams モードを起動できません" in s):
        ln = ln.replace("今回は通常モードで実行します。", "今回は通常モードで実行いたします。")
        done = True
    out.append(ln)
open(p, "w", encoding="utf-8").write("".join(out))
PY
run_case "fallback-msg 異常（CLAUDE.md 文言②改変）→ exit 1" "${F}" 1 "[fallback-msg]"

# ---------------------------------------------------------------------------
# (4) meta-format: テンプレートの Agent Teams 3値表記を崩す
# ---------------------------------------------------------------------------
F="$(make_fixture meta-format)"
/usr/bin/python3 - "${F}/skills/task-review/templates/review-template.md" <<'PY'
import sys
p = sys.argv[1]
t = open(p, encoding="utf-8").read()
t = t.replace(
    "- Agent Teams: [有効 / 無効（指定なし） / 無効（フォールバック）]",
    "- Agent Teams: [有効 / 無効]",
    1,
)
open(p, "w", encoding="utf-8").write(t)
PY
run_case "meta-format 異常（3値表記崩し）→ exit 1" "${F}" 1 "[meta-format]"

# ---------------------------------------------------------------------------
# (5) env-json: README.md の AGENT_TEAMS 設定行を削除
# ---------------------------------------------------------------------------
F="$(make_fixture env-json)"
/usr/bin/python3 - "${F}/README.md" <<'PY'
import sys
p = sys.argv[1]
lines = open(p, encoding="utf-8").read().splitlines(keepends=True)
out = [ln for ln in lines
       if '"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"' not in ln]
open(p, "w", encoding="utf-8").write("".join(out))
PY
run_case "env-json 異常（README.md から削除）→ exit 1" "${F}" 1 "[env-json]"

# ---------------------------------------------------------------------------
# (6) template-ref: ハードコード絶対パスを SKILL.md 本文へ再混入
# ---------------------------------------------------------------------------
F="$(make_fixture template-ref)"
/usr/bin/python3 - "${F}/skills/task-fix/SKILL.md" <<'PY'
import sys
p = sys.argv[1]
t = open(p, encoding="utf-8").read()
# 本文中の相対参照を、ハードコード絶対パスへ差し戻す（再混入を模す）。
t = t.replace(
    "templates/fix-result-template.md",
    "~/.claude/skills/task-fix/templates/fix-result-template.md",
    1,
)
open(p, "w", encoding="utf-8").write(t)
PY
run_case "template-ref 異常（絶対パス再混入）→ exit 1" "${F}" 1 "[template-ref]"

# ---------------------------------------------------------------------------
# (7) flow-checklist: 廃止済みツール名を task-review のステップ0 へ再混入
# ---------------------------------------------------------------------------
F="$(make_fixture flow-checklist-tool)"
/usr/bin/python3 - "${F}/skills/task-review/SKILL.md" <<'PY'
import sys
p = sys.argv[1]
t = open(p, encoding="utf-8").read()
ANCHOR = "> **禁止事項**: (a) Task 登録／チェックリスト宣言の省略、"
assert ANCHOR in t, "fixture 生成失敗: 禁止事項ブロックが見つかりません"
t = t.replace(
    ANCHOR,
    "> 旧来は `TodoWrite` で進捗を管理していました。\n>\n" + ANCHOR,
    1,
)
open(p, "w", encoding="utf-8").write(t)
PY
run_case "flow-checklist 異常（廃止ツール名の再混入）→ exit 1" "${F}" 1 "[flow-checklist]"

# ---------------------------------------------------------------------------
# (8) flow-checklist: ステップ0 見出しごと削除して構造確認を落とす
# ---------------------------------------------------------------------------
F="$(make_fixture flow-checklist-step0)"
/usr/bin/python3 - "${F}/skills/task-todo/SKILL.md" <<'PY'
import re
import sys
p = sys.argv[1]
lines = open(p, encoding="utf-8").read().splitlines(keepends=True)
start = None
out = []
for i, ln in enumerate(lines):
    if start is None and ln.startswith("### ステップ0"):
        start = i
        continue
    if start is not None and ln.startswith("### ") :
        start = None
    if start is None:
        out.append(ln)
open(p, "w", encoding="utf-8").write("".join(out))
PY
run_case "flow-checklist 異常（ステップ0 節の欠落）→ exit 1" "${F}" 1 "[flow-checklist]"

# ---------------------------------------------------------------------------
# (9) frontmatter: task-dev の argument-hint を旧値（既定値）へ差し戻す
#     ARGUMENT_HINT_OVERRIDES による例外が効いていること自体を検証する。
#     例外を消して既定値へフォールバックさせる実装ミスは、この fixture でのみ検出できる。
# ---------------------------------------------------------------------------
F="$(make_fixture frontmatter-argument-hint)"
/usr/bin/python3 - "${F}/skills/task-dev/SKILL.md" <<'PY'
import sys
p = sys.argv[1]
t = open(p, encoding="utf-8").read()
t = t.replace(
    'argument-hint: "<task_name>[,<task_name>...] [--team]"',
    'argument-hint: "<task_name> [--team]"',
    1,
)
open(p, "w", encoding="utf-8").write(t)
PY
run_case "frontmatter 異常（task-dev の argument-hint 差し戻し）→ exit 1" "${F}" 1 "[frontmatter]"

# ---------------------------------------------------------------------------
# (10) flow-checklist: ステップ0 節から Task 方式の記述だけを消す
#      STEP0_REQUIRED_TERMS への「Task」追加が効いていること自体を検証する。
#      置換は step0 節のスライス内だけに限定する（全文置換にすると共通ブロックまで壊れ、
#      common-block も同時に FAIL してテストの意図が曖昧になるため）。
# ---------------------------------------------------------------------------
F="$(make_fixture flow-checklist-step0-task)"
/usr/bin/python3 - "${F}/skills/task-design/SKILL.md" <<'PY'
import sys
p = sys.argv[1]
lines = open(p, encoding="utf-8").read().splitlines(keepends=True)

start = end = None
for i, ln in enumerate(lines):
    if start is None:
        if ln.startswith("### ステップ0"):
            start = i
        continue
    if ln.startswith("### ") or (ln.startswith("## ") and not ln.startswith("### ")):
        end = i
        break
assert start is not None, "fixture 生成失敗: ステップ0 節が見つかりません"
if end is None:
    end = len(lines)

section = "".join(lines[start:end])
assert "Task" in section, "fixture 生成失敗: ステップ0 節に Task 記述がありません"

for old, new in (
    ("select:TaskCreate,TaskUpdate,TaskList,TaskGet", "select:SendMessage"),
    ("TaskCreate", "登録"),
    ("TaskUpdate", "更新"),
    ("Task 方式", "宣言方式"),
    ("Task 一覧", "一覧"),
    ("Task 登録", "登録"),
    ("Task", "進捗管理"),
):
    section = section.replace(old, new)
assert "Task" not in section, "fixture 生成失敗: ステップ0 節に Task が残っています"

open(p, "w", encoding="utf-8").write("".join(lines[:start]) + section + "".join(lines[end:]))
PY
run_case "flow-checklist 異常（ステップ0 の Task 記述欠落）→ exit 1" "${F}" 1 "[flow-checklist]"

# ---------------------------------------------------------------------------
# (11) frontmatter: task-verify-run の argument-hint を既定値へ差し戻す
#      ARGUMENT_HINT_OVERRIDES へ追加した --team 非対応スキルの例外が効いていることを検証する。
# ---------------------------------------------------------------------------
F="$(make_fixture frontmatter-argument-hint-verify-run)"
/usr/bin/python3 - "${F}/skills/task-verify-run/SKILL.md" <<'PY'
import sys
p = sys.argv[1]
t = open(p, encoding="utf-8").read()
t = t.replace(
    'argument-hint: "<task_name>"',
    'argument-hint: "<task_name> [--team]"',
    1,
)
open(p, "w", encoding="utf-8").write(t)
PY
run_case "frontmatter 異常（task-verify-run の argument-hint 差し戻し）→ exit 1" "${F}" 1 "[frontmatter]"

# ---------------------------------------------------------------------------
# (12) frontmatter: task-verify の argument-hint を旧値（既定値）へ差し戻す
#      --manual を落として既定値と一致してしまう実装ミスは、この fixture でのみ検出できる。
# ---------------------------------------------------------------------------
F="$(make_fixture frontmatter-argument-hint-verify)"
/usr/bin/python3 - "${F}/skills/task-verify/SKILL.md" <<'PY'
import sys
p = sys.argv[1]
t = open(p, encoding="utf-8").read()
t = t.replace(
    'argument-hint: "<task_name> [--manual] [--team]"',
    'argument-hint: "<task_name> [--team]"',
    1,
)
open(p, "w", encoding="utf-8").write(t)
PY
run_case "frontmatter 異常（task-verify の argument-hint 差し戻し）→ exit 1" "${F}" 1 "[frontmatter]"

# ---------------------------------------------------------------------------
# (13) meta-format: 新テンプレート（verify-result-template.md）の3値表記を崩す
#      TEMPLATE_FILES の 5→6 が効いていること自体を検証する。
# ---------------------------------------------------------------------------
F="$(make_fixture meta-format-verify-result)"
/usr/bin/python3 - "${F}/skills/task-verify-run/templates/verify-result-template.md" <<'PY'
import sys
p = sys.argv[1]
t = open(p, encoding="utf-8").read()
t = t.replace(
    "- Agent Teams: [有効 / 無効（指定なし） / 無効（フォールバック）]",
    "- Agent Teams: [有効 / 無効]",
    1,
)
open(p, "w", encoding="utf-8").write(t)
PY
run_case "meta-format 異常（新テンプレートの3値表記崩し）→ exit 1" "${F}" 1 "[meta-format]"

# ---------------------------------------------------------------------------
# (14) flow-checklist: task-verify-run のステップ0 節を欠落させる
#      ALL_SKILLS の 9→10 が効いていること自体を検証する。ケース(8) と同じ手法で
#      step0 節をスライス削除する（他検査を巻き込まないため範囲を限定する）。
# ---------------------------------------------------------------------------
F="$(make_fixture flow-checklist-step0-verify-run)"
/usr/bin/python3 - "${F}/skills/task-verify-run/SKILL.md" <<'PY'
import sys
p = sys.argv[1]
lines = open(p, encoding="utf-8").read().splitlines(keepends=True)
start = None
out = []
for i, ln in enumerate(lines):
    if start is None and ln.startswith("### ステップ0"):
        start = i
        continue
    if start is not None and ln.startswith("### "):
        start = None
    if start is None:
        out.append(ln)
assert len(out) < len(lines), "fixture 生成失敗: ステップ0 節が見つかりません"
open(p, "w", encoding="utf-8").write("".join(out))
PY
run_case "flow-checklist 異常（task-verify-run のステップ0 節欠落）→ exit 1" "${F}" 1 "[flow-checklist]"

# ---------------------------------------------------------------------------
# 集計
# ---------------------------------------------------------------------------
echo
echo "————————————————————————————————"
echo "PASS: ${PASS_COUNT} / FAIL: ${FAIL_COUNT}"
if [[ "${FAIL_COUNT}" -ne 0 ]]; then
  echo "回帰テスト失敗"
  exit 1
fi
echo "全回帰テスト合格"
exit 0
