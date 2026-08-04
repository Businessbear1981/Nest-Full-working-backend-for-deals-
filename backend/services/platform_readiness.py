"""
NEST Platform Readiness — the same question we ask of a deal, asked of us.

services/preflight.py asks whether a CREDIT can reach market.
services/platform_readiness.py asks whether a MODULE can reach a user.

The method is deliberately the one we sell. A module is not "60% done" because
six of ten files exist. It clears when its weakest binding constraint clears,
so the score is weakest-link blended with average preparedness -- the same
shape as success_predictor.py, for the same reason: things fail on one thing,
not on the mean of ten things.

THE FACTOR THAT ONLY APPEARS WHEN YOU LOOK PAST THE ROUTE LAYER

A route can be wired to a screen. A service or an intelligence engine cannot.
It is reachable only if some registered blueprint imports it, directly or
through a chain of imports. So REACHABILITY is computed by walking the import
graph out from every registered blueprint, and it is weighted highest.

The distinction is not pedantic. An unreachable module is not "unwired" -- it
is not in the product, and no amount of frontend work changes that, because
nothing on the server can call it either. Those are different diagnoses with
different fixes, and conflating them is how a platform accumulates named
pillars nobody can use.

WIRED IS NOT THE SAME AS DOING SOMETHING

A route can be connected end to end and still compute nothing -- a screen
calling an endpoint that returns a literal it defined in its own file. That is
wired by every structural measure and worthless by every useful one, and it is
the most flattering possible failure because every dashboard reads green.

So a wired route is additionally checked for SUBSTANCE:

  imports_logic     does it import any service, engine or agent? A route that
                    imports nothing computes nothing -- it is returning data
                    written in the route file itself.
  hardcoded_blocks  module-level constant tables. routes/hawkeye.py holds six
                    invented institutional buyers this way.
  demo_markers      mock / stub / placeholder / fallback / TODO / hardcoded.

A wired route with no logic import is HOLLOW, and HOLLOW is reported
separately from WIRED because the fix is completely different: a hollow route
does not need connecting, it needs a body.

WHAT THIS IS NOT. Reachable does not mean correct, wired does not mean
working, and substance does not mean right. This measures whether a path
exists from a user to code that computes something -- never whether the
computation is correct. A module can score 0.95 here and still be wrong.

PROVENANCE. Weights are HAND_SET -- they encode a judgment about what blocks a
module reaching production, not a measurement. Reachability, endpoint counts,
blueprint registration, and frontend calls are read from source and are exact.
Component matching is by NAME OVERLAP and will produce false pairs; it is
reported separately and never drives a verdict on its own.
"""
from __future__ import annotations

import pathlib
import re
from collections import defaultdict, deque
from typing import Any

BACKEND = pathlib.Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
FRONTEND = REPO / "frontend-v2" / "src"

LAYERS = ("routes", "services", "engines", "agents")

# HAND_SET. Reachability dominates because an unreachable module is absent
# from the product at any level of quality. Wiring is next because a module
# nothing calls is also absent, just recoverably so.
WEIGHTS = {
    "reachable": 0.30,
    "is_wired": 0.25,
    "has_substance": 0.25,
    "has_surface": 0.05,
    "has_tests": 0.15,
}

# Words that mark a route as standing in for work rather than doing it.
DEMO_MARKERS = re.compile(
    r"\b(mock|stub|placeholder|fallback|dummy|sample_data|hardcoded|"
    r"TODO|FIXME|not_implemented|NotImplemented)\b", re.I)

# Module-level constant tables -- data written into the route rather than
# computed or fetched. BUYER_UNIVERSE in routes/hawkeye.py is the archetype.
HARDCODED_BLOCK = re.compile(r"^[A-Z][A-Z0-9_]{3,}\s*=\s*[\[{]", re.M)

# Nothing is ever certain. Matches the posture of success_predictor's ceiling.
CEILING = 0.95

WEIGHTS_PROVENANCE = "HAND_SET"

VERDICTS = ("WIRED", "HOLLOW", "WIRE", "BUILD_FRONTEND", "REACHABLE_UNUSED",
            "UNREACHABLE", "REBUILD")

# A route needs enough surface to be worth wiring rather than rebuilding.
MIN_ENDPOINTS_TO_WIRE = 3


class PlatformReadinessError(RuntimeError):
    """Raised when the repository cannot be read."""


def _read(p: pathlib.Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


def _blueprint_prefixes() -> dict[str, str]:
    """Blueprint variable -> url prefix, as actually registered in app.py."""
    app = BACKEND / "app.py"
    if not app.exists():
        raise PlatformReadinessError(f"cannot find {app}")
    src = _read(app)
    return {
        m.group(1): (m.group(2) if m.group(2) is not None else "")
        for m in re.finditer(
            r"register_blueprint\(\s*(\w+)\s*"
            r"(?:,\s*url_prefix\s*=\s*[\"']([^\"']*)[\"'])?", src)
    }


def _modules() -> dict[str, dict[str, Any]]:
    """Every backend module, keyed 'layer/stem'."""
    prefixes = _blueprint_prefixes()
    out: dict[str, dict[str, Any]] = {}
    for layer in LAYERS:
        d = BACKEND / layer
        if not d.exists():
            continue
        for f in sorted(d.glob("*.py")):
            if f.name == "__init__.py":
                continue
            src = _read(f)
            bp = prefix = None
            registered = False
            if layer == "routes":
                m = re.search(r"(\w+)\s*=\s*Blueprint\(", src)
                bp = m.group(1) if m else None
                registered = bool(bp and bp in prefixes)
                prefix = prefixes.get(bp) if bp else None
            out[f"{layer}/{f.stem}"] = {
                "key": f"{layer}/{f.stem}",
                "layer": layer,
                "name": f.stem,
                "blueprint": bp,
                "prefix": prefix,
                "registered": registered,
                # Both decorator styles. Counting only @bp.route() scores every
                # blueprint using @bp.get/@bp.post as zero-endpoint, which once
                # marked auth and preflight for deletion.
                "endpoints": len(re.findall(
                    r"@\w+\.(?:route|get|post|put|patch|delete)\(", src)),
                "lines": len(src.splitlines()),
                "imports": {f"{a}/{b}" for a, b in re.findall(
                    r"from\s+(services|engines|agents)\.(\w+)", src)},
                "demo_markers": len(DEMO_MARKERS.findall(src)),
                "hardcoded_blocks": len(HARDCODED_BLOCK.findall(src)),
            }
    return out


def reachable_from_routes(mods: dict[str, dict]) -> set[str]:
    """
    Everything a registered blueprint can reach, following imports transitively.

    Entry points are registered blueprints only. An unregistered route file is
    itself unreachable, and so is anything only it imports -- which is correct:
    if nothing registers the route, no request ever arrives.
    """
    seen: set[str] = set()
    q = deque(k for k, m in mods.items()
              if m["layer"] == "routes" and m["registered"])
    while q:
        cur = q.popleft()
        if cur in seen:
            continue
        seen.add(cur)
        for nxt in mods.get(cur, {}).get("imports", ()):
            if nxt in mods and nxt not in seen:
                q.append(nxt)
    return seen


def _frontend_calls() -> dict[str, set[str]]:
    """API prefix -> components that call it."""
    calls: dict[str, set[str]] = defaultdict(set)
    if not FRONTEND.exists():
        return calls
    for f in list(FRONTEND.rglob("*.tsx")) + list(FRONTEND.rglob("*.ts")):
        for m in re.finditer(r"[\"'`](/api/[a-zA-Z0-9\-_/${}.]+)", _read(f)):
            parts = [p for p in m.group(1).split("/") if p and p != "api"]
            if parts:
                calls[f"/api/{parts[0]}"].add(f.name)
    return calls


def _tested() -> tuple[set[str], set[str]]:
    """(api prefixes hit by tests, modules imported by tests)."""
    prefixes: set[str] = set()
    mods: set[str] = set()
    d = BACKEND / "tests"
    if not d.exists():
        return prefixes, mods
    for f in d.glob("*.py"):
        src = _read(f)
        prefixes |= set(re.findall(r"[\"'](/api/[a-z0-9\-_/]+)", src))
        mods |= {f"{a}/{b}" for a, b in
                 re.findall(r"from\s+(services|engines|agents)\.(\w+)", src)}
    return prefixes, mods


def _tokens(s: str) -> set[str]:
    s = re.sub(r"[^a-zA-Z]", " ", s)
    s = re.sub(r"(?<!^)(?=[A-Z])", " ", s)
    return {t.lower() for t in s.split() if len(t) > 3}


def score_module(m: dict) -> dict:
    """Probability this module reaches a user, and the cheapest path there."""
    factors = {
        "reachable": 1.0 if m["reachable"] else 0.0,
        "is_wired": 1.0 if m["wired_by"] else 0.0,
        "has_substance": 1.0 if m.get("has_substance") else 0.0,
        "has_surface": 1.0 if m["components"] else 0.0,
        "has_tests": 1.0 if m["tested"] else 0.0,
    }
    weakest = min(factors.values())
    average = (sum(WEIGHTS[k] * v for k, v in factors.items())
               / sum(WEIGHTS.values()))
    # Floor the inputs so a single zero does not collapse the score to zero --
    # same correction success_predictor needed. A module with one missing
    # factor is badly placed, not impossible.
    probability = CEILING * (max(weakest, 0.05) ** 0.5) * (max(average, 0.05) ** 0.5)

    if not m["reachable"]:
        verdict = "UNREACHABLE"
        why = ("no registered route imports it — absent from the product at "
               "any level of quality. Give it a route or delete it.")
    elif m["layer"] == "routes" and m["endpoints"] == 0:
        verdict, why = "REBUILD", "registered but exposes nothing"
    elif m["wired_by"] and not m.get("has_substance"):
        verdict = "HOLLOW"
        why = ("wired end to end but computes nothing — imports no service, "
               "engine or agent, so it returns data written in the route "
               "file. Needs a body, not a connection.")
    elif m["wired_by"]:
        verdict, why = "WIRED", "the product calls it and it calls real logic"
    elif m["layer"] != "routes":
        verdict = "REACHABLE_UNUSED"
        why = "reachable, but the route reaching it has no frontend"
    elif m["components"] and m["endpoints"] >= MIN_ENDPOINTS_TO_WIRE:
        verdict, why = "WIRE", "both halves exist; connect them"
    elif m["endpoints"] >= MIN_ENDPOINTS_TO_WIRE:
        verdict, why = "BUILD_FRONTEND", "backend is real, no surface exists"
    else:
        verdict, why = "REBUILD", "too thin to wire"

    return {**m, "factors": factors, "probability": round(probability, 3),
            "verdict": verdict, "why": why}


def scan() -> dict:
    """Score every backend module. The whole engine in one call."""
    mods = _modules()
    if not mods:
        raise PlatformReadinessError("no backend modules found")

    reach = reachable_from_routes(mods)
    calls = _frontend_calls()
    components = ([p.name for p in FRONTEND.rglob("*.tsx")]
                  if FRONTEND.exists() else [])
    test_prefixes, test_mods = _tested()

    scored: list[dict] = []
    for key, m in mods.items():
        m["reachable"] = key in reach
        # A route with no logic import computes nothing. Non-route layers are
        # themselves the logic, so substance is not in question for them.
        m["imports_logic"] = bool(m["imports"])
        m["has_substance"] = (m["imports_logic"] if m["layer"] == "routes"
                              else True)
        m["wired_by"] = (sorted(calls.get(m["prefix"], set()))
                         if m["prefix"] else [])
        tk = _tokens(m["name"])
        m["components"] = sorted(c for c in components if tk and tk & _tokens(c))
        m["tested"] = key in test_mods or bool(
            m["prefix"] and any(p.startswith(m["prefix"])
                                for p in test_prefixes))
        m.pop("imports", None)
        scored.append(score_module(m))

    scored.sort(key=lambda x: (x["layer"], x["verdict"], -x["probability"]))

    by_verdict: dict[str, int] = defaultdict(int)
    by_layer: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for s in scored:
        by_verdict[s["verdict"]] += 1
        by_layer[s["layer"]][s["verdict"]] += 1

    # Redundancy: one prefix served by several route modules.
    prefix_owners: dict[str, list[str]] = defaultdict(list)
    for s in scored:
        if s["layer"] == "routes" and s["prefix"]:
            prefix_owners[s["prefix"]].append(s["name"])

    routes = [s for s in scored if s["layer"] == "routes"]
    return {
        "modules": scored,
        "totals": {
            "modules": len(scored),
            "reachable": len(reach),
            "unreachable": len(scored) - len(reach),
            "pct_reachable": round(len(reach) / len(scored), 4),
            "route_modules": len(routes),
            "routes_wired": sum(1 for r in routes if r["wired_by"]),
            "frontend_components": len(set(components)),
            "api_prefixes_called": len(calls),
        },
        "by_verdict": dict(by_verdict),
        "by_layer": {k: dict(v) for k, v in by_layer.items()},
        "redundant_prefixes": {k: v for k, v in prefix_owners.items()
                               if len(v) > 1},
        "provenance": {
            "weights": WEIGHTS,
            "weights_provenance": WEIGHTS_PROVENANCE,
            "exact": ["reachable", "endpoints", "registered", "wired_by",
                      "tested"],
            "approximate": ["components — matched by name overlap, produces "
                            "false pairs, never drives a verdict alone"],
        },
        "scope_note": (
            "Reachable does not mean correct and wired does not mean working. "
            "This measures whether a path exists from a user to the code, not "
            "whether the code is right."
        ),
    }


def by_verdict(verdict: str) -> list[dict]:
    """Every module with a given verdict, worst first."""
    if verdict not in VERDICTS:
        raise PlatformReadinessError(
            f"unknown verdict {verdict!r}; expected one of "
            f"{', '.join(VERDICTS)}")
    return [m for m in scan()["modules"] if m["verdict"] == verdict]
