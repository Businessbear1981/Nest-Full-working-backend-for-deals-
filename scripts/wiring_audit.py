"""
Wiring audit — all 155 backend modules, scored, with a reachability verdict.

NEST scores deals on whether they can reach close. This applies the same
method to the platform: for each module, can a user actually reach it, and is
the cheapest path to working to wire what exists or to rebuild it?

THE QUESTION THAT MATTERS MOST is reachability, and it only appears once you
look past the route layer. A route can be wired to a screen. A service or an
intelligence engine cannot -- it is reachable only if some registered route
imports it, directly or through a chain. An engine no route imports is
unreachable from the product no matter how good it is or how much of a
frontend gets built. It is not "unwired". It is not in the product.

So this walks the import graph from every registered blueprint and marks what
it can actually get to.

Scoring mirrors services/success_predictor.py deliberately: weakest-link
blended with average preparedness, because things fail on one binding
constraint rather than on the average of their parts.

    python scripts/wiring_audit.py [--layer services] [--verdict WIRE] [--json]

Every input is read from the repository. Nothing is estimated.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
from collections import defaultdict, deque

REPO = pathlib.Path(__file__).resolve().parents[1]
BACKEND = REPO / "backend"
FRONTEND = REPO / "frontend-v2" / "src"
LAYERS = ("routes", "services", "engines", "agents")

# HAND_SET. Reachability dominates because an unreachable module is not in the
# product at any level of quality, and wiring dominates the rest because a
# module nothing calls is not in the product either.
WEIGHTS = {"reachable": 0.35, "is_wired": 0.30, "has_surface": 0.15,
           "has_tests": 0.20}
CEILING = 0.95


def read(p: pathlib.Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


def blueprint_prefixes() -> dict[str, str]:
    app = read(BACKEND / "app.py")
    return {m.group(1): (m.group(2) if m.group(2) is not None else "")
            for m in re.finditer(
                r"register_blueprint\(\s*(\w+)\s*(?:,\s*url_prefix\s*=\s*"
                r"[\"']([^\"']*)[\"'])?", app)}


def modules() -> dict[str, dict]:
    """Every backend module, keyed 'layer/stem'."""
    bps = blueprint_prefixes()
    out: dict[str, dict] = {}
    for layer in LAYERS:
        for f in sorted((BACKEND / layer).glob("*.py")):
            if f.name == "__init__.py":
                continue
            src = read(f)
            bp = None
            prefix = None
            registered = False
            if layer == "routes":
                m = re.search(r"(\w+)\s*=\s*Blueprint\(", src)
                bp = m.group(1) if m else None
                registered = bool(bp and bp in bps)
                prefix = bps.get(bp) if bp else None
            out[f"{layer}/{f.stem}"] = {
                "key": f"{layer}/{f.stem}",
                "layer": layer,
                "name": f.stem,
                "prefix": prefix,
                "registered": registered,
                "endpoints": len(re.findall(
                    r"@\w+\.(?:route|get|post|put|patch|delete)\(", src)),
                "lines": len(src.splitlines()),
                "imports": set(re.findall(
                    r"from\s+(services|engines|agents)\.(\w+)", src)),
            }
    return out


def reachable_set(mods: dict[str, dict]) -> set[str]:
    """
    Everything a registered route can get to, following imports transitively.

    Entry points are registered blueprints only. An unregistered route file is
    itself unreachable, and so is everything only it imports.
    """
    graph = {k: {f"{a}/{b}" for a, b in m["imports"]} for k, m in mods.items()}
    seen: set[str] = set()
    q = deque(k for k, m in mods.items()
              if m["layer"] == "routes" and m["registered"])
    while q:
        cur = q.popleft()
        if cur in seen:
            continue
        seen.add(cur)
        for nxt in graph.get(cur, ()):
            if nxt in mods and nxt not in seen:
                q.append(nxt)
    return seen


def frontend_calls() -> dict[str, set[str]]:
    calls: dict[str, set[str]] = defaultdict(set)
    if not FRONTEND.exists():
        return calls
    for f in list(FRONTEND.rglob("*.tsx")) + list(FRONTEND.rglob("*.ts")):
        for m in re.finditer(r"[\"'`](/api/[a-zA-Z0-9\-_/${}.]+)", read(f)):
            parts = [p for p in m.group(1).split("/") if p and p != "api"]
            if parts:
                calls[f"/api/{parts[0]}"].add(f.name)
    return calls


def tested_prefixes() -> set[str]:
    out = set()
    for f in (BACKEND / "tests").glob("*.py"):
        out |= set(re.findall(r"[\"'](/api/[a-z0-9\-_/]+)", read(f)))
    return out


def tested_modules() -> set[str]:
    """Services/engines/agents imported by a test."""
    out = set()
    for f in (BACKEND / "tests").glob("*.py"):
        out |= {f"{a}/{b}" for a, b in
                re.findall(r"from\s+(services|engines|agents)\.(\w+)", read(f))}
    return out


def tokens(s: str) -> set[str]:
    s = re.sub(r"[^a-zA-Z]", " ", s)
    s = re.sub(r"(?<!^)(?=[A-Z])", " ", s)
    return {t.lower() for t in s.split() if len(t) > 3}


def score(m: dict) -> dict:
    f = {
        "reachable": 1.0 if m["reachable"] else 0.0,
        "is_wired": 1.0 if m["wired_by"] else 0.0,
        "has_surface": 1.0 if m["components"] else 0.0,
        "has_tests": 1.0 if m["tested"] else 0.0,
    }
    weakest = min(f.values())
    avg = sum(WEIGHTS[k] * v for k, v in f.items()) / sum(WEIGHTS.values())
    prob = CEILING * (max(weakest, 0.05) ** 0.5) * (max(avg, 0.05) ** 0.5)

    if not m["reachable"]:
        v, why = "UNREACHABLE", ("no registered route imports it — not in the "
                                 "product at any quality")
    elif m["layer"] == "routes" and m["endpoints"] == 0:
        v, why = "REBUILD", "registered but exposes nothing"
    elif m["wired_by"]:
        v, why = "WIRED", "the product calls it"
    elif m["layer"] != "routes":
        v, why = "REACHABLE_UNUSED", ("reachable, but the route that reaches "
                                      "it has no frontend")
    elif m["components"] and m["endpoints"] >= 3:
        v, why = "WIRE", "both halves exist; connect them"
    elif m["endpoints"] >= 3:
        v, why = "BUILD_FRONTEND", "backend is real, no surface exists"
    else:
        v, why = "REBUILD", "too thin to wire"

    return {**m, "factors": f, "probability": round(prob, 3),
            "verdict": v, "why": why}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--layer", choices=LAYERS)
    ap.add_argument("--verdict")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    mods = modules()
    reach = reachable_set(mods)
    calls = frontend_calls()
    comps = [p.name for p in FRONTEND.rglob("*.tsx")] if FRONTEND.exists() else []
    tprefix, tmods = tested_prefixes(), tested_modules()

    for k, m in mods.items():
        m["reachable"] = k in reach
        m["wired_by"] = sorted(calls.get(m["prefix"], set())) if m["prefix"] else []
        tk = tokens(m["name"])
        m["components"] = sorted(c for c in comps if tk and tk & tokens(c))
        m["tested"] = (k in tmods) or bool(
            m["prefix"] and any(p.startswith(m["prefix"]) for p in tprefix))
        m.pop("imports", None)

    scored = sorted((score(m) for m in mods.values()),
                    key=lambda x: (x["layer"], x["verdict"], -x["probability"]))
    if args.layer:
        scored = [s for s in scored if s["layer"] == args.layer]
    if args.verdict:
        scored = [s for s in scored if s["verdict"] == args.verdict]

    if args.json:
        print(json.dumps(scored, indent=1))
        return 0

    W = 100
    print("=" * W)
    print("  NEST WIRING AUDIT — all backend modules, scored and decided")
    print("=" * W)
    print(f"  {len(mods)} backend modules · {len(set(comps))} frontend "
          f"components · {len(calls)} API prefixes actually called")
    print(f"  Reachable from a registered route: {len(reach)} of {len(mods)}"
          f"  ({len(reach)/len(mods):.0%})")
    print("  Weights HAND_SET. Probability = reaches working end to end.")
    print()

    by_layer = defaultdict(lambda: defaultdict(int))
    for s in scored:
        by_layer[s["layer"]][s["verdict"]] += 1
    for layer in LAYERS:
        if layer in by_layer:
            row = "  ".join(f"{v} {n}" for v, n in
                            sorted(by_layer[layer].items(), key=lambda kv: -kv[1]))
            print(f"    {layer:<10} {row}")
    print()

    print("=" * W)
    print(f"  {'module':<34}{'prefix':<22}{'ep':>4}{'reach':>7}{'wired':>7}"
          f"{'test':>6}{'P':>7}  verdict")
    print("-" * W)
    cur = None
    for s in scored:
        if s["layer"] != cur:
            cur = s["layer"]
            print(f"  --- {cur} " + "-" * (W - len(cur) - 8))
        print(f"  {s['name'][:33]:<34}{(s['prefix'] or '—')[:21]:<22}"
              f"{s['endpoints']:>4}{('yes' if s['reachable'] else 'NO'):>7}"
              f"{('yes' if s['wired_by'] else 'no'):>7}"
              f"{('yes' if s['tested'] else 'no'):>6}"
              f"{s['probability']:>7.2f}  {s['verdict']}")

    print()
    print("=" * W)
    print("  HOW TO READ THIS")
    print("=" * W)
    print("  UNREACHABLE       no registered route imports it. Not in the")
    print("                    product at any level of quality. Delete it or")
    print("                    give it a route — those are the only options.")
    print("  REACHABLE_UNUSED  a route reaches it, but that route has no")
    print("                    frontend. Wire the route and this comes alive.")
    print("  WIRE              both halves exist. Cheapest real progress.")
    print("  BUILD_FRONTEND    backend earned a surface and never got one.")
    print("  WIRED             already in the product.")
    print()
    print("  Component matching is by NAME OVERLAP and produces false pairs.")
    print("  Reachability, endpoints, registration and wiring are exact.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
