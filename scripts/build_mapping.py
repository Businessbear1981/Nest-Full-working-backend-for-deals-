"""
Build Operations Manual Volume 4 (Part B) — the module and process mapping.

Volume 4's narrative half lives in docs/NEST_GLOSSARY.md: what each named
agent, engine and pillar was intended to do. This is the other half -- the
machine-checked map of what actually reaches a user, generated from
services/platform_readiness.py so it cannot drift from the code.

    python scripts/build_mapping.py [--out docs/NEST_MODULE_MAP.md]
"""
from __future__ import annotations

import argparse
import datetime as dt
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))

from services.platform_readiness import LAYERS, WEIGHTS, scan  # noqa: E402

VERDICT_MEANING = {
    "WIRED": ("In the product", "A screen calls it and it calls real logic. "
              "Nothing to do."),
    "HOLLOW": ("Connected but empty", "Wired end to end and computes nothing — "
               "imports no service, engine or agent, so it returns values "
               "written in the route file itself. Needs a body, not a "
               "connection."),
    "WIRE": ("Both halves exist", "A backend with endpoints and a frontend "
             "component that does not call it. The cheapest real progress "
             "available."),
    "BUILD_FRONTEND": ("Backend with no surface", "Endpoints exist and are "
                       "reachable. No screen was ever built."),
    "REACHABLE_UNUSED": ("Alive but idle", "A registered route imports it, but "
                         "that route has no frontend. Wiring the route brings "
                         "this with it."),
    "UNREACHABLE": ("Not in the product", "No registered route imports it, "
                    "directly or through any chain. No amount of frontend work "
                    "reaches it because nothing on the server can call it "
                    "either. Route it or delete it."),
    "REBUILD": ("Too thin", "Registered but exposing almost nothing."),
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=pathlib.Path,
                    default=REPO / "docs" / "NEST_MODULE_MAP.md")
    args = ap.parse_args()

    r = scan()
    t = r["totals"]
    mods = r["modules"]
    today = dt.date.today().strftime("%d %B %Y")

    o: list[str] = []
    w = o.append

    w("# NEST Operations Manual — Volume 4, Part B")
    w("## The Module Map")
    w("")
    w(f"> **Generated {today}** by `scripts/build_mapping.py` from "
      "`backend/services/platform_readiness.py`. Do not hand-edit — the code "
      "is the source of truth and a hand edit will be overwritten.")
    w(">")
    w("> **What this is.** Every backend module, and whether a user can "
      "actually reach it. Volume 4 Part A (`docs/NEST_GLOSSARY.md`) says what "
      "each module was *intended* to do. This says what is *true*.")
    w("")

    w("## How a module is judged")
    w("")
    w("The platform scores deals on whether they can reach close. This applies "
      "the same method to the platform: weakest-link blended with average "
      "preparedness, because things fail on one binding constraint rather than "
      "on the mean of their parts.")
    w("")
    w("| Factor | Weight | What it asks |")
    w("|---|---|---|")
    w(f"| Reachable | {WEIGHTS['reachable']:.0%} | Does a registered route "
      "import it, directly or through a chain? |")
    w(f"| Wired | {WEIGHTS['is_wired']:.0%} | Does anything in the product "
      "call it? |")
    w(f"| Substance | {WEIGHTS['has_substance']:.0%} | Does the route call "
      "real logic, or return values written in its own file? |")
    w(f"| Surface | {WEIGHTS['has_surface']:.0%} | Does a frontend component "
      "exist? |")
    w(f"| Tests | {WEIGHTS['has_tests']:.0%} | Can it be changed safely? |")
    w("")
    w("**Reachability is weighted highest** because an unreachable module is "
      "absent from the product at any level of quality. Weights are "
      "`HAND_SET`. Reachability, endpoint counts, registration and wiring are "
      "read from source and are exact; component matching is by name overlap "
      "and produces false pairs, so it never drives a verdict alone.")
    w("")
    w(f"**{r['scope_note']}**")
    w("")

    w("## Where the platform stands")
    w("")
    w("| | |")
    w("|---|---|")
    w(f"| Backend modules | **{t['modules']}** |")
    w(f"| Reachable from a registered route | {t['reachable']} "
      f"({t['pct_reachable']:.0%}) |")
    w(f"| **Unreachable — not in the product** | **{t['unreachable']}** |")
    w(f"| Route modules the product calls | **{t['routes_wired']} of "
      f"{t['route_modules']}** |")
    w(f"| Frontend components | {t['frontend_components']} |")
    w(f"| API prefixes actually called | {t['api_prefixes_called']} |")
    w("")

    w("### By layer")
    w("")
    w("| Layer | Verdicts |")
    w("|---|---|")
    for layer in LAYERS:
        counts = r["by_layer"].get(layer)
        if counts:
            row = " · ".join(f"{v} **{n}**" for v, n in
                             sorted(counts.items(), key=lambda kv: -kv[1]))
            w(f"| `{layer}` | {row} |")
    w("")

    w("## What each verdict means, and what to do about it")
    w("")
    for v, (short, long) in VERDICT_MEANING.items():
        n = r["by_verdict"].get(v, 0)
        w(f"**`{v}` — {short}** · {n} modules")
        w("")
        w(long)
        w("")

    if r["redundant_prefixes"]:
        w("## Redundancy")
        w("")
        w("One API prefix served by more than one route module. Each is a "
          "collision to resolve, not a feature.")
        w("")
        w("| Prefix | Route modules |")
        w("|---|---|")
        for prefix, names in sorted(r["redundant_prefixes"].items()):
            w(f"| `{prefix}` | {', '.join(f'`{n}`' for n in names)} |")
        w("")

    # --- Priority worklists, most actionable first.
    for v, heading, why in [
        ("HOLLOW", "Fix first — connected but empty",
         "These read as working on any dashboard and deliver nothing. The most "
         "flattering failure mode the platform has."),
        ("WIRE", "Then — both halves exist, connect them",
         "A backend with endpoints and a component that does not call it. "
         "Cheapest real progress in the codebase."),
        ("BUILD_FRONTEND", "Then — backends that earned a surface",
         "Reachable, endpoints live, no screen was ever built."),
        ("UNREACHABLE", "Decide — route it or delete it",
         "No registered route imports these. Carrying them reads as capability "
         "the platform does not have."),
    ]:
        rows = [m for m in mods if m["verdict"] == v]
        if not rows:
            continue
        w(f"## {heading}")
        w("")
        w(why)
        w("")
        w("| Module | Layer | Prefix | Endpoints | Tested |")
        w("|---|---|---|---|---|")
        for m in sorted(rows, key=lambda x: (-x["endpoints"], x["name"])):
            w(f"| `{m['name']}` | {m['layer']} | "
              f"{'`'+m['prefix']+'`' if m['prefix'] else '—'} | "
              f"{m['endpoints']} | {'yes' if m['tested'] else 'no'} |")
        w("")

    w("## Full map")
    w("")
    cur = None
    for m in mods:
        if m["layer"] != cur:
            cur = m["layer"]
            w(f"### `{cur}`")
            w("")
            w("| Module | Prefix | Endpoints | Reachable | Wired | Tested | P | Verdict |")
            w("|---|---|---|---|---|---|---|---|")
        w(f"| `{m['name']}` | {'`'+m['prefix']+'`' if m['prefix'] else '—'} | "
          f"{m['endpoints']} | {'yes' if m['reachable'] else '**NO**'} | "
          f"{'yes' if m['wired_by'] else 'no'} | "
          f"{'yes' if m['tested'] else 'no'} | {m['probability']:.2f} | "
          f"`{m['verdict']}` |")
    w("")

    w("---")
    w("")
    w("## Regenerate")
    w("")
    w("```bash")
    w("python scripts/build_mapping.py")
    w("python scripts/wiring_audit.py            # same data, terminal")
    w("python scripts/wiring_audit.py --verdict UNREACHABLE")
    w("```")

    args.out.write_text("\n".join(o) + "\n", encoding="utf-8")
    print(f"wrote {args.out}")
    print(f"  {t['modules']} modules · {t['unreachable']} unreachable · "
          f"{t['routes_wired']}/{t['route_modules']} routes wired")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
