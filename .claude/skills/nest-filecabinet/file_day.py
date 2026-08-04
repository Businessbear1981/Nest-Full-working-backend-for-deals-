"""
File a day into the NEST file cabinet.

Reads git for what was BUILT and scaffolds the rest. Git records what changed,
never what was decided or found, so those sections are left for a human --
scaffolded with prompts rather than left blank, because a blank section gets
skipped and a prompted one gets answered.

    python file_day.py [--date YYYY-MM-DD] [--handoff] [--print]

Append only. If an entry exists, new BUILT items are merged in and the human
sections are left untouched.
"""
from __future__ import annotations

import argparse
import datetime as dt
import pathlib
import re
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[3]
CABINET = REPO / "docs" / "filecabinet"

SECTIONS = ("DECIDED", "BUILT", "FOUND", "OPEN")

PROMPTS = {
    "DECIDED": ("_What closed an option today, and why? Include what it rules "
                "out. Skipping this is the most expensive omission in the log._"),
    "FOUND": ("_What is true now that was not known this morning -- especially "
              "the unwelcome things? Findings do not expire because they are "
              "inconvenient._"),
    "OPEN": "_What is unresolved, and who is it waiting on? This is tomorrow's agenda._",
}


def git(*args: str) -> str:
    try:
        return subprocess.run(("git",) + args, cwd=REPO, capture_output=True,
                              text=True, check=True).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def commits_on(day: dt.date) -> list[str]:
    """Commits authored on the given day, newest first."""
    nxt = day + dt.timedelta(days=1)
    raw = git("log", f"--since={day.isoformat()}", f"--until={nxt.isoformat()}",
              "--pretty=format:%h %s")
    return [ln for ln in raw.splitlines() if ln.strip()]


def parse(text: str) -> dict[str, list[str]]:
    """Split an existing entry into its sections."""
    out: dict[str, list[str]] = {s: [] for s in SECTIONS}
    current = None
    for line in text.splitlines():
        m = re.match(r"^## ([A-Z]+)\s*$", line)
        if m and m.group(1) in SECTIONS:
            current = m.group(1)
            continue
        if line.startswith("# "):
            current = None
            continue
        if current:
            out[current].append(line)
    return out


def render(day: dt.date, sections: dict[str, list[str]]) -> str:
    lines = [f"# {day.isoformat()}", ""]
    for s in SECTIONS:
        lines.append(f"## {s}")
        body = [ln for ln in sections.get(s, []) if ln.strip()]
        if body:
            lines.extend(body)
        elif s in PROMPTS:
            lines.append(PROMPTS[s])
        else:
            lines.append("_Nothing recorded._")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def handoff(day: dt.date, sections: dict[str, list[str]]) -> str:
    """Tomorrow's opening prompt, built from what is still open."""
    def body(key):
        got = [ln for ln in sections.get(key, [])
               if ln.strip() and not ln.strip().startswith("_")]
        return "\n".join(got) if got else "_(nothing filed)_"

    return f"""# Handoff — picking up after {day.isoformat()}

Read `docs/filecabinet/{day.isoformat()}.md` for the full day.

## Still open
{body('OPEN')}

## Unfixed findings
{body('FOUND')}

## Decisions already made — do not relitigate
{body('DECIDED')}

## Ground rules
- Numbers come from running the engines (`nest-deal-run`), never from memory.
- Apply `nest-truth-shield` before anything client-facing.
- Never push to main. PRs only.
- File the day before finishing (`nest-filecabinet`).
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--date", help="YYYY-MM-DD; defaults to today")
    ap.add_argument("--handoff", action="store_true",
                    help="also write tomorrow's starting prompt")
    ap.add_argument("--print", dest="dry", action="store_true",
                    help="print, write nothing")
    args = ap.parse_args()

    day = (dt.date.fromisoformat(args.date) if args.date else dt.date.today())
    path = CABINET / f"{day.isoformat()}.md"

    sections = parse(path.read_text(encoding="utf-8")) if path.exists() else \
        {s: [] for s in SECTIONS}

    # Merge commits into BUILT without duplicating on a re-run.
    existing = "\n".join(sections["BUILT"])
    for c in commits_on(day):
        sha = c.split()[0]
        if sha not in existing:
            sections["BUILT"].append(f"- `{sha}` {c[len(sha):].strip()}")
    if not sections["BUILT"]:
        sections["BUILT"].append("_No commits._")

    text = render(day, sections)

    if args.dry:
        print(text)
        if args.handoff:
            print(handoff(day, sections))
        return 0

    CABINET.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    print(f"filed {path}")

    if args.handoff:
        h = CABINET / f"{day.isoformat()}-handoff.md"
        h.write_text(handoff(day, sections), encoding="utf-8")
        print(f"handoff {h}")

    unfilled = [s for s in ("DECIDED", "FOUND", "OPEN")
                if not [ln for ln in sections[s]
                        if ln.strip() and not ln.strip().startswith("_")]]
    if unfilled:
        print(f"\n  Still needs you: {', '.join(unfilled)}")
        print("  Git knows what changed. It does not know what you decided.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
