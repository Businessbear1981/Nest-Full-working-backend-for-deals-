"""
NEST Gate Fee Routes — pay-on-delivery fee ledger, callable over HTTP.

Exposes services/gate_fee_engine.py so a client-facing ledger can be built,
advanced, and read without any frontend.
"""
from datetime import datetime

from flask import Blueprint, jsonify, request

from services.gate_fee_engine import GateFeeError, gate_fee_engine
from services.pom_engine import (
    COUNSEL_RESERVED, DEFAULT_COMMENT_CYCLES, DEFAULT_DRAFTING_MODEL,
    DRAFTING_MODELS, POM_SECTIONS, POMError, compare_drafting_models, plan_pom,
)

gate_fees_bp = Blueprint("gate_fees", __name__)


def _ok(data, code=200):
    return jsonify({"success": True, "data": data, "error": None,
                    "timestamp": datetime.utcnow().isoformat()}), code


def _err(msg, code=400):
    return jsonify({"success": False, "data": None, "error": msg,
                    "timestamp": datetime.utcnow().isoformat()}), code


@gate_fees_bp.route("/ledger", methods=["POST"])
def build_ledger():
    """
    Build a pay-on-delivery fee ledger for one bond series.

    Body: {"series_name": "2027A", "par": 10000000,
           "development_fee_bp": 45, "placement_fee_bp": 75?,
           "placement_licensed": false?, "development_fee_floor": 0?,
           "development_fee_cap": null?}
    """
    body = request.get_json() or {}
    series_name = (body.get("series_name") or "").strip()
    if not series_name:
        return _err("series_name is required", 400)

    try:
        par = float(body.get("par", 0))
        dev_bp = float(body.get("development_fee_bp", 0))
        plc_bp = float(body.get("placement_fee_bp", 0))
        floor = float(body.get("development_fee_floor", 0))
        cap = body.get("development_fee_cap")
        cap = float(cap) if cap is not None else None
    except (TypeError, ValueError):
        return _err("par and fee rates must be numeric", 400)

    if dev_bp <= 0:
        return _err("development_fee_bp must be positive", 400)

    try:
        ledger = gate_fee_engine.build_ledger(
            series_name=series_name,
            par=par,
            development_fee_bp=dev_bp,
            placement_fee_bp=plc_bp,
            placement_licensed=bool(body.get("placement_licensed", False)),
            development_fee_floor=floor,
            development_fee_cap=cap,
        )
    except GateFeeError as exc:
        return _err(str(exc), 400)

    return _ok(ledger)


@gate_fees_bp.route("/advance", methods=["POST"])
def advance_gate():
    """
    Move one gate forward.

    Body: {"ledger": {...}, "gate_id": "g2_capital_stack", "status": "accepted"}

    The ledger is passed in and returned rather than stored, so this works
    against whatever persistence the caller already has. Invalid transitions
    (paying an unaccepted gate, advancing a placement gate while unlicensed)
    are rejected rather than silently allowed.
    """
    body = request.get_json() or {}
    ledger = body.get("ledger")
    if not isinstance(ledger, dict) or "gates" not in ledger:
        return _err("ledger is required and must be a ledger object", 400)

    gate_id = (body.get("gate_id") or "").strip()
    status = (body.get("status") or "").strip()
    if not gate_id or not status:
        return _err("gate_id and status are both required", 400)

    try:
        updated = gate_fee_engine.advance_gate(ledger, gate_id, status)
    except GateFeeError as exc:
        return _err(str(exc), 400)

    return _ok(updated)


@gate_fees_bp.route("/client-view", methods=["POST"])
def client_view():
    """
    The client-facing answer to "where is my deal and what am I paying for?"

    Body: {"ledger": {...}}
    """
    body = request.get_json() or {}
    ledger = body.get("ledger")
    if not isinstance(ledger, dict) or "gates" not in ledger:
        return _err("ledger is required and must be a ledger object", 400)
    return _ok(gate_fee_engine.client_view(ledger))


@gate_fees_bp.route("/program-rollup", methods=["POST"])
def program_rollup():
    """
    Aggregate several series ledgers into one program view.

    Body: {"ledgers": [{...}, {...}]}
    """
    body = request.get_json() or {}
    ledgers = body.get("ledgers")
    if not isinstance(ledgers, list):
        return _err("ledgers must be a list of ledger objects", 400)
    return _ok(gate_fee_engine.program_rollup(ledgers))


@gate_fees_bp.route("/gates", methods=["GET"])
def list_gates():
    """The gate catalogue itself -- what each gate is and what it buys."""
    from services.gate_fee_engine import DEVELOPMENT_GATES, PLACEMENT_GATES
    return _ok({
        "development_gates": DEVELOPMENT_GATES,
        "placement_gates": PLACEMENT_GATES,
        "note": ("Development gates are chargeable pre-license. Placement "
                 "gates are transaction-based and require an effective "
                 "placement agent registration."),
    })


@gate_fees_bp.route("/terminate", methods=["POST"])
def terminate():
    """
    Terminate an engagement and compute the refund due.

    Body: {"ledger": {...}, "reason": "..."}

    A gate paid but never accepted is refunded in full. A gate delivered and
    accepted is earned -- the client holds the work product either way.
    """
    body = request.get_json() or {}
    ledger = body.get("ledger")
    if not isinstance(ledger, dict) or "gates" not in ledger:
        return _err("ledger is required and must be a ledger object", 400)
    return _ok(gate_fee_engine.terminate(ledger, reason=body.get("reason", "")))


@gate_fees_bp.route("/predict", methods=["POST"])
def predict():
    """
    Success prediction for a deal: probability of close, the stall point, and
    the critical-path items driving it.

    Body: {"deal": {...project parameters...}}
    """
    body = request.get_json() or {}
    deal = body.get("deal")
    if not isinstance(deal, dict):
        return _err("deal is required and must be an object", 400)
    from services.success_predictor import predict_success
    return _ok(predict_success(deal))


@gate_fees_bp.route("/optimize", methods=["POST"])
def optimize():
    """
    Optimize the fee mix, using real predicted stall risk when a deal is given.

    Body: {"par": 55000000, "years_to_close": 1.5,
           "licensed_by_close": false, "client_cost_ceiling_bp": 362.5,
           "deal": {...}?, "equity_available": false?,
           "program_terminal_value": 0?, "years_to_realization": 12?}
    """
    body = request.get_json() or {}
    try:
        par = float(body.get("par", 0))
        ceiling = float(body.get("client_cost_ceiling_bp", 0))
        years = float(body.get("years_to_close", 2.0))
    except (TypeError, ValueError):
        return _err("par, client_cost_ceiling_bp and years_to_close must be numeric", 400)

    from services.engagement_economics import optimize_engagement
    result = optimize_engagement(
        par=par,
        years_to_close=years,
        licensed_by_close=bool(body.get("licensed_by_close", False)),
        client_cost_ceiling_bp=ceiling,
        equity_available=bool(body.get("equity_available", False)),
        program_terminal_value=float(body.get("program_terminal_value", 0) or 0),
        years_to_realization=float(body.get("years_to_realization", 12) or 12),
        deal=body.get("deal"),
    )
    if "error" in result:
        return _err(result["error"], 400)
    return _ok(result)


@gate_fees_bp.route("/readiness/checklist", methods=["GET"])
def readiness_catalogue():
    """The full 272-item Project Readiness Checklist, for an intake form."""
    from services.readiness_checklist import checklist_catalogue
    return _ok(checklist_catalogue())


@gate_fees_bp.route("/readiness/score", methods=["POST"])
def readiness_score():
    """
    Score a submission set. Body: {"submissions": {"1.1.1": "available", ...}}

    Item values may be a bare status string or
    {"status": "not_applicable", "justification": "..."}. N/A without a
    justification is counted as incomplete, not excluded.
    """
    body = request.get_json() or {}
    subs = body.get("submissions")
    if not isinstance(subs, dict):
        return _err("submissions is required and must be an object", 400)
    from services.readiness_checklist import score_readiness
    return _ok(score_readiness(subs))


@gate_fees_bp.route("/readiness/intake", methods=["POST"])
def readiness_intake():
    """
    Full intake: score the checklist, derive deal parameters from the evidence,
    and predict success off the same evidence.

    Body: {"submissions": {...}, "deal_overrides": {...}?}
    """
    body = request.get_json() or {}
    subs = body.get("submissions")
    if not isinstance(subs, dict):
        return _err("submissions is required and must be an object", 400)
    overrides = body.get("deal_overrides")
    if overrides is not None and not isinstance(overrides, dict):
        return _err("deal_overrides must be an object", 400)
    from services.readiness_checklist import intake
    return _ok(intake(subs, deal_overrides=overrides))


@gate_fees_bp.route("/preflight", methods=["POST"])
def preflight():
    """
    Structural viability: assuming the checklist is complete, what still kills
    this deal? Returns NO_GO / RESTRUCTURE / PROCEED_WITH_CONDITIONS / PROCEED.

    Body: {"deal": {...}}
    """
    body = request.get_json() or {}
    deal = body.get("deal")
    if not isinstance(deal, dict):
        return _err("deal is required and must be an object", 400)
    from services.preflight import run_preflight
    return _ok(run_preflight(deal))


@gate_fees_bp.route("/flow", methods=["POST"])
def flow():
    """
    Full front-of-engagement chain: readiness -> preflight -> prediction ->
    fee optimization -> ledger, with a single recommended action.

    Body: {"submissions": {...}?, "deal": {...}?, "series_name": "...",
           "par": 55000000, "client_cost_ceiling_bp": 362.5,
           "program_architecture_fee": 0?, "licensed_by_close": false?}
    """
    body = request.get_json() or {}
    from services.deal_preflight_flow import run_flow
    try:
        return _ok(run_flow(
            submissions=body.get("submissions") or {},
            deal=body.get("deal") or {},
            series_name=body.get("series_name", "Series"),
            par=float(body.get("par", 0) or 0),
            client_cost_ceiling_bp=float(body.get("client_cost_ceiling_bp", 362.5)),
            development_fee_bp=(float(body["development_fee_bp"])
                                if body.get("development_fee_bp") else None),
            program_architecture_fee=float(body.get("program_architecture_fee", 0) or 0),
            licensed_by_close=bool(body.get("licensed_by_close", False)),
            years_to_close=float(body.get("years_to_close", 2.0)),
        ))
    except (TypeError, ValueError) as exc:
        return _err(f"Invalid input: {exc}", 400)


@gate_fees_bp.route("/stairway", methods=["POST"])
def stairway():
    """
    "Stairway to Heaven" -- the pathway from not-financeable to financeable.

    Body: {"deal": {...}}

    Returns ordered remediation steps with owner, cost range, duration, what
    each unlocks, a feasibility score, and a client-facing turndown brief.
    """
    body = request.get_json() or {}
    deal = body.get("deal")
    if not isinstance(deal, dict):
        return _err("deal is required and must be an object", 400)
    from services.stairway import build_pathway
    return _ok(build_pathway(deal))


@gate_fees_bp.route("/stairway/full", methods=["POST"])
def stairway_full_route():
    """Preflight + remediation pathway + alternative structures.

    Body: {"deal": {...}}
    """
    body = request.get_json() or {}
    deal = body.get("deal")
    if not isinstance(deal, dict):
        return _err("deal is required and must be an object", 400)
    from services.stairway import stairway_full
    return _ok(stairway_full(deal))


# --- POM engine: what the offering document actually costs NEST to produce.

@gate_fees_bp.route("/pom/plan", methods=["POST"])
def pom_plan():
    """
    Derive NEST's POM hours from the engagement structure and the deal.

    Body: {"deal": {...}?, "drafting_model": "market_standard"?,
           "comment_cycles": 4?}
    """
    body = request.get_json() or {}
    try:
        return _ok(plan_pom(
            body.get("deal") or {},
            drafting_model=body.get("drafting_model", DEFAULT_DRAFTING_MODEL),
            comment_cycles=int(body.get("comment_cycles",
                                        DEFAULT_COMMENT_CYCLES)),
        ))
    except (POMError, TypeError, ValueError) as e:
        return _err(str(e), 400)


@gate_fees_bp.route("/pom/compare", methods=["POST"])
def pom_compare():
    """
    Price the same offering document under all three drafting models.

    Body: {"deal": {...}?, "comment_cycles": 4?}
    """
    body = request.get_json() or {}
    try:
        return _ok(compare_drafting_models(
            body.get("deal") or {},
            comment_cycles=int(body.get("comment_cycles",
                                        DEFAULT_COMMENT_CYCLES)),
        ))
    except (POMError, TypeError, ValueError) as e:
        return _err(str(e), 400)


@gate_fees_bp.route("/pom/sections", methods=["GET"])
def pom_sections():
    """The canonical POM section list, with owners and hour estimates."""
    return _ok({"sections": POM_SECTIONS,
                "drafting_models": list(DRAFTING_MODELS),
                "counsel_reserved": sorted(COUNSEL_RESERVED)})
