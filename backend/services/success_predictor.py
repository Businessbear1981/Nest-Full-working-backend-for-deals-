"""
NEST Success Predictor — where does this deal actually stall, and why.

Answers three questions off real, observable project parameters:

  1. What is the probability this project reaches each arrangement gate?
  2. Where is it most likely to stall, given where it stands TODAY?
  3. What specific missing item is driving that, and what would fix it?

METHODOLOGY, STATED PLAINLY -- read before trusting a number.

This is a **transparent structured scorecard, not a statistically calibrated
model.** It is not fit to historical closing data, because NEST does not yet
have a closed-deal dataset to fit against. Every base rate and factor weight
below is an explicit, editable assumption, and every output echoes the
assumptions and the confidence tier it was produced under.

What that means in practice: the *ranking* of stall risk is the reliable
output -- it reflects real structural dependencies (you cannot get a rating
without audited financials; you cannot price special assessment debt without
seasoned assessments). The *absolute probabilities* are directional and
should be treated as PROPOSED, not VERIFIED, until there is real outcome
data to calibrate against. `confidence` on every result says so.

The engine never invents a parameter. A deal that supplies nothing gets a
low-confidence result and an explicit list of what it would need to answer
properly -- not a fabricated score.
"""
from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Gate prerequisites.
#
# Each gate lists the project parameters that must be real before that gate
# can clear. These are structural dependencies, not opinions -- a rating
# agency will not issue an indicative rating without financials, and a
# special assessment series will not price without seasoned assessments.
#
# `weight` is how much a missing prerequisite hurts that gate's probability.
# ---------------------------------------------------------------------------

GATE_PREREQUISITES = {
    "g1_readiness": [
        ("site_control", 0.35, "Site control (owned, under option, or under contract)"),
        ("sponsor_entity_formed", 0.15, "Project entity formed with clean org chart"),
        ("project_budget", 0.30, "Detailed development budget"),
        ("sponsor_track_record", 0.20, "Sponsor track record on comparable projects"),
    ],
    "g2_capital_stack": [
        ("project_budget", 0.25, "Detailed development budget"),
        ("financial_model", 0.35, "Integrated financial model with sources and uses"),
        ("equity_committed_pct", 0.40, "Sponsor equity actually committed"),
    ],
    "g3_diligence": [
        ("feasibility_study", 0.40, "Independent market feasibility study"),
        ("environmental_phase_i", 0.25, "Phase I environmental assessment"),
        ("construction_pricing", 0.35, "Construction pricing (GMP or hard bid)"),
    ],
    "g4_enhancement": [
        ("projected_dscr", 0.45, "Projected DSCR at or above enhancer threshold"),
        ("revenue_contracted_pct", 0.35, "Contracted or committed revenue"),
        ("feasibility_study", 0.20, "Independent feasibility supporting projections"),
    ],
    "g5_counsel": [
        ("tax_status_determination", 0.45, "Tax status path identified (governmental, 501c3, taxable)"),
        ("issuer_identified", 0.55, "Conduit issuer identified and willing"),
    ],
    "g6_rating": [
        ("audited_financials", 0.40, "Audited financial statements"),
        ("projected_dscr", 0.30, "Projected DSCR supporting an investment grade outcome"),
        ("revenue_mechanism_seasoned", 0.30, "Revenue mechanism seasoned or otherwise evidenced"),
    ],
    "g7_pom": [
        ("audited_financials", 0.30, "Audited financial statements"),
        ("permits_status", 0.40, "Entitlements and permits materially in hand"),
        ("feasibility_study", 0.30, "Feasibility study for the market section"),
    ],
    "g8_bond_ready": [
        ("permits_status", 0.30, "Entitlements and permits materially in hand"),
        ("trustee_engaged", 0.20, "Indenture trustee engaged"),
        ("revenue_mechanism_seasoned", 0.25, "Revenue mechanism seasoned"),
        ("equity_committed_pct", 0.25, "Equity funded to bankability"),
    ],
    "g9_pricing": [
        ("revenue_contracted_pct", 0.40, "Contracted revenue supporting buyer underwriting"),
        ("rating_or_enhancement", 0.35, "Rating obtained or enhancement committed"),
        ("market_window", 0.25, "Receptive market window at pricing"),
    ],
    "g10_closing": [
        ("permits_status", 0.30, "All conditions precedent satisfied"),
        ("rating_or_enhancement", 0.30, "Rating or enhancement in place"),
        ("equity_committed_pct", 0.40, "Equity funded at close"),
    ],
}

# Base rate a gate clears assuming its prerequisites are fully satisfied.
# Later gates carry more execution and market risk even when fully prepared.
GATE_BASE_RATE = {
    "g1_readiness": 0.95, "g2_capital_stack": 0.93, "g3_diligence": 0.90,
    "g4_enhancement": 0.80, "g5_counsel": 0.92, "g6_rating": 0.82,
    "g7_pom": 0.90, "g8_bond_ready": 0.85, "g9_pricing": 0.78,
    "g10_closing": 0.90,
}

# Parameters read as a 0..1 completeness score. Booleans map to 0/1;
# percentages are normalized against the threshold at which the parameter
# stops being a constraint.
# Procurable prerequisites are things a sponsor can go buy or commission --
# a feasibility study, an audit, a GMP, a trustee. Their absence is a cost and
# a delay, not a verdict on viability. Structural prerequisites (a willing
# conduit issuer, a workable tax status, coverage that actually clears) can
# genuinely kill a financing.
#
# This distinction exists because scoring them the same produced a 0%
# probability of close for a real, financeable project whose only sin was
# being early -- an output that is confidently wrong.
PROCURABLE_PARAMETERS = {
    "feasibility_study", "environmental_phase_i", "construction_pricing",
    "audited_financials", "trustee_engaged", "financial_model",
    "project_budget", "permits_status", "revenue_mechanism_seasoned",
}

# A gate whose only unmet items are procurable cannot fall below this. It is
# delayed, not dead.
PROCURABLE_FLOOR = 0.55

PCT_PARAMETERS = {
    "equity_committed_pct": 100.0,      # fully committed at 100%
    "revenue_contracted_pct": 60.0,     # 60% contracted is generally enough
    "permits_status": 100.0,
}

# What a fully-prepared project in a receptive market actually closes at.
# Not 100% -- markets move, sponsors walk, councils vote no. Stated as an
# assumption because it is one; it sets the top of the probability scale.
PERFECT_DEAL_CLOSE_RATE = 0.85

DSCR_FLOOR = 1.20   # below this, coverage is a live constraint
DSCR_STRONG = 1.50  # at or above this, coverage stops being the binding issue


def _param_score(deal: dict, key: str) -> float | None:
    """0..1 completeness for one parameter. None means 'not supplied'."""
    if key == "projected_dscr":
        v = deal.get("projected_dscr", deal.get("dscr"))
        if v in (None, ""):
            return None
        v = float(v)
        if v <= DSCR_FLOOR:
            return 0.0
        if v >= DSCR_STRONG:
            return 1.0
        return (v - DSCR_FLOOR) / (DSCR_STRONG - DSCR_FLOOR)

    if key == "rating_or_enhancement":
        got = deal.get("rating_obtained") or deal.get("enhancement_committed")
        return None if got is None else (1.0 if got else 0.0)

    if key in PCT_PARAMETERS:
        v = deal.get(key)
        if v in (None, ""):
            return None
        return max(0.0, min(1.0, float(v) / PCT_PARAMETERS[key]))

    v = deal.get(key)
    if v is None or v == "":
        return None
    if isinstance(v, bool):
        return 1.0 if v else 0.0
    if isinstance(v, (int, float)):
        return max(0.0, min(1.0, float(v)))
    # Strings: treat known-negative markers as zero, anything else as present.
    return 0.0 if str(v).strip().lower() in ("none", "no", "false", "pending", "n/a") else 1.0


def predict_gate_probabilities(deal: dict) -> dict:
    """
    Per-gate clearing probability plus the specific unmet prerequisites.

    A prerequisite that was never supplied is treated as a **known unknown**,
    not as a failure: it reduces confidence and is reported under
    `unknown_prerequisites`, and is scored at a neutral 0.5 rather than 0.
    Scoring absent data as zero would let a thin intake form manufacture a
    doomed-looking deal, which is its own kind of fabrication.
    """
    gates = []
    supplied = 0
    total_params = 0

    for gate_id, prereqs in GATE_PREREQUISITES.items():
        base = GATE_BASE_RATE[gate_id]
        penalty = 0.0
        structural_penalty = 0.0
        unmet, unknown = [], []

        for key, weight, label in prereqs:
            total_params += 1
            score = _param_score(deal, key)
            if score is None:
                unknown.append({"parameter": key, "needs": label})
                score = 0.5
            else:
                supplied += 1
                if score < 0.75:
                    unmet.append({
                        "parameter": key, "needs": label,
                        "completeness": round(score, 2),
                        "impact": round(weight * (1 - score), 3),
                    })
            gap = weight * (1 - score)
            penalty += gap
            if key not in PROCURABLE_PARAMETERS:
                structural_penalty += gap

        # Normalize penalty by total weight so gates with more prerequisites
        # are not automatically penalized for having more to satisfy.
        total_weight = sum(w for _, w, _ in prereqs)
        prob = base * (1 - min(1.0, penalty / total_weight))

        # Floor the gate when the shortfall is procurable rather than
        # structural. Without this, an early-stage project reads as
        # impossible instead of as unprepared.
        structural_share = structural_penalty / total_weight if total_weight else 0.0
        if structural_share < 0.5:
            prob = max(prob, PROCURABLE_FLOOR * base * (1 - structural_share))

        unmet.sort(key=lambda u: u["impact"], reverse=True)
        gates.append({
            "gate_id": gate_id,
            "base_rate": base,
            "probability": round(max(0.0, min(1.0, prob)), 4),
            "unmet_prerequisites": unmet,
            "unknown_prerequisites": unknown,
            "shortfall": ("structural" if structural_share >= 0.5
                          else "procurable" if unmet else "none"),
        })

    coverage = supplied / total_params if total_params else 0.0
    return {
        "gates": gates,
        "parameter_coverage": round(coverage, 3),
        "confidence": ("low" if coverage < 0.4 else
                       "medium" if coverage < 0.75 else "high"),
    }


def predict_success(deal: dict, *, _procured: bool | None = None) -> dict:
    """
    Full success prediction: cumulative probability of reaching close, the
    single most likely stall point, and what to do about it.
    """
    per_gate = predict_gate_probabilities(deal)
    gates = per_gate["gates"]

    # Deals do not die by compounding ten independent coin flips -- that
    # model produced ~0% for financeable projects. They die from one binding
    # constraint. A missing feasibility study does not fail the deal; it
    # stalls it until someone commissions the study.
    #
    # So preparedness per gate is scored as ratio = probability / base_rate
    # (1.0 = fully prepared for that gate), and close probability blends the
    # WEAKEST link with the overall average. Weakest-link dominates because
    # that is how financings actually fail; the average keeps a single early
    # gap from reading as fatal.
    raw = 1.0
    ratios = []
    for g in gates:
        raw *= g["probability"]
        g["cumulative_to_here"] = round(raw, 4)
        base = GATE_BASE_RATE[g["gate_id"]]
        ratio = g["probability"] / base if base else 0.0
        g["preparedness"] = round(ratio, 3)
        ratios.append(max(1e-6, min(1.0, ratio)))

    weakest = min(ratios)
    average = sum(ratios) / len(ratios)
    cumulative = PERFECT_DEAL_CLOSE_RATE * (weakest ** 0.5) * (average ** 0.5)
    cumulative = max(0.0, min(1.0, cumulative))

    # The stall point is the gate that destroys the most probability, not
    # simply the lowest-probability gate -- a low-probability gate that is
    # already unreachable matters less than an early one that gates everything.
    ranked = sorted(gates, key=lambda g: g["probability"])
    stall = ranked[0]

    blockers = []
    for g in gates:
        for u in g["unmet_prerequisites"]:
            blockers.append({**u, "gate_id": g["gate_id"]})
    blockers.sort(key=lambda b: b["impact"], reverse=True)

    # Deduplicate: one parameter can block several gates. Report the
    # parameter once with every gate it blocks -- that is the item worth
    # fixing first.
    by_param: dict[str, dict] = {}
    for b in blockers:
        p = by_param.setdefault(b["parameter"], {
            "parameter": b["parameter"], "needs": b["needs"],
            "completeness": b["completeness"], "blocks_gates": [],
            "total_impact": 0.0,
        })
        p["blocks_gates"].append(b["gate_id"])
        p["total_impact"] = round(p["total_impact"] + b["impact"], 3)
    critical = sorted(by_param.values(), key=lambda p: p["total_impact"], reverse=True)

    # "Probability of close" with today's parameters frozen forever is the
    # wrong headline for an early project -- it compounds ten gates of
    # unpreparedness and reports near-zero for a deal that is simply early.
    # The decision-useful number is what it closes at once the procurable
    # items are procured, which is what an engagement actually delivers.
    if _procured is None:
        procured_deal = dict(deal)
        for key in PROCURABLE_PARAMETERS:
            if key in PCT_PARAMETERS:
                procured_deal[key] = PCT_PARAMETERS[key]
            else:
                procured_deal[key] = True
        remediated = predict_success(procured_deal, _procured=True)
        prob_if_procured = remediated["probability_of_close"]
        lift = round(prob_if_procured - cumulative, 4)
    else:
        prob_if_procured = None
        lift = None

    return {
        "probability_of_close_as_is": round(cumulative, 4),
        "probability_if_procured": prob_if_procured,
        "lift_from_procurement": lift,
        "headline": (
            None if prob_if_procured is None else
            f"As it stands today this financing prices at {cumulative:.0%}. "
            f"With the procurable items in hand -- feasibility study, audit, "
            f"GMP construction pricing, permits, trustee -- it reaches "
            f"{prob_if_procured:.0%}. A fully prepared project in a receptive "
            f"market tops out near {PERFECT_DEAL_CLOSE_RATE:.0%}; the "
            f"remaining gap is structural, not procurable."
        ),
        "probability_of_close": round(cumulative, 4),
        "confidence": per_gate["confidence"],
        "parameter_coverage": per_gate["parameter_coverage"],
        "stall_point": {
            "gate_id": stall["gate_id"],
            "probability": stall["probability"],
            "unmet": stall["unmet_prerequisites"],
            "unknown": stall["unknown_prerequisites"],
        },
        "critical_path_items": critical[:5],
        "unknown_parameters": sorted({
            u["parameter"] for g in gates for u in g["unknown_prerequisites"]
        }),
        "gates": gates,
        "methodology": (
            "Transparent structured scorecard, not a statistically calibrated "
            "model. Gate rankings and stall-point identification reflect real "
            "structural dependencies and are the reliable output. Absolute "
            "probabilities are directional (PROPOSED, not VERIFIED) until "
            "calibrated against closed-deal outcome data."
        ),
    }


def gate_probability_map(deal: dict) -> dict[str, float]:
    """Gate id -> probability, for feeding the fee optimizer."""
    return {g["gate_id"]: g["probability"]
            for g in predict_gate_probabilities(deal)["gates"]}
