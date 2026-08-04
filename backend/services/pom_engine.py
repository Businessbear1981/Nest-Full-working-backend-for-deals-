"""
NEST POM Engine — what does the offering document actually cost NEST to produce?

WHY THIS EXISTS. `gate_fee_engine.py` carried a hand-set 196 hours for the
Preliminary Offering Memorandum gate. That number was indefensible in both
directions: nobody could say what work it represented, and nobody could say
whether it was too high or too low, because it rested on an unstated assumption
about who drafts the document. That assumption is the entire question.

A POM can be produced three materially different ways, and NEST's hours swing
by a factor of two across them:

  COUNSEL_DRAFTS    Disclosure counsel drafts the full document. NEST reviews,
                    supplies numbers, and turns comments. Cheapest for NEST,
                    most expensive for the client in legal fees, and NEST has
                    the least control over how the credit is characterised.

  MARKET_STANDARD   The conventional municipal allocation. NEST drafts the
                    financial and structural sections -- plan of finance,
                    security, coverage, bondholders' risks -- counsel drafts
                    the legal sections, the borrower drafts the project and
                    management sections, and each expert owns its appendix.

  NEST_DRAFTS_ALL   NEST quarterbacks the entire document except the sections
                    that are legally required to originate with counsel (tax
                    matters, the form of opinion, the summary of principal
                    documents). Most control, most hours.

So this engine does not assert a number. It takes the engagement structure as
an input and derives the number, and it reports the variance against the old
hand-set figure so the change is visible rather than silent.

SECOND THING IT DOES. A POM section cannot be drafted before its input exists.
You cannot write the feasibility summary without a feasibility study, or the
financial information section without audited financials, or the rating section
before a rating. So each section declares its required inputs, and the engine
reports which sections are BLOCKED given the deal as it stands today. That is
the honest answer to "when can we go to market" -- not a date, but a list of
the specific things whose absence is holding the document.

PROVENANCE. The section list reflects standard municipal offering-document
practice. The per-section hours are HAND_SET planning estimates, same as
everywhere else in this platform: NEST has not closed enough deals to have
measured them. What has changed is the granularity -- twenty-two defensible
line items instead of one indefensible total. Each one can be argued with
individually, which is the point.
"""
from __future__ import annotations

from typing import Any

HOURS_PROVENANCE = "HAND_SET_PLANNING_ESTIMATE"

# The figure this engine replaces, retained so the variance is reportable.
LEGACY_HAND_SET_POM_HOURS = 196

# Who originates a section. NEST's hours depend on whether it is drafting or
# reviewing, and reviewing someone else's draft is not free.
OWNER_NEST = "NEST"
OWNER_BOND_COUNSEL = "BOND_COUNSEL"
OWNER_BORROWER = "BORROWER"
OWNER_FEASIBILITY = "FEASIBILITY_CONSULTANT"
OWNER_AUDITOR = "AUDITOR"
OWNER_UNDERWRITER = "UNDERWRITER"

DRAFTING_MODELS = ("counsel_drafts", "market_standard", "nest_drafts_all")
DEFAULT_DRAFTING_MODEL = "market_standard"

# Sections counsel must originate regardless of engagement structure. NEST does
# not draft a tax opinion or a summary of documents it did not paper, and any
# model that says otherwise is describing an unauthorized practice problem.
COUNSEL_RESERVED = {
    "tax_matters", "legal_matters", "appendix_opinion",
    "appendix_summary_of_documents", "appendix_continuing_disclosure_form",
}

# Comment turns on the full document. Each cycle is a read of the whole draft,
# a markup, and a drafting call. Four is a normal first-time issuer.
DEFAULT_COMMENT_CYCLES = 4
HOURS_PER_COMMENT_CYCLE = 9

# id, name, default owner, NEST hours if drafting, NEST hours if reviewing,
# inputs that must exist before the section can be written, and the condition
# under which the section appears at all.
POM_SECTIONS: list[dict[str, Any]] = [
    {"id": "cover_and_summary", "name": "Cover Page and Summary of Terms",
     "owner": OWNER_NEST, "draft_hours": 8, "review_hours": 3,
     "requires": ["par_amount", "maturity_schedule"]},

    {"id": "introduction", "name": "Introduction",
     "owner": OWNER_NEST, "draft_hours": 6, "review_hours": 2,
     "requires": []},

    {"id": "the_bonds", "name": "The Series Bonds (Terms, Redemption, Book-Entry)",
     "owner": OWNER_BOND_COUNSEL, "draft_hours": 14, "review_hours": 5,
     "requires": ["bond_counsel_engaged", "maturity_schedule"]},

    {"id": "plan_of_finance", "name": "Plan of Finance",
     "owner": OWNER_NEST, "draft_hours": 20, "review_hours": 6,
     "requires": ["capital_stack"]},

    {"id": "sources_and_uses", "name": "Estimated Sources and Uses of Funds",
     "owner": OWNER_NEST, "draft_hours": 12, "review_hours": 4,
     "requires": ["capital_stack", "project_budget"]},

    {"id": "security_and_sources", "name": "Security and Sources of Payment",
     "owner": OWNER_NEST, "draft_hours": 28, "review_hours": 10,
     "requires": ["trust_indenture", "revenue_mechanism"]},

    {"id": "the_project", "name": "The Project",
     "owner": OWNER_BORROWER, "draft_hours": 16, "review_hours": 8,
     "requires": ["project_description", "site_control"]},

    {"id": "the_borrower", "name": "The Borrower / Obligated Group",
     "owner": OWNER_BORROWER, "draft_hours": 12, "review_hours": 6,
     "requires": ["org_structure"]},

    {"id": "management", "name": "Management and Development Team",
     "owner": OWNER_BORROWER, "draft_hours": 8, "review_hours": 4,
     "requires": ["org_structure"]},

    {"id": "feasibility_summary", "name": "Summary of the Feasibility Study",
     "owner": OWNER_FEASIBILITY, "draft_hours": 14, "review_hours": 8,
     "requires": ["feasibility_study"]},

    {"id": "financial_information", "name": "Financial Information and Projections",
     "owner": OWNER_NEST, "draft_hours": 24, "review_hours": 8,
     "requires": ["audited_financials", "financial_projections"]},

    {"id": "bondholders_risks", "name": "Bondholders' Risks",
     "owner": OWNER_NEST, "draft_hours": 26, "review_hours": 10,
     "requires": ["feasibility_study", "revenue_mechanism"]},

    {"id": "tax_matters", "name": "Tax Matters",
     "owner": OWNER_BOND_COUNSEL, "draft_hours": 0, "review_hours": 4,
     "requires": ["bond_counsel_engaged", "tax_status_determination"]},

    {"id": "continuing_disclosure", "name": "Continuing Disclosure",
     "owner": OWNER_BOND_COUNSEL, "draft_hours": 6, "review_hours": 3,
     "requires": ["bond_counsel_engaged"]},

    {"id": "legal_matters", "name": "Legal Matters and Litigation",
     "owner": OWNER_BOND_COUNSEL, "draft_hours": 0, "review_hours": 3,
     "requires": ["bond_counsel_engaged"]},

    {"id": "rating", "name": "Rating",
     "owner": OWNER_NEST, "draft_hours": 6, "review_hours": 2,
     "requires": ["rating"], "only_if": "rated"},

    {"id": "underwriting", "name": "Underwriting / Plan of Distribution",
     "owner": OWNER_UNDERWRITER, "draft_hours": 5, "review_hours": 3,
     "requires": ["underwriter_engaged"], "only_if": "underwritten"},

    {"id": "credit_enhancement", "name": "The Credit Facility / Enhancement",
     "owner": OWNER_NEST, "draft_hours": 14, "review_hours": 6,
     "requires": ["credit_enhancement_term_sheet"], "only_if": "enhanced"},

    {"id": "appendix_audited_financials", "name": "Appendix: Audited Financial Statements",
     "owner": OWNER_AUDITOR, "draft_hours": 0, "review_hours": 4,
     "requires": ["audited_financials"]},

    {"id": "appendix_feasibility_study", "name": "Appendix: Feasibility Study",
     "owner": OWNER_FEASIBILITY, "draft_hours": 0, "review_hours": 6,
     "requires": ["feasibility_study"]},

    {"id": "appendix_opinion", "name": "Appendix: Form of Bond Counsel Opinion",
     "owner": OWNER_BOND_COUNSEL, "draft_hours": 0, "review_hours": 2,
     "requires": ["bond_counsel_engaged"]},

    {"id": "appendix_summary_of_documents", "name": "Appendix: Summary of Principal Documents",
     "owner": OWNER_BOND_COUNSEL, "draft_hours": 0, "review_hours": 8,
     "requires": ["trust_indenture"]},

    {"id": "appendix_continuing_disclosure_form", "name": "Appendix: Form of Continuing Disclosure Agreement",
     "owner": OWNER_BOND_COUNSEL, "draft_hours": 0, "review_hours": 2,
     "requires": ["bond_counsel_engaged"]},
]


class POMError(ValueError):
    """Raised on an unknown drafting model."""


def _section_applies(section: dict, deal: dict) -> bool:
    """Conditional sections appear only when the deal actually has the feature."""
    cond = section.get("only_if")
    if cond is None:
        return True
    if cond == "rated":
        return bool(deal.get("rating") or deal.get("seeking_rating"))
    if cond == "underwritten":
        # Absent a stated method, assume a public underwritten sale.
        return deal.get("distribution_method", "underwritten") != "private_placement"
    if cond == "enhanced":
        return bool(deal.get("credit_enhancement")
                    or deal.get("credit_enhancement_term_sheet"))
    return True


def _nest_drafts(section: dict, model: str) -> bool:
    """Whether NEST holds the pen on this section under the given model."""
    if section["id"] in COUNSEL_RESERVED:
        return False
    if section["draft_hours"] <= 0:
        return False
    if model == "counsel_drafts":
        return False
    if model == "nest_drafts_all":
        return True
    return section["owner"] == OWNER_NEST


def _missing_inputs(section: dict, deal: dict) -> list[str]:
    """Inputs the section needs that the deal does not yet have."""
    return [k for k in section.get("requires", []) if not deal.get(k)]


def plan_pom(
    deal: dict | None = None,
    *,
    drafting_model: str = DEFAULT_DRAFTING_MODEL,
    comment_cycles: int = DEFAULT_COMMENT_CYCLES,
) -> dict:
    """
    Derive NEST's POM hours from the engagement structure and the deal.

    Returns the per-section allocation, NEST's total hours, the sections
    currently blocked for want of an input, and the variance against the
    hand-set figure this engine replaces.
    """
    if drafting_model not in DRAFTING_MODELS:
        raise POMError(
            f"unknown drafting model {drafting_model!r}; "
            f"expected one of {', '.join(DRAFTING_MODELS)}"
        )
    if comment_cycles < 0:
        raise POMError("comment_cycles cannot be negative")

    deal = deal or {}
    sections: list[dict] = []
    drafting_hours = review_hours = 0

    for s in POM_SECTIONS:
        if not _section_applies(s, deal):
            continue
        drafts = _nest_drafts(s, drafting_model)
        hours = s["draft_hours"] if drafts else s["review_hours"]
        missing = _missing_inputs(s, deal)
        if drafts:
            drafting_hours += hours
        else:
            review_hours += hours
        sections.append({
            "id": s["id"],
            "name": s["name"],
            "owner": OWNER_NEST if drafts else s["owner"],
            "nest_role": "DRAFT" if drafts else "REVIEW",
            "nest_hours": hours,
            "blocked": bool(missing),
            "missing_inputs": missing,
            "counsel_reserved": s["id"] in COUNSEL_RESERVED,
        })

    overhead = comment_cycles * HOURS_PER_COMMENT_CYCLE
    total = drafting_hours + review_hours + overhead

    blocked = [s for s in sections if s["blocked"]]
    # An input blocking several sections is the one worth chasing first.
    blocking_counts: dict[str, int] = {}
    for s in blocked:
        for k in s["missing_inputs"]:
            blocking_counts[k] = blocking_counts.get(k, 0) + 1
    critical_inputs = sorted(
        blocking_counts.items(), key=lambda kv: (-kv[1], kv[0]))

    return {
        "drafting_model": drafting_model,
        "sections": sections,
        "section_count": len(sections),
        "hours": {
            "drafting": drafting_hours,
            "review": review_hours,
            "comment_cycles": overhead,
            "comment_cycle_count": comment_cycles,
            "total": total,
            "provenance": HOURS_PROVENANCE,
        },
        "variance_from_legacy": {
            "legacy_hand_set_hours": LEGACY_HAND_SET_POM_HOURS,
            "derived_hours": total,
            "delta": total - LEGACY_HAND_SET_POM_HOURS,
            "note": (
                "The legacy figure assumed, without saying so, that NEST "
                "drafts. Under counsel_drafts the same document costs NEST "
                "roughly half as much."
            ),
        },
        "readiness": {
            "sections_blocked": len(blocked),
            "sections_writable_now": len(sections) - len(blocked),
            "pct_writable": (round((len(sections) - len(blocked))
                                   / len(sections), 4) if sections else 0.0),
            "blocked_section_ids": [s["id"] for s in blocked],
            "critical_inputs": [
                {"input": k, "blocks_sections": n} for k, n in critical_inputs
            ],
        },
    }


def compare_drafting_models(deal: dict | None = None,
                            *, comment_cycles: int = DEFAULT_COMMENT_CYCLES
                            ) -> dict:
    """
    Price the same document three ways.

    This is the output that answers the actual question. It does not recommend
    a model -- that is a commercial decision about control and legal cost that
    NEST makes with the client, not one an engine should make silently.
    """
    plans = {m: plan_pom(deal, drafting_model=m, comment_cycles=comment_cycles)
             for m in DRAFTING_MODELS}
    return {
        "models": {
            m: {
                "nest_hours": p["hours"]["total"],
                "drafting_hours": p["hours"]["drafting"],
                "review_hours": p["hours"]["review"],
                "sections_drafted_by_nest": sum(
                    1 for s in p["sections"] if s["nest_role"] == "DRAFT"),
            } for m, p in plans.items()
        },
        "spread_hours": (max(p["hours"]["total"] for p in plans.values())
                         - min(p["hours"]["total"] for p in plans.values())),
        "readiness": plans[DEFAULT_DRAFTING_MODEL]["readiness"],
        "note": (
            "Choose on control and legal cost, not on NEST hours alone. The "
            "sections NEST drafts are the ones that characterise the credit: "
            "plan of finance, security, coverage, and bondholders' risks."
        ),
    }
