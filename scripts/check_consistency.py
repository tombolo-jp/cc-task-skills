#!/usr/bin/env python3
"""cc-task-skills 横断整合性チェックスクリプト（FR-3）。

各 SKILL.md / CLAUDE.md / README.md / テンプレート間で重複記載される定型文
（Agent Teams 共通ブロック・フォールバック文言・メタ情報3行など）の
ズレを機械的に検出する。include 機構が無いため定型文の重複を許容し、ズレをこのスクリプトで担保する。

依存は Python 3 標準ライブラリのみ（/usr/bin/python3 = 3.9.6 で動作）。サードパーティ import なし。

終了コード:
  0 = 全検査 PASS（整合）
  1 = 1件以上の不一致を検出
  2 = スクリプト自体の実行エラー（対象ファイル欠落・パース不能等）
"""

import argparse
import difflib
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# 定数定義
# ---------------------------------------------------------------------------

# Agent Teams 対応スキル（task-init を除く8スキル）。common-block 検査対象。
TEAM_SKILLS = [
    "task-dev",
    "task-req",
    "task-req-update",
    "task-design",
    "task-todo",
    "task-review",
    "task-fix",
    "task-verify",
]

# common-block 検査の正準（基準）スキル（design D-7）。
CANONICAL_SKILL = "task-dev"

# 全8スキル（frontmatter 検査対象）。
ALL_SKILLS = ["task-init"] + TEAM_SKILLS

# テンプレートを持つスキルと、そのテンプレートファイル名（meta-format / template-ref 検査対象）。
TEMPLATE_FILES = {
    "task-dev": "dev-result-template.md",
    "task-fix": "fix-result-template.md",
    "task-review": "review-template.md",
    "task-todo": "todo-template.md",
    "task-verify": "verify-template.md",
}

# frontmatter の argument-hint 期待値（init は URL 用で別ルール、他7は --team 用）。
ARGUMENT_HINT_INIT = "<task_name> [<URL>]"
ARGUMENT_HINT_TEAM = "<task_name> [--team]"

# メタ情報 Agent Teams 行の3値表記（厳密一致）。
META_AGENT_TEAMS_LINE = "- Agent Teams: [有効 / 無効（指定なし） / 無効（フォールバック）]"
META_MODEL_LINE = "- 実行モデル: [モデル名]"
META_DATETIME_LINE = "- 実行日時: [日時]"

# env-json で両ファイルに存在すべき行（前後空白は無視して比較）。
ENV_JSON_LINE = '"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"'


# ---------------------------------------------------------------------------
# CheckResult データ構造
# ---------------------------------------------------------------------------

class CheckResult:
    """1検査の結果。passed=True なら整合、False なら不一致。

    detail には不一致の原因（ファイル・行番号・差分）を人間可読の文字列で格納する。
    """

    def __init__(self, check_id, passed, summary, detail=""):
        self.check_id = check_id
        self.passed = passed
        self.summary = summary
        self.detail = detail

    def to_dict(self):
        return {
            "check_id": self.check_id,
            "passed": self.passed,
            "summary": self.summary,
            "detail": self.detail,
        }


class CheckError(Exception):
    """対象ファイル欠落・パース不能など、検査続行不能なエラー（終了コード2）。"""


# ---------------------------------------------------------------------------
# ルート解決・ファイル収集
# ---------------------------------------------------------------------------

def resolve_root(explicit_root=None):
    """リポジトリルートを解決する。

    優先順:
      1. --root で明示されたパス
      2. git rev-parse --show-toplevel
      3. このスクリプトの親の親（scripts/check_consistency.py → リポジトリルート）
    """
    if explicit_root:
        root = Path(explicit_root).resolve()
        if not root.is_dir():
            raise CheckError(f"--root で指定されたディレクトリが存在しません: {root}")
        return root

    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).resolve().parent),
        )
        if out.returncode == 0:
            candidate = Path(out.stdout.strip())
            if candidate.is_dir():
                return candidate.resolve()
    except (OSError, subprocess.SubprocessError):
        pass

    # __file__ の親の親（scripts/ の親）
    return Path(__file__).resolve().parent.parent


def read_text(path):
    """テキストファイルを読む。欠落・読込不能は CheckError。"""
    if not path.is_file():
        raise CheckError(f"対象ファイルが存在しません: {path}")
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise CheckError(f"ファイル読込に失敗しました: {path} ({exc})")


def rel(root, path):
    """ルートからの相対パス文字列（レポート表示用）。"""
    try:
        return str(Path(path).resolve().relative_to(root))
    except ValueError:
        return str(path)


class Repo:
    """検査対象ファイルを収集・キャッシュするコンテナ。"""

    def __init__(self, root):
        self.root = root
        self._cache = {}

    def skill_md(self, skill):
        return self.root / "skills" / skill / "SKILL.md"

    def template_md(self, skill):
        return self.root / "skills" / skill / "templates" / TEMPLATE_FILES[skill]

    @property
    def claude_md(self):
        return self.root / "CLAUDE.md"

    @property
    def readme_md(self):
        return self.root / "README.md"

    def text(self, path):
        key = str(path)
        if key not in self._cache:
            self._cache[key] = read_text(path)
        return self._cache[key]


# ---------------------------------------------------------------------------
# 共通ユーティリティ
# ---------------------------------------------------------------------------

def parse_frontmatter(text):
    """SKILL.md 先頭の `---...---` を簡易自前パース（PyYAML 非使用）。

    `key: value` 形式のみ対応。値の前後クォートは保持したまま返す（呼び出し側で扱う）。
    frontmatter が無ければ None。
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    fm = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return fm
        m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if m:
            fm[m.group(1)] = m.group(2).strip()
    # 終端 --- が無い場合は frontmatter として不正
    return None


def strip_quotes(value):
    """前後のシングル/ダブルクォートを1組だけ除去する。"""
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def extract_common_block(text):
    """SKILL.md から Agent Teams 共通ブロックを抽出する。

    範囲: 「### 重要: `--team`」で始まる行 〜 「#### 役割分担」の直前行。
    行番号非依存（マーカー検出）。見つからなければ (None, None, None)。
    戻り値: (block_text, start_lineno_1based, end_lineno_exclusive_1based)
    """
    lines = text.splitlines(keepends=True)
    start = end = None
    for i, line in enumerate(lines):
        if start is None and re.match(r"^### 重要: `--team`", line):
            start = i
        if start is not None and line.startswith("#### 役割分担"):
            end = i
            break
    if start is None or end is None:
        return None, None, None
    block = "".join(lines[start:end])
    return block, start + 1, end + 1


def normalize_msg(s):
    """フォールバック文言の整形差を吸収する正規化。

    - 先頭の `> `（blockquote マーカー）を除去
    - 前後の鉤括弧「」を除去
    - 全角スペースを半角へ統一
    - 前後空白を strip
    """
    s = s.strip()
    if s.startswith("> "):
        s = s[2:]
    elif s.startswith(">"):
        s = s[1:]
    s = s.strip()
    if s.startswith("「"):
        s = s[1:]
    if s.endswith("」"):
        s = s[:-1]
    s = s.replace("　", " ")
    return s.strip()


def make_diff(expected, actual, expected_label, actual_label):
    """unified_diff の文字列を返す（行末改行を整える）。"""
    diff = difflib.unified_diff(
        expected.splitlines(keepends=True),
        actual.splitlines(keepends=True),
        fromfile=expected_label,
        tofile=actual_label,
        lineterm="",
    )
    return "\n".join(line.rstrip("\n") for line in diff)


# ---------------------------------------------------------------------------
# 検査関数群（§7.2 の6検査）
# ---------------------------------------------------------------------------

def check_frontmatter(repo):
    """[frontmatter] 全8スキルの model / disable-model-invocation / name / argument-hint 規約準拠。"""
    check_id = "frontmatter"
    problems = []
    for skill in ALL_SKILLS:
        path = repo.skill_md(skill)
        text = repo.text(path)
        fm = parse_frontmatter(text)
        loc = rel(repo.root, path)
        if fm is None:
            problems.append(f"{loc}: frontmatter（---...---）が見つからない、または不正です")
            continue

        # model: opus（全8必須）
        if fm.get("model") != "opus":
            problems.append(
                f"{loc}: model は 'opus' であるべきですが '{fm.get('model')}' です"
            )

        # disable-model-invocation: true（全8必須）
        if fm.get("disable-model-invocation") != "true":
            problems.append(
                f"{loc}: disable-model-invocation は 'true' であるべきですが "
                f"'{fm.get('disable-model-invocation')}' です"
            )

        # name=ディレクトリ名一致
        if fm.get("name") != skill:
            problems.append(
                f"{loc}: name はディレクトリ名 '{skill}' と一致すべきですが '{fm.get('name')}' です"
            )

        # argument-hint（init は別ルール）
        hint = strip_quotes(fm.get("argument-hint", ""))
        expected_hint = ARGUMENT_HINT_INIT if skill == "task-init" else ARGUMENT_HINT_TEAM
        if hint != expected_hint:
            problems.append(
                f"{loc}: argument-hint は '{expected_hint}' であるべきですが '{hint}' です"
            )

    if problems:
        return CheckResult(
            check_id, False,
            "frontmatter 規約に不一致があります",
            "\n".join("    " + p for p in problems),
        )
    return CheckResult(check_id, True, "全9スキルの model/disable-model-invocation/name/argument-hint 規約準拠")


def check_common_block(repo):
    """[common-block] Agent Teams 共通ブロックが task-dev 基準とバイト一致するか。"""
    check_id = "common-block"
    canonical_path = repo.skill_md(CANONICAL_SKILL)
    canonical_text = repo.text(canonical_path)
    canonical_block, c_start, c_end = extract_common_block(canonical_text)
    if canonical_block is None:
        return CheckResult(
            check_id, False,
            f"正準スキル {CANONICAL_SKILL} で共通ブロックを抽出できません",
            f"    マーカー（### 重要: `--team` / #### 役割分担）が見つかりません: "
            f"{rel(repo.root, canonical_path)}",
        )
    canonical_hash = hashlib.sha256(canonical_block.encode("utf-8")).hexdigest()
    canonical_label = f"{rel(repo.root, canonical_path)} (lines {c_start}-{c_end - 1})"

    problems = []
    for skill in TEAM_SKILLS:
        if skill == CANONICAL_SKILL:
            continue
        path = repo.skill_md(skill)
        text = repo.text(path)
        block, start, end = extract_common_block(text)
        loc = rel(repo.root, path)
        if block is None:
            problems.append(
                f"{loc}: 共通ブロックを抽出できません（マーカー欠落）"
            )
            continue
        if hashlib.sha256(block.encode("utf-8")).hexdigest() != canonical_hash:
            diff = make_diff(
                canonical_block, block,
                canonical_label,
                f"{loc} (lines {start}-{end - 1})",
            )
            problems.append(
                f"{loc} (lines {start}-{end - 1}) が基準と一致しません\n{diff}"
            )

    if problems:
        return CheckResult(
            check_id, False,
            f"Agent Teams 共通ブロックが基準（{CANONICAL_SKILL}）と一致しません",
            f"    基準: {canonical_label}\n" + "\n".join("    " + p for p in problems),
        )
    return CheckResult(
        check_id, True,
        f"8スキルの Agent Teams 共通ブロックが {CANONICAL_SKILL} 基準と一致（sha256: {canonical_hash[:12]}…）",
    )


def _extract_blockquote_messages(text):
    """SKILL.md から `> ⚠️` で始まる blockquote 文言を正規化して列挙する。"""
    msgs = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("> ⚠️") or stripped.startswith(">⚠️"):
            msgs.append(normalize_msg(stripped))
    return msgs


def check_fallback_msg(repo):
    """[fallback-msg] フォールバック文言②が CLAUDE.md と SKILL.md で整形差を除いて一致するか。

    CLAUDE.md は鉤括弧地の文、SKILL.md は `> ⚠️` blockquote。normalize_msg で整形差を吸収。
    env 変数ハードゲート撤廃に伴い文言①（環境変数設定依頼）は廃止され、照合は文言②
    （チームメイト起動不可）のみとする。task-init の URL 用文言は別物なので照合対象から除外。
    """
    check_id = "fallback-msg"
    claude_text = repo.text(repo.claude_md)

    # CLAUDE.md の鉤括弧地の文（「⚠️ ... 今回は通常モードで実行します。」）を抽出
    claude_msgs = []
    for line in claude_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("「⚠️") and stripped.endswith("」"):
            claude_msgs.append(normalize_msg(stripped))

    # 文言②（チームメイト起動不可）を特定
    msg_tool = None
    for m in claude_msgs:
        if "利用できないため" in m and "Agent Teams モードを起動できません" in m:
            msg_tool = m

    problems = []
    if msg_tool is None:
        problems.append("CLAUDE.md にフォールバック文言②（チームメイト起動不可）が見つかりません")
    else:
        # 各 Agent Teams 対応 SKILL.md の blockquote と照合
        for skill in TEAM_SKILLS:
            path = repo.skill_md(skill)
            text = repo.text(path)
            loc = rel(repo.root, path)
            skill_msgs = _extract_blockquote_messages(text)
            if msg_tool not in skill_msgs:
                problems.append(
                    f"{loc}: フォールバック文言②が CLAUDE.md と一致しません（または欠落）"
                )

    if problems:
        return CheckResult(
            check_id, False,
            "フォールバック文言が CLAUDE.md と SKILL.md で一致しません",
            "\n".join("    " + p for p in problems),
        )
    return CheckResult(
        check_id, True,
        "フォールバック文言②が CLAUDE.md と8スキル SKILL.md で一致（整形差正規化後）",
    )


def check_meta_format(repo):
    """[meta-format] 5テンプレートの `## メタ情報` 直後3行が一致し、3値表記が厳密一致か。"""
    check_id = "meta-format"
    expected = [META_MODEL_LINE, META_DATETIME_LINE, META_AGENT_TEAMS_LINE]
    problems = []

    for skill in TEMPLATE_FILES:
        path = repo.template_md(skill)
        text = repo.text(path)
        loc = rel(repo.root, path)
        lines = text.splitlines()
        idx = None
        for i, line in enumerate(lines):
            if line.strip() == "## メタ情報":
                idx = i
                break
        if idx is None:
            problems.append(f"{loc}: `## メタ情報` セクションが見つかりません")
            continue
        # 直後3行を抽出（空行はスキップしない＝直後の3行をそのまま）
        following = [line.rstrip() for line in lines[idx + 1: idx + 4]]
        if following != expected:
            diff = make_diff(
                "\n".join(expected) + "\n",
                "\n".join(following) + "\n",
                "期待 (メタ情報3行)",
                loc,
            )
            problems.append(f"{loc}: メタ情報3行が期待と一致しません\n{diff}")

    if problems:
        return CheckResult(
            check_id, False,
            "テンプレートのメタ情報3行に不一致があります",
            "\n".join("    " + p for p in problems),
        )
    return CheckResult(
        check_id, True,
        "5テンプレートの `## メタ情報` 3行（3値表記含む）が一致",
    )


def check_env_json(repo):
    """[env-json] CLAUDE.md と README.md に `"...AGENT_TEAMS": "1"` 行が両方存在し同一か。"""
    check_id = "env-json"
    problems = []
    found = {}
    for label, path in (("CLAUDE.md", repo.claude_md), ("README.md", repo.readme_md)):
        text = repo.text(path)
        matches = [line.strip() for line in text.splitlines() if ENV_JSON_LINE in line.strip()]
        if not matches:
            problems.append(f"{label}: '{ENV_JSON_LINE}' を含む行が見つかりません")
        else:
            found[label] = matches[0].strip()

    if len(found) == 2 and found["CLAUDE.md"] != found["README.md"]:
        problems.append(
            "CLAUDE.md と README.md の AGENT_TEAMS 設定行が一致しません\n"
            f"      CLAUDE.md: {found['CLAUDE.md']}\n"
            f"      README.md: {found['README.md']}"
        )

    if problems:
        return CheckResult(
            check_id, False,
            "AGENT_TEAMS 環境変数の JSON 設定行に不一致があります",
            "\n".join("    " + p for p in problems),
        )
    return CheckResult(
        check_id, True,
        'CLAUDE.md / README.md の "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1" が一致',
    )


def check_template_ref(repo):
    """[template-ref] テンプレート参照の実在確認＋ハードコード絶対パス再混入検出。

    - 5 SKILL.md 本文の `templates/X-template.md` 参照を抽出し、当該スキルの templates/ 配下に
      実ファイルが存在するか pathlib で確認。
    - 併せて `~/.claude/skills/.../templates/` のハードコード絶対パス再混入を検出。
      ただし README/CLAUDE のインストールコマンド `cp -r ... ~/.claude/skills/` 文脈は除外。
    """
    check_id = "template-ref"
    problems = []
    ref_re = re.compile(r"templates/([A-Za-z0-9_-]+-template\.md)")
    # ハードコード絶対パス: ~/.claude/skills/.../templates/ を含む参照
    hardcode_re = re.compile(r"~/\.claude/skills/[^\s`]*templates/")

    for skill in TEMPLATE_FILES:
        path = repo.skill_md(skill)
        text = repo.text(path)
        loc = rel(repo.root, path)

        refs = set(ref_re.findall(text))
        if not refs:
            problems.append(f"{loc}: templates/X-template.md 形式の参照が見つかりません")
        for ref in refs:
            target = repo.root / "skills" / skill / "templates" / ref
            if not target.is_file():
                problems.append(
                    f"{loc}: 参照 'templates/{ref}' に対応する実ファイルが存在しません "
                    f"（期待: {rel(repo.root, target)}）"
                )

        # ハードコード絶対パスの再混入検出（SKILL.md 本文）
        for lineno, line in enumerate(text.splitlines(), 1):
            if hardcode_re.search(line):
                problems.append(
                    f"{loc}:{lineno}: テンプレート参照にハードコード絶対パス "
                    f"(~/.claude/skills/.../templates/) が再混入しています: {line.strip()}"
                )

    if problems:
        return CheckResult(
            check_id, False,
            "テンプレート参照に不一致（実ファイル欠落 or 絶対パス再混入）があります",
            "\n".join("    " + p for p in problems),
        )
    return CheckResult(
        check_id, True,
        "5スキルのテンプレート参照が相対パスで実在し、ハードコード絶対パスの再混入なし",
    )


# 実行する検査関数の一覧（順序が出力順）。
CHECKS = [
    check_frontmatter,
    check_common_block,
    check_fallback_msg,
    check_meta_format,
    check_env_json,
    check_template_ref,
]


# ---------------------------------------------------------------------------
# レポート生成・エントリポイント
# ---------------------------------------------------------------------------

def render_text(results, verbose):
    """text 形式のレポートを返す。"""
    lines = []
    passed_count = sum(1 for r in results if r.passed)
    total = len(results)
    for r in results:
        if r.passed:
            if verbose:
                lines.append(f"✓ [{r.check_id}] {r.summary}")
        else:
            lines.append(f"✗ [{r.check_id}] {r.summary}")
            if r.detail:
                lines.append(r.detail)
    lines.append("———————————————————————————————")
    lines.append(f"検査 {total} 件中 {passed_count} 件 PASS / {total - passed_count} 件 FAIL")
    return "\n".join(lines)


def render_json(results):
    """json 形式のレポートを返す。"""
    payload = {
        "results": [r.to_dict() for r in results],
        "passed": sum(1 for r in results if r.passed),
        "total": len(results),
        "all_passed": all(r.passed for r in results),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="cc-task-skills 横断整合性チェック（FR-3）",
    )
    parser.add_argument(
        "--root",
        default=None,
        help="検査対象リポジトリルートを明示（既定: git ルート → スクリプトの親の親）",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="出力形式（既定: text）",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="一致した検査も含めて全件表示する",
    )
    args = parser.parse_args(argv)

    try:
        root = resolve_root(args.root)
        repo = Repo(root)
        print(f"検査対象ルート: {root}", file=sys.stderr)

        results = []
        for check in CHECKS:
            try:
                results.append(check(repo))
            except CheckError:
                raise
            except Exception as exc:  # noqa: BLE001 - 想定外は実行エラー(2)として扱う
                raise CheckError(f"検査 {check.__name__} 実行中にエラー: {exc}")

    except CheckError as exc:
        print(f"実行エラー: {exc}", file=sys.stderr)
        return 2

    if args.format == "json":
        print(render_json(results))
    else:
        print(render_text(results, args.verbose))

    return 0 if all(r.passed for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
