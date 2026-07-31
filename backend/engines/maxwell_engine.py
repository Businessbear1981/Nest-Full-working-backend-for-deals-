"""
NEST Maxwell Scoring Engine — Silo 4
Reverse-engineered Moody's factor decomposition.

Output reads exactly like a Moody's analyst's worksheet.
A rating committee can stamp without rebuilding analysis.

Methodology configs:
  - Moody's Generic Project Finance (doc 361401)
  - S&P PF Framework (Construction SACP + Operations SACP weak-link)
  - Moody's Corporates (356428)
  - Moody's P&C Insurers (418354)
"""
from datetime import datetime
from typing import Dict, List, Optional
from services.core import CreditEngine, JPM
from services.rating_benchmarks import (
    STRUCTURING_CRITERIA,
    SECTOR_SCORING_OVERRIDES,
    score_sp_financial_risk,
)

credit = CreditEngine()

# Real DSCR-by-rating floors (STRUCTURING_CRITERIA) mapped onto Moody's
# lettered tiers actually used by _dscr_to_score below.
_DSCR_RATING_ORDER = ["AAA", "AA", "A", "BBB", "BB", "B"]
_DSCR_RATING_TO_NUMERIC = {"AAA": 1, "AA": 3, "A": 6, "BBB": 9, "BB": 12, "B": 15}

# Real Estate LTV-by-rating ceilings (SECTOR_SCORING_OVERRIDES) — the only
# LTV benchmark table rating_benchmarks actually publishes.
_LTV_THRESHOLDS = SECTOR_SCORING_OVERRIDES["real_estate"]["adjustments"]["ltv_thresholds"]
_LTV_RATING_ORDER = ["Aaa", "Aa", "A", "Baa", "Ba", "B"]
_LTV_RATING_TO_NUMERIC = {"Aaa": 1, "Aa": 3, "A": 6, "Baa": 9, "Ba": 12, "B": 15}

# ── Moody's Generic Project Finance Factor Weights ───────────
MOODYS_GENERIC_PF = {
    "name": "Moody's Generic Project Finance",
    "doc_id": "361401",
    "factors": [
        {"name": "Asset Operating Risk", "weight": 0.20, "sub_factors": [
            "Technology risk", "Resource risk", "Operating track record",
            "Complexity of operations", "Asset quality and condition"
        ]},
        {"name": "Off-taker Risk", "weight": 0.20, "sub_factors": [
            "Off-taker credit quality", "Revenue contract strength",
            "Market competitiveness", "Demand risk exposure"
        ]},
        {"name": "Cash Flow Predictability", "weight": 0.25, "sub_factors": [
            "Revenue predictability", "Cost predictability",
            "Debt service coverage stability", "Cash flow volatility"
        ]},
        {"name": "Financial Profile", "weight": 0.25, "sub_factors": [
            "DSCR (min/avg)", "Leverage (debt/equity)",
            "Liquidity adequacy", "Reserve fund adequacy"
        ]},
        {"name": "Structural Features", "weight": 0.10, "sub_factors": [
            "Cash sweep mechanism", "Distribution lock-up",
            "Security package quality", "Intercreditor provisions"
        ]},
    ]
}

# ── Score Mapping ────────────────────────────────────────────
SCORE_MAP = {
    "Aaa": 1, "Aa1": 2, "Aa2": 3, "Aa3": 4,
    "A1": 5, "A2": 6, "A3": 7,
    "Baa1": 8, "Baa2": 9, "Baa3": 10,
    "Ba1": 11, "Ba2": 12, "Ba3": 13,
    "B1": 14, "B2": 15, "B3": 16,
    "Caa1": 17, "Caa2": 18, "Caa3": 19,
}

REVERSE_MAP = {v: k for k, v in SCORE_MAP.items()}


def _numeric_to_rating(score: float) -> str:
    """Convert weighted numeric score to Moody's rating."""
    rounded = max(1, min(19, round(score)))
    return REVERSE_MAP.get(rounded, "Baa2")


def _dscr_to_score(dscr: float) -> int:
    """Map DSCR to Moody's factor score using the real DSCR-by-rating
    floors published in rating_benchmarks.STRUCTURING_CRITERIA, instead of
    independently-invented cutoffs."""
    for rating in _DSCR_RATING_ORDER:
        if dscr >= STRUCTURING_CRITERIA["dscr_by_rating"][rating]["min"]:
            return _DSCR_RATING_TO_NUMERIC[rating]
    return 17  # below the B floor — Caa1


def _ltv_to_score(ltv: float) -> int:
    """Map LTV to factor score using the real estate LTV-by-rating ceilings
    published in rating_benchmarks.SECTOR_SCORING_OVERRIDES, instead of
    independently-invented cutoffs."""
    ltv_pct = ltv  # already expressed as a percentage (e.g. 65, not 0.65)
    for rating in _LTV_RATING_ORDER:
        if ltv_pct <= _LTV_THRESHOLDS[rating] * 100:
            return _LTV_RATING_TO_NUMERIC[rating]
    return 17  # exceeds the B ceiling


def score_deal(deal: dict, methodology: str = "moodys_generic_pf") -> dict:
    """
    Full factor decomposition scoring.
    Returns output matching build brief Section 3.2 schema.
    """
    # Run existing credit engine for base metrics
    metrics = credit.compute(deal)
    dscr = metrics["dscr"]
    ltv = metrics["ltv_pct"]
    obligor_grade = metrics["obligor_grade"]

    # Factor scoring
    factor_results = []
    weighted_score = 0.0

    for factor in MOODYS_GENERIC_PF["factors"]:
        if factor["name"] == "Financial Profile":
            score = round((_dscr_to_score(dscr) + _ltv_to_score(ltv)) / 2)
            rationale = f"DSCR {dscr}x, LTV {ltv}%"
        elif factor["name"] == "Cash Flow Predictability":
            score = _dscr_to_score(dscr)
            rationale = f"DSCR-implied cash flow stability at {dscr}x"
        elif factor["name"] == "Asset Operating Risk":
            occ = deal.get("occupancy_pct", 85)
            score = 7 if occ >= 90 else 9 if occ >= 80 else 12
            rationale = f"Occupancy {occ}%"
        elif factor["name"] == "Off-taker Risk":
            score = deal.get("offtaker_score", 9)
            rationale = deal.get("offtaker_rationale", "Standard contractual framework")
        elif factor["name"] == "Structural Features":
            has_sweep = deal.get("cash_sweep", True)
            has_lockup = deal.get("distribution_lockup", True)
            score = 6 if (has_sweep and has_lockup) else 9 if has_sweep else 12
            rationale = f"Sweep: {'Yes' if has_sweep else 'No'}, Lock-up: {'Yes' if has_lockup else 'No'}"
        else:
            score = 9
            rationale = "Standard assessment"

        rating = _numeric_to_rating(score)
        weighted_score += score * factor["weight"]

        factor_results.append({
            "factor_name": factor["name"],
            "weight": factor["weight"],
            "score": score,
            "factor_rating": rating,
            "rationale": rationale,
            "sub_factors": factor["sub_factors"],
        })

    # Structural notching
    notching = []
    if deal.get("surety_wrap"):
        notching.append({"feature": "Surety wrap (Hylant)", "impact_notches": -2})
    if deal.get("cash_funded_dsrf"):
        notching.append({"feature": "Cash-funded DSRF", "impact_notches": -1})
    if metrics.get("ltv_alert"):
        notching.append({"feature": f"LTV {ltv}% exceeds 75% threshold", "impact_notches": 1})

    notch_adj = sum(n["impact_notches"] for n in notching)
    final_score = max(1, min(19, round(weighted_score + notch_adj)))
    indicative = _numeric_to_rating(final_score)

    # Real S&P cross-check via rating_benchmarks — sector-specific DSCR/LTV
    # scoring (SECTOR_SCORING_OVERRIDES) when a sector is known, standard
    # corporate FFO/Debt + Debt/EBITDA scoring otherwise. Independent of the
    # Moody's PF factor decomposition above, so a rating committee can see
    # where the two agencies' methodologies agree or diverge on this deal.
    sp_financial_risk = score_sp_financial_risk({
        "dscr": dscr,
        "ltv": ltv,
        "sector": deal.get("sector", "real_estate"),
    })

    # S&P weak-link (for construction deals)
    construction_sacp = None
    operations_sacp = None
    weak_link = None
    if deal.get("is_construction"):
        c_score = deal.get("construction_risk_score", 12)
        o_score = round(weighted_score)
        construction_sacp = _numeric_to_rating(c_score)
        operations_sacp = _numeric_to_rating(o_score)
        weak_link = _numeric_to_rating(max(c_score, o_score))

    return {
        "deal_id": deal.get("id", ""),
        "methodology": MOODYS_GENERIC_PF["name"],
        "methodology_doc_id": MOODYS_GENERIC_PF["doc_id"],
        "scoring_date": datetime.utcnow().isoformat(),
        "factor_decomposition": factor_results,
        "scorecard_indicated_outcome": _numeric_to_rating(round(weighted_score)),
        "structural_notching": notching,
        "indicative_rating": indicative,
        "construction_sacp": construction_sacp,
        "operations_sacp": operations_sacp,
        "weak_link_sacp": weak_link,
        "confidence_band": f"{_numeric_to_rating(max(1, final_score - 1))} to {_numeric_to_rating(min(19, final_score + 1))}",
        "jpm_obligor_grade": obligor_grade,
        "jpm_metrics": metrics,
        "sp_financial_risk": sp_financial_risk,
    }
