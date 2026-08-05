"""
Assemble the NEST Skills book — every skill, in one document.

The skills are the repeatable procedures: what NEST does the same way twice.
They live as separate SKILL.md files because that is how they are loaded on
demand. This gathers them into one readable volume for people who need to know
what the procedures ARE without running any of them.

    python scripts/build_skills_book.py [--out docs/NEST_SKILLS.md]

Generated from .claude/skills/. Do not hand-edit the output.
"""
from __future__ import annotations

import argparse
import datetime as dt
import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parents[1]
SKILLS = REPO / ".claude" / "skills"

# Reading order: bracket the deal work with the session procedures.
ORDER = ["kevin", "nest-docs", "nest-deal-run", "nest-house-style",
         "nest-truth-shield", "nest-filecabinet"]


def frontmatter(text: str) -> tuple[dict[str, str], str]:
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not m:
        return {}, text
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    return meta, m.group(2).lstrip("\n")


def demote(body: str) -> str:
    """Push every heading down one level so skills nest under their section."""
    out = []
    fence = False
    for line in body.splitlines():
        if line.lstrip().startswith("```"):
            fence = not fence
        if not fence and re.match(r"^#{1,5} ", line):
            line = "#" + line
        out.append(line)
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=pathlib.Path,
                    default=REPO / "docs" / "NEST_SKILLS.md")
    args = ap.parse_args()

    found = {p.parent.name: p for p in SKILLS.glob("*/SKILL.md")}
    names = [n for n in ORDER if n in found]
    names += sorted(n for n in found if n not in ORDER)

    today = dt.date.today().strftime("%d %B %Y")
    o: list[str] = []
    w = o.append

    w("# NEST Skills")
    w("## The repeatable procedures, in one volume")
    w("")
    w(f"> **Generated {today}** by `scripts/build_skills_book.py` from "
      "`.claude/skills/`. Do not hand-edit — the skill files are the source "
      "of truth.")
    w("")
    w("**What a skill is.** A procedure NEST runs the same way every time, "
      "written down once. Before these existed the same work was rebuilt each "
      "session — the deal chain hand-rolled as a throwaway script, the "
      "document format reconstructed from memory, the verification pass done "
      "or skipped depending on how much time was left. Two briefs written a "
      "day apart could quote different numbers for the same deal and neither "
      "author would know.")
    w("")
    w("A skill is loaded on demand when the work matches its description. It "
      "costs nothing until it is needed.")
    w("")

    w("## The set")
    w("")
    w("| Skill | Use it when |")
    w("|---|---|")
    for n in names:
        meta, _ = frontmatter(found[n].read_text(encoding="utf-8"))
        desc = meta.get("description", "")
        # The description is written for retrieval and front-loads its
        # triggers; the first clause is the readable part.
        short = desc.split(". ")[0].rstrip(".")
        if len(short) > 150:
            short = short[:147].rsplit(" ", 1)[0] + "…"
        w(f"| **`/{n}`** | {short} |")
    w("")

    w("**The intended flow.** `kevin` appears twice because it brackets the "
      "others — a session that opens on agreed facts but never closes on a "
      "filed record leaves the next one reconstructing both from memory.")
    w("")
    w("```")
    w("kevin             →  open the session on generated, agreed facts")
    w("nest-docs         →  decide what the silo owes")
    w("nest-deal-run     →  produce the numbers by running the engines")
    w("nest-house-style  →  format them into a document, tagged and sourced")
    w("nest-truth-shield →  verify every claim before it leaves")
    w("nest-filecabinet  →  file what was decided, built, found, left open")
    w("kevin             →  close the session and publish it")
    w("```")
    w("")

    w("## Design rules")
    w("")
    w("**A skill calls the code. It never reimplements it.** The engines in "
      "`backend/services/` are the single source of truth for every NEST "
      "number. A skill is the *procedure* for invoking them and presenting "
      "the result. The moment a skill hardcodes a threshold there are two "
      "sources of truth and one of them is silently wrong.")
    w("")
    w("**A skill earns its place by being run more than once.** A procedure "
      "used once is a script. Writing it up as a skill adds a maintenance "
      "burden and a second thing to keep true.")
    w("")

    for n in names:
        meta, body = frontmatter(found[n].read_text(encoding="utf-8"))
        w("---")
        w("")
        w(f"# `/{n}`")
        w("")
        if meta.get("description"):
            w(f"> {meta['description']}")
            w("")
        w(demote(body).rstrip())
        w("")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(o) + "\n", encoding="utf-8")
    print(f"wrote {args.out}")
    print(f"  {len(names)} skills: {', '.join(names)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
