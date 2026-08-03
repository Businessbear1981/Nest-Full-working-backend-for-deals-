"""
NEST Deal Preflight Flow — one call, intake to fee ledger.

Chains the whole front of the engagement in the order a real desk works it:

  1. READINESS   Score the 272-item checklist. Can the engagement even begin?
  2. PREFLIGHT   Assuming perfect paperwork, does the credit work? This runs
                 REGARDLESS of readiness -- that ordering is deliberate. A
                 structurally unfinanceable deal should be identified in week
                 one, before the sponsor spends months assembling documents
                 for a financing that was never going to sell.
  3. PREDICT     Where does it stall, and what is driving that?
  4. OPTIMIZE    Given the real stall risk, what fee mix actually works?
  5. LEDGER      The pay-on-delivery ledger the client sees.

The recommendation is deliberately conservative about proceeding: a NO_GO
from preflight overrides a clean checklist, because documents do not fix a
credit that does not cover.
"""
from __future__ import annotations

from typing import Any


def run_flow(
    *,
    submissions: dict | None = None,
    deal: dict | None = None,
    series_name: str = "Series",
    par: float = 0.0,
    client_cost_ceiling_bp: float = 362.5,
    development_fee_bp: float | None = None,
    program_architecture_fee: float = 0.0,
    licensed_by_close: bool = False,
    years_to_close: float = 2.0,
) -> dict:
    """Run the full front-of-engagement chain and return every stage."""
    from services.readiness_checklist import intake as readiness_intake
    from services.preflight import run_preflight
    from services.engagement_economics import optimize_engagement
    from services.gate_fee_engine import gate_fee_engine

    deal = dict(deal or {})

    # 1 + 3 -- readiness scoring derives parameters and predicts.
    intake_result = readiness_intake(submissions or {}, deal_overrides=deal)
    readiness = intake_result["readiness"]
    prediction = intake_result["prediction"]

    # 2 -- structural viability, independent of paperwork.
    pre = run_preflight({**intake_result["parameters_used"], **deal})

    # 4 -- fee optimization driven by the real prediction.
    optimization = None
    if par > 0:
        optimization = optimize_engagement(
            par=par, years_to_close=years_to_close,
            licensed_by_close=licensed_by_close,
            client_cost_ceiling_bp=client_cost_ceiling_bp,
            deal=intake_result["parameters_used"],
        )

    # 5 -- the ledger the client actually sees.
    ledger = None
    if par > 0:
        dev_bp = development_fee_bp
        if dev_bp is None and optimization and "recommended" in optimization:
            dev_bp = optimization["recommended"]["development_fee_bp"]
        if dev_bp:
            ledger = gate_fee_engine.build_ledger(
                series_name=series_name, par=par,
                development_fee_bp=dev_bp,
                placement_fee_bp=(client_cost_ceiling_bp - dev_bp),
                placement_licensed=licensed_by_close,
                program_architecture_fee=program_architecture_fee,
            )

    # --- Recommendation. Preflight NO_GO beats everything else.
    if pre["walk_away_signal"]:
        action = "WALK"
        rationale = (
            "Preflight returned NO_GO. " + pre["headline"] + " This is not a "
            "diligence gap -- completing the checklist does not change it. "
            "Declining now is the correct outcome and costs the client "
            "nothing further."
        )
    elif pre["verdict"] == "RESTRUCTURE":
        action = "ENGAGE_TO_RESTRUCTURE"
        rationale = (
            f"{pre['counts']['structural']} structural change(s) required "
            "before this can go to market. That work is exactly what the "
            "development gates are for, and it should be scoped explicitly "
            "in the engagement rather than discovered at the rating gate."
        )
    elif not readiness["move_forward_memorandum"]["issues"]:
        action = "ENGAGE_AT_GATE_1_ONLY"
        rationale = (
            f"Structurally financeable, but readiness is "
            f"{readiness['readiness_pct']}% against an 80% threshold. Take "
            "Gate 1 only; the Move Forward Memorandum does not issue and the "
            "Gate 1 fee stays refundable until it does."
        )
    else:
        action = "ENGAGE"
        rationale = (
            f"Readiness {readiness['readiness_pct']}% clears the threshold and "
            "preflight found no structural blocker. Proceed through the gates."
        )

    return {
        "series_name": series_name,
        "recommended_action": action,
        "rationale": rationale,
        "stage_1_readiness": {
            "score_pct": readiness["readiness_pct"],
            "rag": readiness["rag"],
            "board": readiness["board"],
            "move_forward_issues": readiness["move_forward_memorandum"]["issues"],
            "gap_count": readiness["gap_count"],
        },
        "stage_2_preflight": {
            "verdict": pre["verdict"],
            "walk_away_signal": pre["walk_away_signal"],
            "headline": pre["headline"],
            "counts": pre["counts"],
            "no_go": pre["no_go"],
            "structural": pre["structural"],
            "watch": pre["watch"],
            "cannot_assess": pre["cannot_assess"],
        },
        "stage_3_prediction": {
            "probability_as_is": prediction["probability_of_close_as_is"],
            "probability_if_procured": prediction["probability_if_procured"],
            "headline": prediction["headline"],
            "stall_point": prediction["stall_point"]["gate_id"],
            "critical_path": prediction["critical_path_items"],
        },
        "stage_4_optimization": optimization and {
            "recommended": optimization["recommended"],
            "rationale": optimization["rationale"],
        },
        "stage_5_ledger": ledger and {
            "upfront_due": ledger["upfront_due"],
            "program_architecture_fee": ledger["program_architecture_fee"],
            "development_pool": ledger["fee_pools"]["development"],
            "gates": [
                {"seq": g["seq"], "name": g["name"], "silo": g["silo"],
                 "amount": g["amount"], "fee_class": g["fee_class"],
                 "status": g["status"]}
                for g in sorted(ledger["gates"], key=lambda x: x["seq"])
            ],
        },
    }
