"""
Run a deal through every NEST engine and print one consolidated report.

Exists because the chain was being hand-rolled as a throwaway script for every
brief, which meant two briefs written a day apart could quote different
numbers for the same deal. There is now one path.

    python run_deal.py [--deal deal.json] [--json] [--fee-bp 45]

No --deal runs the Horn Lake 2028A reference deal, which doubles as a smoke
test that the engines still behave after a change.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

# The engines live in backend/. Resolve it relative to this file so the script
# runs from any working directory.
REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "backend"))

from services.document_package import build_package          # noqa: E402
from services.gate_fee_engine import gate_fee_engine         # noqa: E402
from services.pom_engine import compare_drafting_models, plan_pom  # noqa: E402
from services.preflight import run_preflight                 # noqa: E402
from services.success_predictor import predict_success       # noqa: E402

# Horn Lake Series 2028A, as it actually stands. Fields that are false are
# false because the thing does not exist yet -- not to make a point.
REFERENCE_DEAL = {
    "name": "73 Holdings — Series 2028A (reference)",
    "par_amount": 92_000_000,
    "sector": "mixed_use",
    "borrower_type": "developer",
    "total_project_cost": 1_405_000_000,
    "total_debt": 1_053_750_000,
    "stabilized_dscr": 1.50,
    "revenue_mechanism": "special_tax",
    "revenue_mechanism_seasoned": False,
    "revenue_contracted_pct": 0,
    "operating_history_years": 0,
    "capitalized_interest_months": 24,
    "revenue_ramp_months": 36,
    "tax_exempt": True,
    "conduit_issuer": None,
    "seeking_rating": True,
    "credit_enhancement": True,
    "capital_stack": True,
    "project_budget": True,
    "site_control": True,
    "org_structure": True,
    "project_description": True,
    "market_data": True,
    "readiness_submissions": True,
    "bond_counsel_engaged": False,
    "feasibility_study": False,
    "audited_financials": False,
    "financial_projections": False,
}

W = 78


def rule(char="="):
    print(char * W)


def head(title):
    print()
    rule()
    print(f"  {title}")
    rule()


def dev_bp(par: float) -> int:
    """Tiered development fee. Rates rise as series shrink -- a $10M series is
    nearly the work of a $55M one. HAND_SET."""
    if par < 25e6:
        return 90
    if par < 50e6:
        return 70
    if par < 75e6:
        return 55
    if par < 150e6:
        return 45
    return 35


def _try(label, fn, *a, **kw):
    """Engines report 'cannot assess' rather than guessing; a hard failure
    should still not kill the whole run."""
    try:
        return fn(*a, **kw)
    except Exception as e:            # noqa: BLE001 - report, don't mask
        print(f"  [{label} unavailable: {type(e).__name__}: {e}]")
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--deal", type=pathlib.Path,
                    help="path to a deal JSON file")
    ap.add_argument("--json", action="store_true",
                    help="emit machine-readable JSON instead of a report")
    ap.add_argument("--fee-bp", type=float, default=None,
                    help="override the tiered development fee basis points")
    args = ap.parse_args()

    if args.deal:
        deal = json.loads(args.deal.read_text(encoding="utf-8"))
    else:
        deal = dict(REFERENCE_DEAL)

    par = float(deal.get("par_amount") or 0)
    bp = args.fee_bp if args.fee_bp is not None else dev_bp(par)

    pre = _try("preflight", run_preflight, deal)
    pred = _try("prediction", predict_success, deal)
    pom = _try("POM", plan_pom, deal)
    models = _try("POM models", compare_drafting_models, deal)
    pkg = _try("document package", build_package, deal)
    ledger = _try("fee ledger", gate_fee_engine.build_ledger,
                  series_name=deal.get("name", "series"),
                  par=par or 1.0, development_fee_bp=bp,
                  placement_fee_bp=275, placement_licensed=False)

    if args.json:
        print(json.dumps({"deal": deal, "preflight": pre, "prediction": pred,
                          "pom": pom, "pom_models": models,
                          "document_package": pkg, "ledger": ledger},
                         indent=1, default=str))
        return 0

    rule()
    print(f"  NEST DEAL RUN — {deal.get('name', 'unnamed deal')}")
    print(f"  par ${par:,.0f}   development fee {bp} bp")
    rule()
    print("  All thresholds HAND_SET or RULE_BASED. Zero MARKET_DERIVED —")
    print("  no closed deals, no verified EMMA filings. Hours are planning")
    print("  estimates, not measured.")

    # ---- Preflight
    if pre:
        head("PREFLIGHT — does the credit work?")
        print(f"  Verdict: {pre.get('verdict')}"
              f"   walk-away signal: {pre.get('walk_away_signal')}")
        print(f"  {pre.get('headline','')}")
        print()
        for key in ("no_go", "structural", "watch"):
            for t in pre.get(key, []):
                print(f"    {t.get('severity','?'):<11}{t.get('code','')}"
                      f"   [{t.get('threshold_provenance','?')}]")
                if t.get("evidence"):
                    print(f"                {t['evidence']}")
        if not any(pre.get(k) for k in ("no_go", "structural", "watch")):
            print("    no traps fired on the data supplied")
        if pre.get("cannot_assess"):
            print(f"    {len(pre['cannot_assess'])} detector(s) could not "
                  f"assess -- inputs missing, not clean")
        print(f"  assessment completeness "
              f"{pre.get('assessment_completeness', 0):.0%}")

    # ---- Prediction
    if pred:
        head("PREDICTION — where does it stall?")
        print(f"  {pred.get('headline','')}")
        print()
        print(f"  as-is {pred.get('probability_of_close_as_is',0):.0%}"
              f"   procured {pred.get('probability_if_procured',0):.0%}")

        stall = pred.get("stall_point") or {}
        if stall:
            print(f"  Stalls at {stall.get('gate_id','?')} "
                  f"({stall.get('probability',0):.0%}), unmet:")
            for u in stall.get("unmet", []):
                print(f"    - {u.get('needs', u.get('parameter',''))}"
                      f"  (impact {u.get('impact',0):.0%})")

        items = pred.get("critical_path_items") or []
        if items:
            print("  Critical path, by how many gates each blocks:")
            for it in items[:5]:
                gates = ", ".join(it.get("blocks_gates", []))
                print(f"    - {it.get('needs', it.get('parameter',''))}")
                print(f"        blocks {gates}")

    # ---- POM
    if pom and models:
        head("POM — the biggest single lift")
        r = pom["readiness"]
        print(f"  {pom['section_count']} sections · "
              f"{r['sections_writable_now']} writable, "
              f"{r['sections_blocked']} blocked ({r['pct_writable']:.0%})")
        print(f"  {'model':<22}{'NEST hours':>12}{'sections drafted':>20}")
        for m, v in models["models"].items():
            print(f"  {m:<22}{v['nest_hours']:>12}"
                  f"{v['sections_drafted_by_nest']:>20}")
        if r["critical_inputs"]:
            print("  Holding it up:")
            for ci in r["critical_inputs"][:4]:
                print(f"    {ci['input']:<30} blocks "
                      f"{ci['blocks_sections']} section(s)")

    # ---- Document package
    if pkg:
        head("DOCUMENT PACKAGE — ten silos")
        print(f"  {'#':<3}{'silo':<28}{'gate':<15}{'docs':>6}{'done':>6}"
              f"{'blkd':>6}  RAG")
        for s in pkg["silos"]:
            print(f"  {s['seq']:<3}{s['name'][:27]:<28}"
                  f"{s['gate_state']:<15}{s['document_count']:>6}"
                  f"{s['documents_complete']:>6}{s['documents_blocked']:>6}"
                  f"  {s['rag']}")
        t = pkg["totals"]
        print(f"  applicable {t['documents']} · complete {t['complete']} "
              f"({t['pct_complete']:.0%}) · excluded as N/A "
              f"{t['excluded_as_inapplicable']}")
        print(f"  Current silo: {pkg['current_silo']}")

    # ---- Fees
    if ledger:
        head("FEE LEDGER — what we are owed, and has it been earned")
        e = ledger["effort"]
        print(f"  development pool  ${ledger['fee_pools']['development']:,.0f}")
        print(f"  hours             {e['development_hours']}"
              f"   (x{e.get('effort_multiplier') or 1:.2f} for par)")
        print(f"  effective rate    ${e['development_effective_hourly']:,.0f}/hr"
              f"   target ${e['target_blended_hourly']:,.0f}")
        if e["development_below_cost"]:
            print(f"  ** BELOW COST ** floor to fix: "
                  f"${e['development_fee_floor_for_cost_recovery']:,.0f}")
        else:
            print("  clears cost recovery")
        print(f"  placement gates locked until licensed: "
              f"${ledger['fee_pools'].get('placement', 0):,.0f}")

    print()
    rule()
    print("  Feed this into a document using the nest-docs skill.")
    print("  Paste the output. Do not transcribe numbers by hand.")
    rule()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
