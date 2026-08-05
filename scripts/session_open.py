"""
Open a cross-working session with the synopsis, generated.

A joint session between Sean and Kevin starts by agreeing on what is true.
Doing that from memory is how two people spend twenty minutes discovering they
were describing different commits. This reads git and the readiness engine and
prints the four things a session has to open with:

    1. Code pushed since the last session
    2. New modules, and new terms that need defining
    3. Backend/frontend integration -- where it stands, and what moved
    4. Anything that got worse

    python scripts/session_open.py                  # since the last snapshot
    python scripts/session_open.py --since HEAD~10  # explicit baseline
    python scripts/session_open.py --save           # record today's snapshot
    python scripts/session_open.py --out docs/sessions/2026-08-05-open.md

The snapshot lives in docs/sessions/.snapshot.json so the next session can say
what *moved* rather than only what is. Without it there is no delta and the
integration section reads as a status board, which nobody acts on.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))

from services.platform_readiness import scan  # noqa: E402

SESSIONS = REPO / "docs" / "sessions"
SNAPSHOT = SESSIONS / ".snapshot.json"

# Verdicts where a rising count is bad news, and the honest framing for each.
WORSE_IF_UP = {
    "UNREACHABLE": "modules no route can reach",
    "HOLLOW": "routes wired to nothing",
    "REBUILD": "modules too thin to keep",
}


def git(*args: str) -> str:
    try:
        return subprocess.run(("git",) + args, cwd=REPO, capture_output=True,
                              text=True, encoding="utf-8", errors="replace",
                              check=True).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def load_snapshot() -> dict:
    if SNAPSHOT.exists():
        try:
            return json.loads(SNAPSHOT.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def commits_since(ref: str) -> list[tuple[str, str, str]]:
    raw = git("log", f"{ref}..HEAD", "--date=short",
              "--pretty=format:%h\x1f%ad\x1f%an\x1f%s")
    out = []
    for line in raw.splitlines():
        parts = line.split("\x1f")
        if len(parts) == 4:
            out.append((parts[0], parts[1], f"{parts[2]} — {parts[3]}"))
    return out


def files_added(ref: str) -> list[str]:
    raw = git("diff", "--diff-filter=A", "--name-only", f"{ref}..HEAD")
    return [ln for ln in raw.splitlines() if ln.strip()]


def new_modules(added: list[str]) -> dict[str, list[str]]:
    """Added Python modules under backend/, grouped by layer."""
    groups: dict[str, list[str]] = {}
    for path in added:
        p = pathlib.PurePosixPath(path)
        if p.suffix != ".py" or "backend" not in p.parts:
            continue
        if p.name.startswith("test_") or p.name == "__init__.py":
            continue
        parts = p.parts
        i = parts.index("backend")
        layer = parts[i + 1] if len(parts) > i + 1 else "backend"
        groups.setdefault(layer, []).append(p.stem)
    return {k: sorted(v) for k, v in sorted(groups.items())}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--since", help="baseline ref; defaults to last snapshot")
    ap.add_argument("--save", action="store_true",
                    help="record today's counts as the new baseline")
    ap.add_argument("--out", type=pathlib.Path, help="write markdown here too")
    args = ap.parse_args()

    snap = load_snapshot()
    ref = args.since or snap.get("head")
    today = dt.date.today()

    r = scan()
    t = r["totals"]
    by_verdict = r["by_verdict"]
    prev = snap.get("by_verdict", {})
    prev_totals = snap.get("totals", {})

    o: list[str] = []
    w = o.append

    w(f"# Session open — {today.strftime('%d %B %Y')}")
    w("")
    if ref:
        w(f"> Baseline `{ref}`"
          + (f" (snapshot of {snap['date']})" if snap.get("date") and
             not args.since else "")
          + f" · HEAD `{git('rev-parse', '--short', 'HEAD')}`"
          + f" · branch `{git('rev-parse', '--abbrev-ref', 'HEAD')}`")
    else:
        w("> **No baseline snapshot.** This is the first session opened this "
          "way, so everything below is a level, not a change. Run with "
          "`--save` to give the next session a delta.")
    w("")

    # --- 1. Code pushed -----------------------------------------------------
    w("## 1. Code pushed since we last spoke")
    w("")
    commits = commits_since(ref) if ref else []
    if not ref:
        w("_No baseline to diff against._")
    elif not commits:
        w("**Nothing.** No commits since the baseline. That is itself the "
          "first agenda item.")
    else:
        w(f"{len(commits)} commits.")
        w("")
        w("| Commit | Date | Who / what |")
        w("|---|---|---|")
        for sha, date, who in commits:
            w(f"| `{sha}` | {date} | {who} |")
    w("")

    # --- 2. New modules and terms ------------------------------------------
    w("## 2. New modules, and terms that need defining")
    w("")
    added = files_added(ref) if ref else []
    mods = new_modules(added)
    if not mods:
        w("_No new backend modules._")
    else:
        for layer, names in mods.items():
            w(f"**`{layer}`** — {', '.join('`' + n + '`' for n in names)}")
            w("")
        w("**Every name above needs a Volume 3 or 4A entry before this session "
          "ends: what it is, why it exists, who owns it.** A module that ships "
          "without a definition is a module the other person has to guess at, "
          "and guesses become two different mental models of the same system.")
    w("")
    docs_added = [p for p in added if p.startswith("docs/")]
    if docs_added:
        w("Documentation added: "
          + ", ".join(f"`{pathlib.PurePosixPath(p).name}`"
                      for p in sorted(docs_added)))
        w("")

    # --- 3. Integration -----------------------------------------------------
    w("## 3. Backend ↔ frontend integration")
    w("")

    def delta(now: int, was) -> str:
        if was is None:
            return ""
        d = now - was
        if d == 0:
            return " *(no change)*"
        return f" *({d:+d})*"

    w("| | Now | |")
    w("|---|---|---|")
    w(f"| Backend modules | {t['modules']} |"
      f"{delta(t['modules'], prev_totals.get('modules'))} |")
    w(f"| Reachable from a registered route | {t['reachable']} "
      f"({t['pct_reachable']:.0%}) |"
      f"{delta(t['reachable'], prev_totals.get('reachable'))} |")
    w(f"| **Unreachable — not in the product** | **{t['unreachable']}** |"
      f"{delta(t['unreachable'], prev_totals.get('unreachable'))} |")
    w(f"| Route modules the product calls | {t['routes_wired']} of "
      f"{t['route_modules']} |"
      f"{delta(t['routes_wired'], prev_totals.get('routes_wired'))} |")
    w("")
    w("| Verdict | Count | |")
    w("|---|---|---|")
    for v, n in sorted(by_verdict.items(), key=lambda kv: -kv[1]):
        w(f"| `{v}` | {n} |{delta(n, prev.get(v))} |")
    w("")
    w("Regenerate any of this with `python scripts/wiring_audit.py`. "
      "**Do not quote a number in this session that did not come from a run.**")
    w("")

    # --- 4. What got worse --------------------------------------------------
    w("## 4. What got worse")
    w("")
    regressions = []
    for v, label in WORSE_IF_UP.items():
        was, now = prev.get(v), by_verdict.get(v, 0)
        if was is not None and now > was:
            regressions.append(f"- **`{v}` {was} → {now}** — {label}. "
                               "Something was added without a path to a user.")
    if not prev:
        w("_No baseline to compare against._")
    elif regressions:
        for line in regressions:
            w(line)
        w("")
        w("**Handle these before the agenda.** A regression discussed at the "
          "end of a session is a regression that survives it.")
    else:
        w("Nothing regressed against the baseline.")
    w("")

    # --- The standing rule --------------------------------------------------
    w("---")
    w("")
    w("## The standing rule")
    w("")
    w("**If a process is flawed, rebuild it end to end. Do not patch it.**")
    w("")
    w("A patched process keeps the shape of the mistake and hides it behind a "
      "fix, which is how a hollow route happens: fifteen endpoints answering "
      "correctly and computing nothing. Rebuilding costs a day and ends the "
      "argument. Patching costs an hour and reopens it every month.")
    w("")
    w("Test to apply, out loud, before choosing: *if we were building this "
      "today knowing what we know, would we build it this way?* If no, it is a "
      "rebuild, and the rebuild decision goes in today's file cabinet entry "
      "with the reason.")

    text = "\n".join(o) + "\n"
    print(text)

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
        print(f"wrote {args.out}", file=sys.stderr)

    if args.save:
        SESSIONS.mkdir(parents=True, exist_ok=True)
        SNAPSHOT.write_text(json.dumps({
            "date": today.isoformat(),
            "head": git("rev-parse", "HEAD"),
            "totals": t,
            "by_verdict": by_verdict,
        }, indent=2), encoding="utf-8")
        print(f"snapshot saved {SNAPSHOT}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
