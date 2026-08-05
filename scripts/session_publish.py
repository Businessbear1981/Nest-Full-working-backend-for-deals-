"""
Close a session: file the day, then publish it to the Kevin workspace.

Three things have to happen at the end of every session and all three get
skipped when they are three separate commands nobody remembers:

    1. file the day        -> docs/filecabinet/YYYY-MM-DD.md  (canonical)
    2. render the handoff  -> docs/filecabinet/YYYY-MM-DD-handoff.md
    3. publish to Kevin    -> <workspace>/sessions/, NEST-branded

    python scripts/session_publish.py
    python scripts/session_publish.py --date 2026-08-04
    python scripts/session_publish.py --workspace "D:\\elsewhere\\Kevin"

The workspace is the shared platform folder, not a git repo -- it is the
readable copy. The repo log stays canonical because it travels with the code
through PRs, where both people see it.
"""
from __future__ import annotations

import argparse
import datetime as dt
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
PY = sys.executable
FILE_DAY = REPO / ".claude" / "skills" / "nest-filecabinet" / "file_day.py"
BRAND = REPO / "scripts" / "nest_brand.py"
OPEN = REPO / "scripts" / "session_open.py"

DEFAULT_WORKSPACE = pathlib.Path(
    r"C:\Users\Sean Gilmore\OneDrive\Desktop\Kevin")


def run(*args: str | pathlib.Path, quiet: bool = False) -> bool:
    r = subprocess.run([str(a) for a in args], cwd=REPO,
                       capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print(f"  ! failed: {' '.join(str(a) for a in args[1:3])}",
              file=sys.stderr)
        if r.stderr.strip():
            print("    " + r.stderr.strip().splitlines()[-1], file=sys.stderr)
        return False
    if not quiet and r.stdout.strip():
        print("  " + r.stdout.strip().splitlines()[-1])
    return True


def brand(src: pathlib.Path, dst: pathlib.Path) -> bool:
    if not src.exists():
        print(f"  - skipped {src.name} (not written)")
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    return run(PY, BRAND, src, "--audience", "internal", "--out", dst,
               quiet=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--date", help="YYYY-MM-DD; defaults to today")
    ap.add_argument("--workspace", type=pathlib.Path,
                    default=DEFAULT_WORKSPACE)
    ap.add_argument("--no-open", action="store_true",
                    help="skip regenerating the session opener")
    args = ap.parse_args()

    day = (dt.date.fromisoformat(args.date) if args.date else dt.date.today())
    stamp = day.isoformat()
    fc = REPO / "docs" / "filecabinet"
    sessions = args.workspace / "sessions"

    print(f"Closing {stamp}")

    # 1. File the day. Append-only -- safe to run twice.
    print("\n[1/3] filing the day")
    run(PY, FILE_DAY, "--date", stamp, "--handoff")

    # 2. Move the snapshot baseline forward so the next session gets a delta.
    #    Deliberately does NOT pass --out: the opener was written at the START
    #    of the session against the previous baseline, and rewriting it here --
    #    where the baseline has already advanced to HEAD -- replaces a real
    #    synopsis with "Nothing since the baseline." The opener is a record of
    #    what the session opened with and is never regenerated at close.
    if not args.no_open:
        print("\n[2/3] snapshotting readiness for the next session's delta")
        run(PY, OPEN, "--save", quiet=True)
    else:
        print("\n[2/3] skipped")

    # 3. Publish to the shared workspace.
    print(f"\n[3/3] publishing to {sessions}")
    published = 0
    for src, name in [
        (fc / f"{stamp}.md", f"{stamp}-session-notes.html"),
        (fc / f"{stamp}-handoff.md", f"{stamp}-handoff.html"),
        (REPO / "docs" / "sessions" / f"{stamp}-open.md",
         f"{stamp}-open.html"),
    ]:
        if brand(src, sessions / name):
            print(f"  + {name}")
            published += 1

    # The module map is the one artefact worth refreshing every session, since
    # it is what the integration conversation is actually about.
    mm = REPO / "docs" / "NEST_MODULE_MAP.md"
    if mm.exists():
        (args.workspace / "briefs").mkdir(parents=True, exist_ok=True)
        (args.workspace / "briefs" / "NEST_MODULE_MAP.md").write_text(
            mm.read_text(encoding="utf-8"), encoding="utf-8")
        print("  + briefs/NEST_MODULE_MAP.md")

    print(f"\n{published} session files published.")
    print("\nStill needs you: the journal entry in "
          f"{args.workspace / 'journal'}")
    print("Git records what changed. It does not record what you decided.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
