"""
NEST Gate Fee Routes — pay-on-delivery fee ledger, callable over HTTP.

Exposes services/gate_fee_engine.py so a client-facing ledger can be built,
advanced, and read without any frontend.
"""
from datetime import datetime

from flask import Blueprint, jsonify, request

from services.gate_fee_engine import GateFeeError, gate_fee_engine

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
