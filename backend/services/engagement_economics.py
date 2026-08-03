"""
NEST Engagement Economics — value and optimize the whole compensation stack.

An arrangement engagement pays NEST through four channels that behave nothing
alike:

  1. GATED DEVELOPMENT FEES  near-certain, paid within months of the work.
  2. SUCCESS FEE             large, but years out, contingent on close, and
                             unavailable to an unlicensed advisor.
  3. EQUITY (profits interest)  largest headline number, most remote cash,
                             and the only channel that can cost money before
                             it pays anything (see phantom tax below).
  4. ADMINISTRATION          small annual, very long duration, low risk.

Comparing them on face value is the mistake this module exists to prevent.
A $12M success fee eight years out at 60% probability is not worth more than
$4M of gated fees collected as the work lands. Everything here is reduced to
a risk-adjusted present value so the mix can actually be compared and traded.

PHANTOM TAX -- the non-obvious one. A profits interest under Rev. Proc. 93-27
with a Rev. Proc. 2001-43 election makes the holder report its distributive
share of entity income whether or not any cash is distributed. In a leveraged
development SPV that recycles residual equity into the next phase, allocated
income and distributed cash diverge for years. Without a mandatory tax
distribution the holder owes real cash tax on paper income. `value_equity`
models that as a negative cash flow, because it is one.

Nothing here asserts a market rate. Discount rates, probabilities and exit
assumptions are caller-supplied inputs with documented defaults, and every
result reports the assumptions it used.
"""
from __future__ import annotations

from typing import Any

# Defaults are stated, not hidden. They are starting assumptions for modeling,
# not market data, and every output echoes back what was used.
DEFAULT_DISCOUNT_RATE = 0.12      # advisory-firm cost of capital, illiquid
DEFAULT_GATE_PROBABILITY = 0.92   # a gate already engaged usually delivers
DEFAULT_CLOSE_PROBABILITY = 0.60  # bond-ready -> priced and closed
DEFAULT_TAX_RATE = 0.40           # combined federal + state on allocated income


def _pv(amount: float, years: float, rate: float) -> float:
    """Present value of a single cash flow."""
    if years <= 0:
        return amount
    return amount / ((1.0 + rate) ** years)


def value_gated_fees(
    ledger: dict,
    *,
    discount_rate: float = DEFAULT_DISCOUNT_RATE,
    gate_probability: float = DEFAULT_GATE_PROBABILITY,
    months_per_gate: float = 3.0,
) -> dict:
    """
    Risk-adjusted PV of a gate ledger from services/gate_fee_engine.py.

    Gates already paid are worth face -- no discount, no probability haircut,
    the money is in. That asymmetry is the entire argument for the pay-on-
    delivery model and it should show up in the numbers.
    """
    # Development gates only. Placement gates are valued by
    # value_success_fee() -- counting them here too would double-count the
    # success fee into the "near-certain, collected early" bucket and make
    # every optimization prefer whichever mix put more dollars in placement.
    gates = [g for g in ledger.get("gates", [])
             if g.get("fee_class", "development") == "development"]
    if not gates:
        return {"pv": 0.0, "face": 0.0, "note": "No development gates on this ledger."}

    banked = 0.0
    at_risk_face = 0.0
    pv = 0.0
    for g in sorted(gates, key=lambda x: x.get("seq", 0)):
        amt = float(g.get("amount") or 0)
        if g.get("status") == "paid":
            banked += amt
            pv += amt
            continue
        if g.get("status") == "waived":
            continue
        at_risk_face += amt
        years = (g.get("seq", 1) * months_per_gate) / 12.0
        # Each successive gate compounds the risk of the ones before it.
        cumulative_p = gate_probability ** g.get("seq", 1)
        pv += _pv(amt * cumulative_p, years, discount_rate)

    return {
        "pv": round(pv, 2),
        "face": round(banked + at_risk_face, 2),
        "banked": round(banked, 2),
        "at_risk_face": round(at_risk_face, 2),
        "assumptions": {
            "discount_rate": discount_rate,
            "gate_probability": gate_probability,
            "months_per_gate": months_per_gate,
        },
    }


def value_success_fee(
    *,
    par: float,
    fee_bp: float,
    years_to_close: float,
    close_probability: float = DEFAULT_CLOSE_PROBABILITY,
    discount_rate: float = DEFAULT_DISCOUNT_RATE,
    licensed_by_close: bool = True,
) -> dict:
    """
    Risk-adjusted PV of a success fee earned at closing.

    If NEST is not licensed by close the fee is not collectable at all --
    returned as zero with the reason stated, not quietly discounted.
    """
    face = par * fee_bp / 10_000
    if not licensed_by_close:
        return {
            "pv": 0.0, "face": round(face, 2), "collectable": False,
            "note": ("Success fee is transaction-based compensation and is not "
                     "collectable without an effective placement agent "
                     "registration at closing."),
        }
    pv = _pv(face * close_probability, years_to_close, discount_rate)
    return {
        "pv": round(pv, 2),
        "face": round(face, 2),
        "collectable": True,
        "assumptions": {
            "fee_bp": fee_bp,
            "years_to_close": years_to_close,
            "close_probability": close_probability,
            "discount_rate": discount_rate,
        },
    }


def value_equity(
    *,
    interest_pct: float,
    program_terminal_value: float,
    years_to_realization: float,
    realization_probability: float = 0.50,
    discount_rate: float = DEFAULT_DISCOUNT_RATE,
    annual_allocated_income: float = 0.0,
    years_of_phantom_income: float = 0.0,
    tax_rate: float = DEFAULT_TAX_RATE,
    tax_distribution_provision: bool = False,
) -> dict:
    """
    Risk-adjusted PV of a profits interest, net of phantom tax.

    `program_terminal_value` is the equity value at realization (REIT
    placement, phase sale, refinancing), NOT program cost. A profits interest
    participates only in appreciation after grant, so passing gross project
    cost here materially overstates the result.

    If `tax_distribution_provision` is False, allocated income creates a real
    negative cash flow: tax owed on income never received. That is the single
    most commonly missed term in these grants.
    """
    upside_face = program_terminal_value * (interest_pct / 100.0)
    upside_pv = _pv(upside_face * realization_probability,
                    years_to_realization, discount_rate)

    phantom_pv = 0.0
    if not tax_distribution_provision and annual_allocated_income and years_of_phantom_income:
        annual_tax = annual_allocated_income * (interest_pct / 100.0) * tax_rate
        for y in range(1, int(years_of_phantom_income) + 1):
            phantom_pv += _pv(annual_tax, y, discount_rate)

    return {
        "pv": round(upside_pv - phantom_pv, 2),
        "upside_pv": round(upside_pv, 2),
        "upside_face": round(upside_face, 2),
        "phantom_tax_pv": round(-phantom_pv, 2),
        "tax_distribution_provision": tax_distribution_provision,
        "warning": None if tax_distribution_provision else (
            "No mandatory tax distribution provision. The holder may owe cash "
            "tax on allocated income it never receives. Model shown net of "
            "that cost; the fix is a tax distribution clause senior to the "
            "entity's reinvestment waterfall."
        ),
        "assumptions": {
            "interest_pct": interest_pct,
            "program_terminal_value": program_terminal_value,
            "years_to_realization": years_to_realization,
            "realization_probability": realization_probability,
            "discount_rate": discount_rate,
            "tax_rate": tax_rate,
        },
    }


def value_administration(
    *,
    par: float,
    annual_bp: float,
    years: float,
    start_year: float = 1.0,
    discount_rate: float = DEFAULT_DISCOUNT_RATE,
    probability: float = 0.85,
) -> dict:
    """PV of ongoing administration -- small, long, and reliably underrated."""
    annual = par * annual_bp / 10_000
    pv = sum(_pv(annual * probability, start_year + y, discount_rate)
             for y in range(int(years)))
    return {
        "pv": round(pv, 2),
        "annual": round(annual, 2),
        "face_undiscounted": round(annual * years, 2),
        "assumptions": {"annual_bp": annual_bp, "years": years,
                        "probability": probability,
                        "discount_rate": discount_rate},
    }


def optimize_engagement(
    *,
    par: float,
    years_to_close: float,
    licensed_by_close: bool,
    client_cost_ceiling_bp: float,
    equity_available: bool = False,
    program_terminal_value: float = 0.0,
    years_to_realization: float = 12.0,
    discount_rate: float = DEFAULT_DISCOUNT_RATE,
    close_probability: float = DEFAULT_CLOSE_PROBABILITY,
    candidate_dev_bp: list[float] | None = None,
) -> dict:
    """
    Search the fee mix that maximizes NEST's risk-adjusted PV while keeping
    the client's total cash cost inside `client_cost_ceiling_bp`.

    The optimization is over how much of the total cash budget is taken as
    gated development fees (near-certain, early) versus success fee (large,
    late, contingent). Equity is layered on top when available -- it does not
    consume the client's cash budget, which is exactly why it is attractive to
    the client and why it must be valued honestly rather than at face.

    Returns every candidate, not just the winner, so the tradeoff is visible.
    """
    if par <= 0:
        return {"error": "par must be positive"}
    if client_cost_ceiling_bp <= 0:
        return {"error": "client_cost_ceiling_bp must be positive"}

    candidates = candidate_dev_bp or [10, 20, 30, 45, 60, 80, 100, 125, 150]
    from services.gate_fee_engine import gate_fee_engine

    results = []
    for dev_bp in candidates:
        if dev_bp > client_cost_ceiling_bp:
            continue
        success_bp = client_cost_ceiling_bp - dev_bp

        ledger = gate_fee_engine.build_ledger(
            series_name="optimization_candidate",
            par=par,
            development_fee_bp=dev_bp,
            placement_fee_bp=success_bp,
            placement_licensed=licensed_by_close,
        )
        gated = value_gated_fees(ledger, discount_rate=discount_rate)
        success = value_success_fee(
            par=par, fee_bp=success_bp, years_to_close=years_to_close,
            close_probability=close_probability, discount_rate=discount_rate,
            licensed_by_close=licensed_by_close,
        )

        total_pv = gated["pv"] + success["pv"]
        results.append({
            "development_fee_bp": dev_bp,
            "success_fee_bp": success_bp,
            "gated_pv": gated["pv"],
            "success_pv": success["pv"],
            "total_pv": round(total_pv, 2),
            "client_face_cost": round(par * client_cost_ceiling_bp / 10_000, 2),
            "pre_license_collectable": round(gated["face"], 2),
        })

    if not results:
        return {"error": "No candidate fee split fits inside the cost ceiling."}

    results.sort(key=lambda r: r["total_pv"], reverse=True)
    best = results[0]

    equity = None
    if equity_available and program_terminal_value > 0:
        equity = value_equity(
            interest_pct=1.5,
            program_terminal_value=program_terminal_value,
            years_to_realization=years_to_realization,
            discount_rate=discount_rate,
            tax_distribution_provision=False,
        )

    return {
        "par": par,
        "recommended": best,
        "all_candidates": results,
        "equity_overlay": equity,
        "total_pv_with_equity": round(
            best["total_pv"] + (equity["pv"] if equity else 0.0), 2),
        "rationale": (
            f"At a {client_cost_ceiling_bp}bp total client cost, taking "
            f"{best['development_fee_bp']}bp through delivery gates and "
            f"{best['success_fee_bp']}bp at close maximizes risk-adjusted "
            f"present value. Gated fees are worth more per dollar than success "
            f"fees because they are collected near-certainly and years earlier; "
            f"the ceiling is what stops that logic from pushing everything "
            f"forward into fees the client will not accept."
        ),
        "assumptions": {
            "discount_rate": discount_rate,
            "close_probability": close_probability,
            "years_to_close": years_to_close,
            "licensed_by_close": licensed_by_close,
        },
    }
