"""
NEST Project Readiness Checklist — the intake gate for a real engagement.

This is the operational front door. A sponsor submits documents against the
272-item due diligence checklist; this module scores what is actually there,
computes the Project Readiness Score, decides whether a Move Forward
Memorandum can issue, and hands the result to the success predictor so the
readiness score and the probability-of-close mechanics are driven by the same
evidence rather than by two separate opinions.

SCORING METHODOLOGY -- exactly as the Development Services Agreement defines
it, not a reinterpretation:

    Score = complete items / applicable items

Items marked "Not Applicable" with justification are excluded from BOTH the
numerator and the denominator. An item marked N/A *without* justification is
counted as incomplete -- otherwise "N/A" becomes a way to inflate the score by
declaring inconvenient items irrelevant.

The Move Forward Memorandum issues at >= 80%. Below that, Milestone 1.1's fee
is refundable, which is what makes the threshold real rather than decorative.

Nothing here fabricates a status. An item not submitted is `missing`, and
missing items are reported item-by-item, not summarized away.
"""
from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Any

_DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "data", "project_readiness_checklist.json")

# The DSA's Move Forward threshold.
MOVE_FORWARD_THRESHOLD = 0.80

VALID_ITEM_STATUSES = ("available", "pending", "not_applicable", "missing")

# ---------------------------------------------------------------------------
# Which checklist categories evidence which success-predictor parameters.
#
# This is the join that makes the readiness score and the probability-of-close
# mechanics one system instead of two. A category has to be materially
# complete before it can be said to evidence its parameter -- a half-finished
# Technical section does not prove a feasibility study exists.
# ---------------------------------------------------------------------------

CATEGORY_TO_PARAMETERS = {
    "1": {  # Organizational
        "sponsor_entity_formed": ["1.1", "1.2"],
        "sponsor_track_record": ["1.2"],
    },
    "2": {  # Financial
        "project_budget": ["2.1"],
        "financial_model": ["2.3"],
        "audited_financials": ["2.4"],
    },
    "3": {  # Commercial
        "feasibility_study": ["3.1"],
    },
    "4": {  # Technical
        "construction_pricing": ["4.3"],
        "environmental_phase_i": ["4.2"],
        "site_control": ["4.4"],
    },
    "5": {  # Legal
        "revenue_contracted_pct": ["5.2"],
    },
    "6": {  # Regulatory
        "permits_status": ["6.1"],
    },
    "7": {  # Risk Management
        "trustee_engaged": ["7.4"],
    },
}

# A subcategory must be at least this complete to count as evidencing its
# parameter. Partial evidence is not evidence.
PARAMETER_EVIDENCE_THRESHOLD = 0.70

# Red / amber / green banding. Green is set at the Move Forward threshold on
# purpose: "green" must mean "this actually clears", not "this looks fine".
RAG_GREEN = 0.80
RAG_AMBER = 0.50


def rag(pct: float | None) -> str:
    """Traffic-light status for a completion ratio."""
    if pct is None:
        return "grey"
    if pct >= RAG_GREEN:
        return "green"
    if pct >= RAG_AMBER:
        return "amber"
    return "red"


@lru_cache(maxsize=1)
def load_checklist() -> dict:
    """The 272-item catalogue, loaded once."""
    with open(_DATA, encoding="utf-8") as fh:
        return json.load(fh)


def checklist_catalogue() -> dict:
    """Full catalogue for a client-facing intake form."""
    cl = load_checklist()
    return {
        "total_items": cl["total_items"],
        "source": cl["source"],
        "move_forward_threshold": MOVE_FORWARD_THRESHOLD,
        "categories": [
            {
                "num": c["num"], "name": c["name"], "item_count": c["item_count"],
                "subcategories": [
                    {"num": s["num"], "name": s["name"],
                     "items": s["items"]}
                    for s in c["subcategories"]
                ],
            }
            for c in cl["categories"]
        ],
    }


def _normalize(submissions: dict) -> dict[str, dict]:
    """
    Accept either {"1.1.1": "available"} or
    {"1.1.1": {"status": "not_applicable", "justification": "..."}}.
    """
    out: dict[str, dict] = {}
    for k, v in (submissions or {}).items():
        if isinstance(v, str):
            out[str(k)] = {"status": v.strip().lower(), "justification": ""}
        elif isinstance(v, dict):
            out[str(k)] = {
                "status": str(v.get("status", "missing")).strip().lower(),
                "justification": str(v.get("justification", "") or ""),
                "comment": v.get("comment", ""),
                "available_in_days": v.get("available_in_days"),
            }
    return out


def score_readiness(submissions: dict) -> dict:
    """
    Score a submission set against the checklist.

    Returns the overall Project Readiness Score, a category-by-category
    breakdown, the gap analysis (what is actually missing, named), and whether
    the Move Forward Memorandum can issue.
    """
    cl = load_checklist()
    subs = _normalize(submissions)

    total_applicable = 0
    total_complete = 0
    excluded_na = 0
    disallowed_na = 0
    categories = []
    gaps = []

    for cat in cl["categories"]:
        cat_applicable = cat_complete = 0
        sub_rows = []

        for sub in cat["subcategories"]:
            s_applicable = s_complete = 0
            for item in sub["items"]:
                rec = subs.get(item["num"])
                status = rec["status"] if rec else "missing"

                if status == "not_applicable":
                    if rec and rec.get("justification").strip():
                        excluded_na += 1
                        continue  # excluded from numerator AND denominator
                    # N/A without justification is not a free pass.
                    disallowed_na += 1
                    status = "missing"

                s_applicable += 1
                if status == "available":
                    s_complete += 1
                else:
                    gaps.append({
                        "item": item["num"], "text": item["text"],
                        "category": cat["name"], "subcategory": sub["name"],
                        "status": status,
                        "available_in_days": (rec or {}).get("available_in_days"),
                    })

            sub_rows.append({
                "num": sub["num"], "name": sub["name"],
                "applicable": s_applicable, "complete": s_complete,
                "pct": round(s_complete / s_applicable, 4) if s_applicable else None,
                "pct_display": (round(s_complete / s_applicable * 100, 1)
                                if s_applicable else None),
                "rag": rag(s_complete / s_applicable if s_applicable else None),
            })
            cat_applicable += s_applicable
            cat_complete += s_complete

        categories.append({
            "num": cat["num"], "name": cat["name"],
            "applicable": cat_applicable, "complete": cat_complete,
            "pct": round(cat_complete / cat_applicable, 4) if cat_applicable else None,
            "pct_display": (round(cat_complete / cat_applicable * 100, 1)
                            if cat_applicable else None),
            "rag": rag(cat_complete / cat_applicable if cat_applicable else None),
            "subcategories": sub_rows,
        })
        total_applicable += cat_applicable
        total_complete += cat_complete

    score = total_complete / total_applicable if total_applicable else 0.0
    move_forward = score >= MOVE_FORWARD_THRESHOLD

    weakest = sorted(
        [c for c in categories if c["pct"] is not None],
        key=lambda c: c["pct"])[:3]

    return {
        "readiness_score": round(score, 4),
        "readiness_pct": round(score * 100, 1),
        "items_complete": total_complete,
        "items_applicable": total_applicable,
        "items_total_in_checklist": cl["total_items"],
        "excluded_not_applicable": excluded_na,
        "not_applicable_rejected_no_justification": disallowed_na,
        "move_forward_memorandum": {
            "issues": move_forward,
            "threshold": MOVE_FORWARD_THRESHOLD,
            "shortfall_pct": None if move_forward else round(
                (MOVE_FORWARD_THRESHOLD - score) * 100, 1),
            "consequence": (
                "Move Forward Memorandum issues; Phase 2 and 3 milestone fees "
                "may be deposited and the engagement proceeds."
                if move_forward else
                "Move Forward Memorandum does not issue. The Milestone 1.1 fee "
                "is refundable in full and the engagement does not advance."
            ),
        },
        "rag": rag(score),
        "rag_summary": {
            "green": sum(1 for c in categories if c["rag"] == "green"),
            "amber": sum(1 for c in categories if c["rag"] == "amber"),
            "red": sum(1 for c in categories if c["rag"] == "red"),
            "bands": {"green": f">= {RAG_GREEN:.0%}",
                      "amber": f"{RAG_AMBER:.0%} - {RAG_GREEN:.0%}",
                      "red": f"< {RAG_AMBER:.0%}"},
        },
        "board": [
            {"process": c["name"], "pct": c["pct_display"], "rag": c["rag"],
             "complete": c["complete"], "applicable": c["applicable"]}
            for c in categories
        ],
        "categories": categories,
        "weakest_categories": [
            {"name": c["name"], "pct": round(c["pct"] * 100, 1)} for c in weakest
        ],
        "gap_analysis": gaps,
        "gap_count": len(gaps),
    }


def derive_deal_parameters(readiness: dict) -> dict:
    """
    Translate a scored checklist into success-predictor parameters.

    This is the join. A parameter is only asserted when the subcategories that
    evidence it are materially complete -- otherwise it is left absent, so the
    predictor reports it as a known unknown rather than assuming either way.
    """
    by_sub = {
        s["num"]: s
        for c in readiness.get("categories", [])
        for s in c.get("subcategories", [])
    }

    deal: dict[str, Any] = {}
    for _cat, params in CATEGORY_TO_PARAMETERS.items():
        for param, sub_nums in params.items():
            pcts = [by_sub[n]["pct"] for n in sub_nums
                    if n in by_sub and by_sub[n]["pct"] is not None]
            if not pcts:
                continue
            avg = sum(pcts) / len(pcts)
            if param in ("permits_status", "revenue_contracted_pct"):
                # Percentage-valued parameters carry the evidence level through
                # rather than collapsing to a boolean.
                deal[param] = round(avg * 100, 1)
            else:
                deal[param] = avg >= PARAMETER_EVIDENCE_THRESHOLD

    return deal


def intake(submissions: dict, *, deal_overrides: dict | None = None) -> dict:
    """
    Full intake run: score the checklist, derive parameters, predict success.

    `deal_overrides` supplies what the checklist cannot evidence on its own --
    projected DSCR, whether a conduit issuer is identified, market window --
    and takes precedence over derived values.
    """
    readiness = score_readiness(submissions)
    derived = derive_deal_parameters(readiness)
    deal = {**derived, **(deal_overrides or {})}

    from services.success_predictor import predict_success
    prediction = predict_success(deal)

    return {
        "readiness": readiness,
        "derived_parameters": derived,
        "parameters_used": deal,
        "prediction": prediction,
        "engagement_can_begin": readiness["move_forward_memorandum"]["issues"],
        "summary": (
            f"Readiness {readiness['readiness_pct']}% "
            f"({readiness['items_complete']}/{readiness['items_applicable']} "
            f"applicable items). "
            + ("Move Forward Memorandum issues. " if readiness["move_forward_memorandum"]["issues"]
               else "Below the 80% threshold -- Milestone 1.1 fee refundable. ")
            + f"Predicted close probability {prediction['probability_of_close_as_is']:.0%} "
              f"as-is, stalling at {prediction['stall_point']['gate_id']}."
        ),
    }
