"""
NEST Universal Document Package — what every silo must produce, and when.

WHAT THIS IS. One catalogue of every document a bond financing produces,
assigned to the silo that produces it, behind the checklist gate that must
clear before work on it can start. It is the join between three things that
already existed separately and never talked to each other:

  docs/Bible_Pass1_v2.md SILO 4   the document taxonomy -- WHAT documents exist
  services/gate_fee_engine.py     the ten arrangement gates -- WHEN NEST is paid
  services/readiness_checklist.py the 272-item intake -- WHAT the sponsor has

A NOTE ON THE WORD "SILO", because the codebase uses it two incompatible ways
and anyone reading this will hit the collision within ten minutes:

  The Bible defines SIXTEEN silos. Those are KNOWLEDGE domains -- "The Anatomy
  of a Bond", "The Players", "The Documents". They are a reference library and
  a curriculum. Bible Silo 4 is the document taxonomy this module draws on.

  backend/engines/ declares a "14-Silo Architecture" and numbers its engines
  against it. Those are WORKFLOW stages.

  The two numberings CONFLICT outright. Bible Silo 9 is Credit Enhancement;
  engines/audit_package.py claims Silo 9. Bible Silo 11 is Pricing;
  engines/placement.py claims Silo 11.

This module uses NEITHER numbering. It uses the ten named silos already
carried on the gates in gate_fee_engine.py -- intake, structuring, diligence,
enhancement, documentation, rating, packaging, certification, placement,
closing -- because those are the stages NEST actually bills against and the
frontend already gates on. The Bible supplies the document catalogue; the
gates supply the sequence. Resolving the numbering collision is a separate
decision and is deliberately not made here.

THE GATE RULE. A document is not workable merely because someone has time for
it. It is workable when its inputs exist. So every document declares what it
requires, and the engine reports one of:

  BLOCKED       an input it depends on does not exist yet
  READY         workable now, not started
  IN_PROGRESS   started
  DELIVERED     produced, awaiting acceptance
  ACCEPTED      signed off

A silo is LOCKED while its gate prerequisites are unmet, OPEN once they clear,
and COMPLETE when every required document in it is accepted. Conditional
documents drop out entirely when the deal does not have the feature -- a
taxable private placement does not need a Form 8038 or a blue sky filing, and
carrying them as "incomplete" would misreport the deal.

THE POM IS DIFFERENT. The Preliminary Official Statement is the one composite
document in the catalogue: it is not a single artifact with a single owner but
twenty-three sections with six different owners, and it is the single largest
block of NEST hours in the entire engagement. It therefore delegates to
services/pom_engine.py rather than being tracked as one line item. Every other
document here is atomic.

PROVENANCE. The catalogue reflects Bible Silo 4 plus standard municipal
closing practice. Which documents are REQUIRED versus CONDITIONAL is a
structural judgment stated per document. No hours or costs are asserted here
-- this module answers "what must exist and can we start it", not "what does
it cost". Cost lives in gate_fee_engine.py and pom_engine.py.
"""
from __future__ import annotations

from typing import Any

from services.pom_engine import plan_pom

# --- Bible Silo 4 categories, used verbatim so the taxonomy stays traceable.
CAT_MASTER = "Master Transaction Documents"
CAT_SECURITY = "Security Documents"
CAT_MARKETING = "Marketing Documents"
CAT_OPINION = "Opinion Documents"
CAT_OPERATIONAL = "Operational Documents"
CAT_CERTIFICATE = "Closing Certificates"
CAT_FILING = "Public Filings"
CAT_WORKPRODUCT = "NEST Work Product"      # not a Bible category; NEST's own

# --- The ten arrangement silos, in sequence, joined to their fee gate.
SILOS: list[dict[str, Any]] = [
    {"id": "intake", "seq": 1, "gate_id": "g1_readiness",
     "name": "Intake and Readiness",
     "gate_requires": []},
    {"id": "structuring", "seq": 2, "gate_id": "g2_capital_stack",
     "name": "Capital Stack Architecture",
     "gate_requires": ["project_budget"]},
    {"id": "diligence", "seq": 3, "gate_id": "g3_diligence",
     "name": "Independent Diligence",
     "gate_requires": ["capital_stack"]},
    {"id": "enhancement", "seq": 4, "gate_id": "g4_enhancement",
     "name": "Credit Enhancement",
     "gate_requires": ["capital_stack", "feasibility_study"]},
    {"id": "documentation", "seq": 5, "gate_id": "g5_counsel",
     "name": "Documentation and Counsel",
     "gate_requires": ["bond_counsel_engaged"]},
    {"id": "rating", "seq": 6, "gate_id": "g6_rating",
     "name": "Rating Agency",
     "gate_requires": ["feasibility_study", "financial_projections"]},
    {"id": "packaging", "seq": 7, "gate_id": "g7_pom",
     "name": "Offering Document",
     "gate_requires": ["bond_counsel_engaged"]},
    {"id": "certification", "seq": 8, "gate_id": "g8_bond_ready",
     "name": "Bond-Ready Certification",
     "gate_requires": ["trust_indenture"]},
    {"id": "placement", "seq": 9, "gate_id": "g9_pricing",
     "name": "Placement and Pricing",
     "gate_requires": ["preliminary_official_statement"]},
    {"id": "closing", "seq": 10, "gate_id": "g10_closing",
     "name": "Closing and Settlement",
     "gate_requires": ["priced"]},
]

SILO_IDS = [s["id"] for s in SILOS]

# Conditions a document may hang on. Absent the feature, the document is not
# merely incomplete -- it does not belong to this deal at all.
COND_TAX_EXEMPT = "tax_exempt"
COND_CONDUIT = "conduit_issuer"
COND_RATED = "rated"
COND_ENHANCED = "enhanced"
COND_PUBLIC_OFFERING = "public_offering"
COND_SECURED = "secured"
COND_CONSTRUCTION = "construction"

# id, name, category, silo, owner, requires, only_if
DOCUMENT_CATALOGUE: list[dict[str, Any]] = [
    # ---- INTAKE
    {"id": "data_room", "name": "Secure Data Room", "category": CAT_WORKPRODUCT,
     "silo": "intake", "owner": "NEST", "requires": []},
    {"id": "readiness_report", "name": "Readiness Checklist Report and Gap Analysis",
     "category": CAT_WORKPRODUCT, "silo": "intake", "owner": "NEST",
     "requires": ["readiness_submissions"]},
    {"id": "sponsor_diligence_memo", "name": "Sponsor Diligence Memorandum",
     "category": CAT_WORKPRODUCT, "silo": "intake", "owner": "NEST",
     "requires": ["org_structure"]},
    {"id": "go_no_go_memo", "name": "Written Go / No-Go Recommendation",
     "category": CAT_WORKPRODUCT, "silo": "intake", "owner": "NEST",
     "requires": ["readiness_submissions"]},

    # ---- STRUCTURING
    {"id": "capital_stack_memo", "name": "Capital Stack Architecture Memorandum",
     "category": CAT_WORKPRODUCT, "silo": "structuring", "owner": "NEST",
     "requires": ["project_budget"]},
    {"id": "financial_model", "name": "Financial Model",
     "category": CAT_WORKPRODUCT, "silo": "structuring", "owner": "NEST",
     "requires": ["project_budget", "revenue_mechanism"]},
    {"id": "sources_and_uses", "name": "Sources and Uses Statement",
     "category": CAT_WORKPRODUCT, "silo": "structuring", "owner": "NEST",
     "requires": ["capital_stack", "project_budget"]},
    {"id": "funding_strategy_memo", "name": "Funding Strategy Memorandum",
     "category": CAT_WORKPRODUCT, "silo": "structuring", "owner": "NEST",
     "requires": ["capital_stack"]},
    {"id": "indicative_term_sheet", "name": "Indicative Term Sheet",
     "category": CAT_WORKPRODUCT, "silo": "structuring", "owner": "NEST",
     "requires": ["capital_stack"]},

    # ---- DILIGENCE
    {"id": "feasibility_study", "name": "Feasibility Study",
     "category": CAT_WORKPRODUCT, "silo": "diligence",
     "owner": "FEASIBILITY_CONSULTANT", "requires": ["market_data"]},
    {"id": "independent_engineer_report", "name": "Independent Engineer's Report",
     "category": CAT_WORKPRODUCT, "silo": "diligence", "owner": "VENDOR",
     "requires": ["project_description"]},
    {"id": "market_study", "name": "Market and Demand Study",
     "category": CAT_WORKPRODUCT, "silo": "diligence", "owner": "VENDOR",
     "requires": ["project_description"]},
    {"id": "environmental_phase_i", "name": "Phase I Environmental Site Assessment",
     "category": CAT_WORKPRODUCT, "silo": "diligence", "owner": "VENDOR",
     "requires": ["site_control"]},
    {"id": "appraisal", "name": "Appraisal",
     "category": CAT_WORKPRODUCT, "silo": "diligence", "owner": "VENDOR",
     "requires": ["site_control"]},
    {"id": "audited_financials", "name": "Audited Financial Statements",
     "category": CAT_WORKPRODUCT, "silo": "diligence", "owner": "AUDITOR",
     "requires": ["org_structure"]},

    # ---- ENHANCEMENT
    {"id": "enhancer_info_memo", "name": "Information Memorandum to Credit Enhancers",
     "category": CAT_WORKPRODUCT, "silo": "enhancement", "owner": "NEST",
     "requires": ["capital_stack", "feasibility_study"], "only_if": COND_ENHANCED},
    {"id": "insurance_underwriting_report", "name": "Insurance Underwriting Report",
     "category": CAT_WORKPRODUCT, "silo": "enhancement", "owner": "VENDOR",
     "requires": ["feasibility_study"], "only_if": COND_ENHANCED},
    {"id": "enhancement_term_sheet", "name": "Credit Enhancement Term Sheet",
     "category": CAT_WORKPRODUCT, "silo": "enhancement", "owner": "COUNTERPARTY",
     "requires": ["enhancer_info_memo"], "only_if": COND_ENHANCED},

    # ---- DOCUMENTATION
    {"id": "trust_indenture", "name": "Trust Indenture",
     "category": CAT_MASTER, "silo": "documentation", "owner": "BOND_COUNSEL",
     "requires": ["bond_counsel_engaged", "capital_stack"]},
    {"id": "supplemental_indenture", "name": "Supplemental Indenture (per series)",
     "category": CAT_MASTER, "silo": "documentation", "owner": "BOND_COUNSEL",
     "requires": ["trust_indenture"]},
    {"id": "loan_agreement", "name": "Loan Agreement (conduit)",
     "category": CAT_MASTER, "silo": "documentation", "owner": "BOND_COUNSEL",
     "requires": ["bond_counsel_engaged"], "only_if": COND_CONDUIT},
    {"id": "tax_regulatory_agreement", "name": "Tax Regulatory Agreement",
     "category": CAT_MASTER, "silo": "documentation", "owner": "BOND_COUNSEL",
     "requires": ["tax_status_determination"], "only_if": COND_TAX_EXEMPT},
    {"id": "bond_purchase_agreement", "name": "Bond Purchase Agreement",
     "category": CAT_MASTER, "silo": "documentation", "owner": "BOND_COUNSEL",
     "requires": ["trust_indenture"]},
    {"id": "mortgage_security_agreement", "name": "Mortgage and Security Agreement",
     "category": CAT_SECURITY, "silo": "documentation", "owner": "BOND_COUNSEL",
     "requires": ["site_control"], "only_if": COND_SECURED},
    {"id": "ucc_financing_statements", "name": "UCC Financing Statements",
     "category": CAT_SECURITY, "silo": "documentation", "owner": "BOND_COUNSEL",
     "requires": ["org_structure"], "only_if": COND_SECURED},
    {"id": "assignment_of_rents", "name": "Assignment of Rents and Leases",
     "category": CAT_SECURITY, "silo": "documentation", "owner": "BOND_COUNSEL",
     "requires": ["site_control"], "only_if": COND_SECURED},
    {"id": "continuing_disclosure_agreement", "name": "Continuing Disclosure Agreement",
     "category": CAT_OPERATIONAL, "silo": "documentation", "owner": "BOND_COUNSEL",
     "requires": ["bond_counsel_engaged"], "only_if": COND_PUBLIC_OFFERING},
    {"id": "construction_disbursement_agreement",
     "name": "Construction Disbursement Agreement",
     "category": CAT_OPERATIONAL, "silo": "documentation", "owner": "BOND_COUNSEL",
     "requires": ["trust_indenture"], "only_if": COND_CONSTRUCTION},
    {"id": "paying_agent_agreement", "name": "Paying Agent / Registrar Agreement",
     "category": CAT_OPERATIONAL, "silo": "documentation", "owner": "BOND_COUNSEL",
     "requires": ["trust_indenture"]},

    # ---- RATING
    {"id": "rating_info_package", "name": "Rating Agency Information Package",
     "category": CAT_WORKPRODUCT, "silo": "rating", "owner": "NEST",
     "requires": ["feasibility_study", "financial_projections"],
     "only_if": COND_RATED},
    {"id": "rating_presentation", "name": "Rating Committee Presentation",
     "category": CAT_WORKPRODUCT, "silo": "rating", "owner": "NEST",
     "requires": ["rating_info_package"], "only_if": COND_RATED},
    {"id": "indicative_rating_letter", "name": "Indicative Rating Letter",
     "category": CAT_WORKPRODUCT, "silo": "rating", "owner": "COUNTERPARTY",
     "requires": ["rating_presentation"], "only_if": COND_RATED},

    # ---- PACKAGING (the composite)
    {"id": "preliminary_official_statement",
     "name": "Preliminary Official Statement (POS / POM)",
     "category": CAT_MARKETING, "silo": "packaging", "owner": "NEST",
     "requires": ["bond_counsel_engaged"], "composite": "pom"},
    {"id": "investor_pitch_book", "name": "Investor Pitch Book",
     "category": CAT_MARKETING, "silo": "packaging", "owner": "NEST",
     "requires": ["capital_stack"]},
    {"id": "roadshow_deck", "name": "Roadshow Deck",
     "category": CAT_MARKETING, "silo": "packaging", "owner": "NEST",
     "requires": ["capital_stack"], "only_if": COND_PUBLIC_OFFERING},

    # ---- CERTIFICATION
    {"id": "permits_matrix", "name": "Permits and Approvals Matrix",
     "category": CAT_WORKPRODUCT, "silo": "certification", "owner": "NEST",
     "requires": ["permits"]},
    {"id": "conditions_precedent_checklist", "name": "Conditions Precedent Checklist",
     "category": CAT_WORKPRODUCT, "silo": "certification", "owner": "NEST",
     "requires": ["trust_indenture"]},
    {"id": "bond_ready_certification", "name": "Bond-Ready Certification",
     "category": CAT_WORKPRODUCT, "silo": "certification", "owner": "NEST",
     "requires": ["conditions_precedent_checklist"]},

    # ---- PLACEMENT
    {"id": "official_statement", "name": "Official Statement (final)",
     "category": CAT_MARKETING, "silo": "placement", "owner": "NEST",
     "requires": ["preliminary_official_statement", "priced"]},
    {"id": "comfort_letter", "name": "Comfort Letter",
     "category": CAT_OPINION, "silo": "placement", "owner": "AUDITOR",
     "requires": ["audited_financials"]},
    {"id": "auditors_consent", "name": "Auditor's Consent Letter",
     "category": CAT_OPINION, "silo": "placement", "owner": "AUDITOR",
     "requires": ["audited_financials"]},
    {"id": "underwriters_counsel_opinion", "name": "Underwriter's Counsel Opinion",
     "category": CAT_OPINION, "silo": "placement", "owner": "BOND_COUNSEL",
     "requires": ["underwriter_engaged"], "only_if": COND_PUBLIC_OFFERING},
    {"id": "order_book", "name": "Order Book and Allocation Memorandum",
     "category": CAT_WORKPRODUCT, "silo": "placement", "owner": "NEST",
     "requires": ["preliminary_official_statement"]},

    # ---- CLOSING
    {"id": "bond_counsel_opinion", "name": "Bond Counsel Opinion",
     "category": CAT_OPINION, "silo": "closing", "owner": "BOND_COUNSEL",
     "requires": ["trust_indenture"]},
    {"id": "tax_opinion", "name": "Tax Opinion",
     "category": CAT_OPINION, "silo": "closing", "owner": "BOND_COUNSEL",
     "requires": ["tax_status_determination"], "only_if": COND_TAX_EXEMPT},
    {"id": "borrowers_counsel_opinion", "name": "Borrower's Counsel Opinion",
     "category": CAT_OPINION, "silo": "closing", "owner": "COUNTERPARTY",
     "requires": ["org_structure"]},
    {"id": "trustees_counsel_opinion", "name": "Trustee's Counsel Opinion",
     "category": CAT_OPINION, "silo": "closing", "owner": "COUNTERPARTY",
     "requires": ["trust_indenture"]},
    {"id": "officers_certificate", "name": "Officer's Certificate",
     "category": CAT_CERTIFICATE, "silo": "closing", "owner": "COUNTERPARTY",
     "requires": ["org_structure"]},
    {"id": "incumbency_certificate", "name": "Incumbency Certificate",
     "category": CAT_CERTIFICATE, "silo": "closing", "owner": "COUNTERPARTY",
     "requires": ["org_structure"]},
    {"id": "tax_certificate", "name": "Tax Certificate",
     "category": CAT_CERTIFICATE, "silo": "closing", "owner": "BOND_COUNSEL",
     "requires": ["tax_status_determination"], "only_if": COND_TAX_EXEMPT},
    {"id": "receipt_cross_receipt", "name": "Receipt and Cross-Receipt",
     "category": CAT_CERTIFICATE, "silo": "closing", "owner": "COUNTERPARTY",
     "requires": ["priced"]},
    {"id": "trustee_authentication", "name": "Trustee's Certificate of Authentication",
     "category": CAT_CERTIFICATE, "silo": "closing", "owner": "COUNTERPARTY",
     "requires": ["trust_indenture"]},
    {"id": "dtc_letter", "name": "DTC Letter of Representations",
     "category": CAT_CERTIFICATE, "silo": "closing", "owner": "COUNTERPARTY",
     "requires": ["priced"], "only_if": COND_PUBLIC_OFFERING},
    {"id": "form_8038", "name": "IRS Form 8038 / 8038-G",
     "category": CAT_FILING, "silo": "closing", "owner": "BOND_COUNSEL",
     "requires": ["priced"], "only_if": COND_TAX_EXEMPT},
    {"id": "emma_filing", "name": "EMMA Filing",
     "category": CAT_FILING, "silo": "closing", "owner": "NEST",
     "requires": ["official_statement"], "only_if": COND_PUBLIC_OFFERING},
    {"id": "mortgage_recordation", "name": "Mortgage Recordation",
     "category": CAT_FILING, "silo": "closing", "owner": "BOND_COUNSEL",
     "requires": ["mortgage_security_agreement"], "only_if": COND_SECURED},
    {"id": "ucc_filings", "name": "UCC Filings",
     "category": CAT_FILING, "silo": "closing", "owner": "BOND_COUNSEL",
     "requires": ["ucc_financing_statements"], "only_if": COND_SECURED},
    {"id": "blue_sky_filings", "name": "State Securities (Blue Sky) Filings",
     "category": CAT_FILING, "silo": "closing", "owner": "BOND_COUNSEL",
     "requires": ["priced"], "only_if": COND_PUBLIC_OFFERING},
    {"id": "cusip_dtc_eligibility", "name": "CUSIP Assignment and DTC Eligibility",
     "category": CAT_FILING, "silo": "closing", "owner": "NEST",
     "requires": ["priced"]},
    {"id": "closing_binder", "name": "Closing Binder",
     "category": CAT_WORKPRODUCT, "silo": "closing", "owner": "NEST",
     "requires": ["bond_counsel_opinion", "officers_certificate"]},
]

DOC_STATUSES = ("not_started", "in_progress", "delivered", "accepted", "waived")
TERMINAL_STATUSES = ("accepted", "waived")


class DocumentPackageError(ValueError):
    """Raised on an unknown silo or document status."""


def _condition_met(cond: str | None, deal: dict) -> bool:
    """Whether the deal has the feature a conditional document hangs on."""
    if cond is None:
        return True
    if cond == COND_TAX_EXEMPT:
        return bool(deal.get("tax_exempt") or deal.get("tax_exempt_portion"))
    if cond == COND_CONDUIT:
        return bool(deal.get("conduit_issuer"))
    if cond == COND_RATED:
        return bool(deal.get("rating") or deal.get("seeking_rating"))
    if cond == COND_ENHANCED:
        return bool(deal.get("credit_enhancement")
                    or deal.get("credit_enhancement_term_sheet"))
    if cond == COND_PUBLIC_OFFERING:
        return deal.get("distribution_method", "underwritten") != "private_placement"
    if cond == COND_SECURED:
        # Real-property security is the default for project debt; a deal can
        # opt out explicitly rather than by omission.
        return deal.get("secured", True) is not False
    if cond == COND_CONSTRUCTION:
        return bool(deal.get("construction") or deal.get("project_budget"))
    return True


def _satisfied(key: str, deal: dict, statuses: dict) -> bool:
    """
    An input is satisfied by a deal fact OR by an upstream document reaching a
    terminal status. Documents feed each other -- the closing binder genuinely
    cannot exist before the opinions it contains.
    """
    if deal.get(key):
        return True
    return statuses.get(key) in TERMINAL_STATUSES


def build_package(deal: dict | None = None,
                  statuses: dict[str, str] | None = None) -> dict:
    """
    The full document package for a deal, silo by silo.

    `statuses` maps document id -> status, and is supplied by the caller. This
    module holds no state, same as every other engine here.
    """
    deal = deal or {}
    statuses = dict(statuses or {})
    for doc_id, st in statuses.items():
        if st not in DOC_STATUSES:
            raise DocumentPackageError(
                f"unknown status {st!r} for document {doc_id!r}; "
                f"expected one of {', '.join(DOC_STATUSES)}")

    # Which documents apply to this deal at all.
    applicable = [d for d in DOCUMENT_CATALOGUE
                  if _condition_met(d.get("only_if"), deal)]

    by_silo: dict[str, list[dict]] = {s: [] for s in SILO_IDS}
    for d in applicable:
        missing = [k for k in d["requires"]
                   if not _satisfied(k, deal, statuses)]
        status = statuses.get(d["id"], "not_started")
        if status in TERMINAL_STATUSES or status in ("in_progress", "delivered"):
            state = status.upper()
        elif missing:
            state = "BLOCKED"
        else:
            state = "READY"
        entry = {
            "id": d["id"],
            "name": d["name"],
            "category": d["category"],
            "owner": d["owner"],
            "status": status,
            "state": state,
            "blocked_by": missing,
            "conditional_on": d.get("only_if"),
            "composite": d.get("composite"),
        }
        if d.get("composite") == "pom":
            # The POM is not one document; it is twenty-three sections with six
            # owners. Delegate rather than pretend it is atomic.
            pom = plan_pom(deal)
            entry["composite_detail"] = {
                "section_count": pom["section_count"],
                "sections_writable_now": pom["readiness"]["sections_writable_now"],
                "sections_blocked": pom["readiness"]["sections_blocked"],
                "pct_writable": pom["readiness"]["pct_writable"],
                "nest_hours": pom["hours"]["total"],
                "drafting_model": pom["drafting_model"],
                "critical_inputs": pom["readiness"]["critical_inputs"],
            }
        by_silo[d["silo"]].append(entry)

    silos = []
    for s in SILOS:
        docs = by_silo[s["id"]]
        unmet = [k for k in s["gate_requires"]
                 if not _satisfied(k, deal, statuses)]
        done = [d for d in docs if d["status"] in TERMINAL_STATUSES]
        if not docs:
            # No applicable documents means the silo does not apply to this
            # deal -- an unenhanced deal has no enhancement silo. Reporting it
            # as LOCKED would imply work that is pending rather than absent,
            # and would drag the program percentage down for no reason.
            gate_state = "NOT_APPLICABLE"
        elif unmet:
            gate_state = "LOCKED"
        elif len(done) == len(docs):
            gate_state = "COMPLETE"
        else:
            gate_state = "OPEN"
        silos.append({
            "id": s["id"],
            "seq": s["seq"],
            "name": s["name"],
            "gate_id": s["gate_id"],
            "gate_state": gate_state,
            "gate_blocked_by": unmet,
            "document_count": len(docs),
            "documents_complete": len(done),
            "documents_ready": sum(1 for d in docs if d["state"] == "READY"),
            "documents_blocked": sum(1 for d in docs if d["state"] == "BLOCKED"),
            "pct_complete": round(len(done) / len(docs), 4) if docs else 0.0,
            "rag": _rag(len(done), len(docs), gate_state),
            "documents": docs,
        })

    total = sum(s["document_count"] for s in silos)
    complete = sum(s["documents_complete"] for s in silos)
    return {
        "silos": silos,
        "totals": {
            "documents": total,
            "complete": complete,
            "ready": sum(s["documents_ready"] for s in silos),
            "blocked": sum(s["documents_blocked"] for s in silos),
            "pct_complete": round(complete / total, 4) if total else 0.0,
            "excluded_as_inapplicable": len(DOCUMENT_CATALOGUE) - len(applicable),
        },
        "current_silo": next(
            (s["id"] for s in silos if s["gate_state"] == "OPEN"), None),
    }


def _rag(done: int, total: int, gate_state: str) -> str:
    """Red / amber / green, matching readiness_checklist.py's bands."""
    if gate_state in ("LOCKED", "NOT_APPLICABLE") or not total:
        return "GREY"
    pct = done / total
    if pct >= 0.80:
        return "GREEN"
    if pct >= 0.50:
        return "AMBER"
    return "RED"


def silo_package(silo_id: str, deal: dict | None = None,
                 statuses: dict[str, str] | None = None) -> dict:
    """One silo's package, for a drill-down view."""
    if silo_id not in SILO_IDS:
        raise DocumentPackageError(
            f"unknown silo {silo_id!r}; expected one of {', '.join(SILO_IDS)}")
    pkg = build_package(deal, statuses)
    return next(s for s in pkg["silos"] if s["id"] == silo_id)
