#!/usr/bin/env python3
"""cc-task-skills 分量計測スクリプト。

スキル1回の実行で **常時ロードされる行数**（SKILL.md 本体）と、
**該当フェーズに入って初めて読み込まれる行数**（references/ / templates/）を分けて表示する。

「重厚さ」の議論を印象ではなく数値で行うための道具であり、
`scripts/check_consistency.py` のような合否判定は持たない（常に exit 0）。

依存は Python 3 標準ライブラリのみ。

使い方:
  python3 scripts/measure_weight.py        # スキル別の内訳
  python3 scripts/measure_weight.py -v     # 識別子と重複の統計も表示
"""

import argparse
import collections
import io
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ["task-init", "task-req", "task-req-update", "task-design", "task-dev", "task-verify"]

ID_RE = re.compile(r"\b([A-Z]{1,3})-(\d+[a-z]?)\b")


def lines_of(path):
    if not path.is_file():
        return 0
    return io.open(path, encoding="utf-8").read().count("\n")


def measure_skill(skill):
    base = ROOT / "skills" / skill
    always = lines_of(base / "SKILL.md")
    refs = {p.name: lines_of(p) for p in sorted((base / "references").glob("*.md"))}
    tmpl = {p.name: lines_of(p) for p in sorted((base / "templates").glob("*.md"))}
    return always, refs, tmpl


def report_weight():
    print(f"{'スキル':<16}{'常時':>7}{'条件付き':>9}{'計':>7}  内訳（条件付き）")
    print("─" * 78)
    t_always = t_lazy = 0
    for skill in SKILLS:
        always, refs, tmpl = measure_skill(skill)
        lazy = sum(refs.values()) + sum(tmpl.values())
        t_always += always
        t_lazy += lazy
        detail = " / ".join(f"{n}:{v}" for n, v in list(refs.items()) + list(tmpl.items()))
        print(f"{skill:<16}{always:>7}{lazy:>9}{always + lazy:>7}  {detail}")
    print("─" * 78)
    print(f"{'合計':<16}{t_always:>7}{t_lazy:>9}{t_always + t_lazy:>7}")
    print()
    for name in ("CLAUDE.md", "README.md"):
        p = ROOT / name
        kb = len(io.open(p, encoding="utf-8").read().encode("utf-8")) / 1024
        note = "（全セッションで常時ロード）" if name == "CLAUDE.md" else ""
        print(f"{name:<16}{lines_of(p):>7} 行  {kb:>5.1f} KB  {note}")
    docs = sorted((ROOT / "docs").glob("*.md"))
    if docs:
        print(f"{'docs/*.md':<16}{sum(lines_of(p) for p in docs):>7} 行  "
              f"（必要なときだけ開く。{len(docs)} ファイル）")


def report_detail():
    files = ([ROOT / "skills" / s / "SKILL.md" for s in SKILLS]
             + sorted(ROOT.glob("skills/*/references/*.md"))
             + sorted(ROOT.glob("skills/*/templates/*.md")))
    ids = collections.Counter()
    for f in files:
        for m in ID_RE.finditer(io.open(f, encoding="utf-8").read()):
            ids[f"{m.group(1)}-{m.group(2)}"] += 1
    once = [k for k, v in ids.items() if v == 1]
    ns = {k.rsplit("-", 1)[0] for k in ids}
    print()
    print(f"識別子: ユニーク {len(ids)} 件 / 名前空間 {len(ns)} 種 / "
          f"1回しか出現しないもの {len(once)} 件")

    waste = 0
    for f in files:
        sent = collections.defaultdict(int)
        for line in io.open(f, encoding="utf-8"):
            for piece in re.split(r"(?<=。)", line.strip()):
                piece = piece.strip()
                if len(piece) >= 35:
                    sent[piece] += 1
        waste += sum(len(k) * (v - 1) for k, v in sent.items() if v >= 2)
    print(f"同一ファイル内で重複する散文（35字以上）: 約 {waste} 字")
    print()
    print("※ 分量の削減は識別子や行の削除ではなく、常時ロードの削減で行う方針である")
    print("  （CLAUDE.md「設計原則: 識別子とエラー列挙は削らず、増やさない」を参照）。")


def main():
    ap = argparse.ArgumentParser(description="cc-task-skills の分量を計測する")
    ap.add_argument("-v", "--verbose", action="store_true", help="識別子・重複の統計も表示する")
    args = ap.parse_args()
    report_weight()
    if args.verbose:
        report_detail()
    return 0


if __name__ == "__main__":
    sys.exit(main())
