"""
Print the platform readiness report.

All logic lives in backend/services/platform_readiness.py. This file only
formats it -- if it held any scoring of its own there would be two sources of
truth and one of them would be silently wrong.

    python scripts/wiring_audit.py [--layer services] [--verdict WIRE] [--json]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))

from services.platform_readiness import LAYERS, VERDICTS, scan  # noqa: E402

W = 100


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--layer", choices=LAYERS)
    ap.add_argument("--verdict", choices=VERDICTS)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    report = scan()
    mods = report["modules"]
    if args.layer:
        mods = [m for m in mods if m["layer"] == args.layer]
    if args.verdict:
        mods = [m for m in mods if m["verdict"] == args.verdict]

    if args.json:
        print(json.dumps({**report, "modules": mods}, indent=1))
        return 0

    t = report["totals"]
    print("=" * W)
    print("  NEST PLATFORM READINESS — can a user reach this code?")
    print("=" * W)
    print(f"  {t['modules']} backend modules · {t['frontend_components']} "
          f"frontend components · {t['api_prefixes_called']} API prefixes "
          f"actually called")
    print(f"  Reachable from a registered route: {t['reachable']} of "
          f"{t['modules']}  ({t['pct_reachable']:.0%})")
    print(f"  Route modules the product calls:   {t['routes_wired']} of "
          f"{t['route_modules']}")
    print(f"  Weights {report['provenance']['weights_provenance']}. "
          f"Probability = reaches a user.")
    print()
    for layer in LAYERS:
        counts = report["by_layer"].get(layer)
        if counts:
            row = "  ".join(f"{v} {n}" for v, n in
                            sorted(counts.items(), key=lambda kv: -kv[1]))
            print(f"    {layer:<10} {row}")
    print()

    print("=" * W)
    print(f"  {'module':<34}{'prefix':<22}{'ep':>4}{'reach':>7}{'wired':>7}"
          f"{'test':>6}{'P':>7}  verdict")
    print("-" * W)
    cur = None
    for m in mods:
        if m["layer"] != cur:
            cur = m["layer"]
            print(f"  --- {cur} " + "-" * (W - len(cur) - 8))
        print(f"  {m['name'][:33]:<34}{(m['prefix'] or '—')[:21]:<22}"
              f"{m['endpoints']:>4}{('yes' if m['reachable'] else 'NO'):>7}"
              f"{('yes' if m['wired_by'] else 'no'):>7}"
              f"{('yes' if m['tested'] else 'no'):>6}"
              f"{m['probability']:>7.2f}  {m['verdict']}")

    if report["redundant_prefixes"]:
        print()
        print("=" * W)
        print("  REDUNDANCY — one prefix served by several route modules")
        print("=" * W)
        for prefix, names in sorted(report["redundant_prefixes"].items()):
            print(f"  {prefix:<24} {', '.join(names)}")

    print()
    print("=" * W)
    print("  HOW TO READ THIS")
    print("=" * W)
    print("  UNREACHABLE       no registered route imports it. Absent from the")
    print("                    product at any quality. Route it or delete it.")
    print("  REACHABLE_UNUSED  a route reaches it, but that route has no")
    print("                    frontend. Wire the route and this comes alive.")
    print("  WIRE              both halves exist. Cheapest real progress.")
    print("  BUILD_FRONTEND    backend earned a surface and never got one.")
    print("  WIRED             already in the product.")
    print()
    print(f"  {report['scope_note']}")
    print(f"  Approximate: {report['provenance']['approximate'][0]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
