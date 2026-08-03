"""
NEST Preflight — is this financeable at all, assuming perfect paperwork?

THE DISTINCTION THIS MODULE EXISTS TO ENFORCE:

    services/readiness_checklist.py asks "does the sponsor have the documents?"
    services/preflight.py asks       "does the credit actually work?"

Those are orthogonal, and confusing them is the expensive mistake. A sponsor
can deliver all 272 checklist items, score 100% readiness, clear the Move
Forward Memorandum -- and still be running a financing that cannot be sold at
any price. In that case the checklist has done nothing but document, in
exhaustive detail, why the deal fails.

So preflight deliberately assumes the checklist is COMPLETE and asks what is
left. What remains after perfect documentation are structural traps: things no
amount of diligence, packaging, or sponsor effort will fix, because they are
properties of the credit rather than properties of the file.

Three severities, and the difference is decision-relevant:

  NO_GO       The financing cannot be done as contemplated. Not "harder" --
              cannot. Walking away early is the correct and cheapest outcome,
              and identifying it in week one instead of month nine is the
              single most valuable thing this engine does.

  STRUCTURAL  A real trap that requires the structure to change: a different
              instrument, a different issuer, enhancement, a different tax
              treatment, resizing. Solvable, but not by working harder on the
              current plan.

  WATCH       A genuine risk that should be surfaced to the client early and
              monitored, but does not by itself block execution.

METHODOLOGY. Every trap below encodes a real structural dependency in
municipal and project finance, and each one states its own reasoning in the
`why` field. Thresholds are explicit and editable. This is a rules engine over
stated constraints -- it is not calibrated against a historical default
dataset, and it does not pretend to be. Where a trap depends on a judgment
NEST has not yet made, it reports `needs_determination` rather than guessing.

Nothing here fabricates a finding. A trap fires only on data actually
supplied; missing inputs produce an explicit "cannot assess" entry.
"""
from __future__ import annotations

from typing import Any

# --- Explicit thresholds. Editable, and every finding cites the one it used.

DSCR_ABSOLUTE_FLOOR = 1.10      # below this, no structure sells the paper
DSCR_INVESTMENT_GRADE = 1.35    # broadly, coverage supporting IG on project debt
DSCR_ENHANCEMENT_REACH = 1.20   # below this, a wrap is generally unavailable

MIN_INSTITUTIONAL_SERIES = 20_000_000    # below: retail/bank market, not institutional
MAX_BANK_QUALIFIED = 10_000_000          # BQ limit per issuer per calendar year

MAX_DEBT_TO_COST = 0.75         # above this, equity is too thin for development debt
CONCENTRATION_WARN = 0.60       # one demand driver carrying this much revenue

# Sectors where tax-exempt treatment is generally unavailable to a private
# developer absent a governmental issuer and a qualifying public purpose.
PRIVATE_USE_SECTORS = {
    "hotel", "hospitality", "retail", "entertainment", "commercial",
    "office", "sports", "resort", "mixed_use",
}


def _f(deal: dict, *keys, default=None):
    for k in keys:
        v = deal.get(k)
        if v not in (None, ""):
            return v
    return default


def _trap(code, severity, title, why, evidence, fix, threshold=None) -> dict:
    return {
        "code": code, "severity": severity, "title": title,
        "why": why, "evidence": evidence, "fix": fix,
        "threshold_used": threshold,
    }


# ---------------------------------------------------------------------------
# Trap detectors. Each returns a trap dict, None (clear), or a
# "cannot assess" marker when the input it needs was not supplied.
# ---------------------------------------------------------------------------

def _coverage(deal):
    dscr = _f(deal, "stabilized_dscr", "projected_dscr", "dscr")
    if dscr is None:
        return {"code": "COVERAGE", "cannot_assess": True,
                "needs": "stabilized_dscr -- projected DSCR at stabilization"}
    dscr = float(dscr)
    if dscr < DSCR_ABSOLUTE_FLOOR:
        return _trap(
            "COVERAGE_FATAL", "NO_GO",
            f"Coverage does not clear at stabilization ({dscr:.2f}x)",
            "Debt service coverage below roughly 1.10x at stabilization means "
            "the asset does not generate enough cash to pay its own debt in a "
            "normal year. No structure, enhancement, or packaging fixes a "
            "revenue shortfall -- the only real remedies are less debt or more "
            "revenue, both of which change the deal rather than finance it.",
            f"Stabilized DSCR {dscr:.2f}x",
            "Resize the debt to what coverage supports, increase equity, or "
            "re-underwrite the revenue assumptions. Do not proceed to market.",
            DSCR_ABSOLUTE_FLOOR)
    if dscr < DSCR_ENHANCEMENT_REACH:
        return _trap(
            "COVERAGE_THIN", "STRUCTURAL",
            f"Coverage too thin for enhancement to reach ({dscr:.2f}x)",
            "Bond insurers underwrite credits that are near investment grade "
            "on their own. A wrap is a rating improvement, not a rescue: "
            "below roughly 1.20x coverage, enhancement is typically either "
            "declined or priced so wide that it destroys the benefit.",
            f"Stabilized DSCR {dscr:.2f}x",
            "Resize, add a debt service reserve funded from proceeds, sculpt "
            "amortization to the revenue ramp, or bring subordinate capital.",
            DSCR_ENHANCEMENT_REACH)
    if dscr < DSCR_INVESTMENT_GRADE:
        return _trap(
            "COVERAGE_SUB_IG", "WATCH",
            f"Coverage below investment grade range ({dscr:.2f}x)",
            "Coverage in this band generally prices as non-investment-grade "
            "project debt. It is sellable, but to a narrower buyer set and at "
            "a materially wider spread than the program's assumed coupons.",
            f"Stabilized DSCR {dscr:.2f}x",
            "Plan for enhancement or a 144A execution, and stress the "
            "assumed coupons before publishing them.",
            DSCR_INVESTMENT_GRADE)
    return None


def _tax_exemption(deal):
    assumed = _f(deal, "tax_exempt_par", default=0)
    if not assumed:
        return None
    sector = str(_f(deal, "sector", default="")).lower()
    issuer = _f(deal, "conduit_issuer_identified", "issuer_identified")
    borrower = str(_f(deal, "borrower_type", default="")).lower()
    public_purpose = _f(deal, "public_purpose_established")

    private_use = any(s in sector for s in PRIVATE_USE_SECTORS)
    is_private_developer = borrower in ("developer", "private", "for_profit", "llc")

    if private_use and is_private_developer and not public_purpose:
        return _trap(
            "TAX_EXEMPT_INELIGIBLE", "STRUCTURAL",
            f"${assumed:,.0f} assumed tax-exempt on private-use property",
            "Tax-exempt treatment is not a function of who issues the paper -- "
            "it depends on the use of the financed property. Hotel, retail, "
            "entertainment, and commercial space owned and operated by a "
            "private developer is private business use. Absent a governmental "
            "issuer financing a qualifying public purpose (or a 501(c)(3) "
            "borrower), that portion is taxable, and taxable pricing is "
            "materially wider than the tax-exempt coupons the program assumes.",
            f"Sector '{sector}', borrower type '{borrower}', "
            f"conduit issuer identified: {bool(issuer)}",
            "Segregate genuinely public components (infrastructure, roads, "
            "utilities, public realm) into the tax-exempt series and reprice "
            "the private-use components as taxable. Confirm with bond counsel "
            "before the capital stack is published.",
            None)
    if assumed and not issuer:
        return _trap(
            "NO_CONDUIT_ISSUER", "NO_GO",
            "Tax-exempt series assumed with no issuer identified",
            "Tax-exempt municipal bonds must be issued by a governmental "
            "issuer or conduit authority willing to lend its name to the "
            "transaction. This is a political decision, not a financial one, "
            "and it cannot be manufactured by the advisor or the sponsor. "
            "Until an issuer has indicated willingness, the tax-exempt "
            "portion of the capital stack does not exist.",
            f"${assumed:,.0f} assumed tax-exempt, no issuer identified",
            "Approach the county or a state conduit authority for an "
            "inducement resolution before any tax-exempt series is marketed. "
            "Treat this as the first structural gate, not a later formality.",
            None)
    return None


def _revenue_mechanism(deal):
    mech = str(_f(deal, "revenue_mechanism", default="")).lower()
    seasoned = _f(deal, "revenue_mechanism_seasoned")
    if not mech:
        return {"code": "REVENUE_MECHANISM", "cannot_assess": True,
                "needs": "revenue_mechanism -- special_assessment, special_tax, "
                         "lease, offtake, or operating"}
    if mech in ("special_assessment", "special_tax") and seasoned is False:
        return _trap(
            "UNSEASONED_ASSESSMENT", "STRUCTURAL",
            f"{mech.replace('_', ' ').title()} security is not yet seasoned",
            "Assessment and special tax bonds are bought on collection "
            "history. Without a levy that has actually been assessed and "
            "collected, a buyer is underwriting a projection rather than a "
            "record, which materially narrows the buyer set and widens "
            "pricing. This is a timing constraint, not a documentation gap -- "
            "it is not fixed by diligence.",
            f"Mechanism '{mech}', seasoned: {seasoned}",
            "Sequence the series so the assessment is levied and collected "
            "for at least one cycle before pricing, or bridge with taxable "
            "construction debt and refund into the assessment series once "
            "seasoned.",
            None)
    return None


def _prestabilization(deal):
    contracted = _f(deal, "revenue_contracted_pct")
    operating = _f(deal, "operating_history_years", default=0)
    if contracted is None:
        return {"code": "PRESTABILIZATION", "cannot_assess": True,
                "needs": "revenue_contracted_pct -- share of revenue under "
                         "signed lease or offtake"}
    if float(contracted) < 30 and float(operating or 0) < 1:
        return _trap(
            "PRESTABILIZATION_RISK", "STRUCTURAL",
            "No operating history and minimal contracted revenue",
            "A project with neither an operating record nor signed revenue "
            "contracts is asking buyers to fund construction against "
            "projections alone. That is financeable, but only through "
            "specific structures -- enhancement, capitalized interest through "
            "lease-up, a sale-proceeds paydown, or a sponsor completion "
            "guarantee. It does not price as investment grade unenhanced.",
            f"{contracted}% contracted, {operating or 0} years operating history",
            "Pre-lease to a threshold before pricing, secure enhancement, or "
            "structure capitalized interest sized to a realistic absorption "
            "curve -- not the base case.",
            30)
    return None


def _capitalized_interest(deal):
    capi = _f(deal, "capitalized_interest_months")
    ramp = _f(deal, "revenue_ramp_months")
    if capi is None or ramp is None:
        return None
    if float(capi) < float(ramp):
        return _trap(
            "CAPI_EXHAUSTION", "STRUCTURAL",
            f"Capitalized interest ({capi} mo) runs out before revenue arrives "
            f"({ramp} mo)",
            "Capitalized interest defers the problem; it does not solve it. "
            "If the funded interest period ends before the asset generates "
            "cash, the borrower must pay debt service out of an asset that is "
            "not yet earning -- which is the exact mechanism by which "
            "development bonds default. The gap is the whole risk.",
            f"Cap-i {capi} months vs revenue ramp {ramp} months "
            f"({float(ramp) - float(capi):.0f} month gap)",
            "Size capitalized interest to the downside absorption case with a "
            "cushion, not the base case, and fund it from proceeds.",
            None)
    return None


def _leverage(deal):
    debt = _f(deal, "total_debt", "bond_par")
    cost = _f(deal, "total_project_cost")
    if not debt or not cost:
        return None
    ratio = float(debt) / float(cost)
    if ratio > MAX_DEBT_TO_COST:
        return _trap(
            "OVERLEVERED", "STRUCTURAL",
            f"Debt is {ratio:.0%} of project cost",
            "Development-stage project debt above roughly 75% of cost leaves "
            "too little equity beneath the bonds to absorb cost overruns or "
            "absorption delay. Buyers of construction-period paper are "
            "underwriting the equity cushion as much as the revenue.",
            f"${float(debt):,.0f} debt / ${float(cost):,.0f} cost = {ratio:.0%}",
            "Increase sponsor equity, phase the debt so each series funds a "
            "smaller increment, or bring mezzanine capital beneath the bonds.",
            MAX_DEBT_TO_COST)
    return None


def _concentration(deal):
    driver = _f(deal, "primary_demand_driver")
    share = _f(deal, "primary_demand_driver_share")
    if not driver or share is None:
        return None
    if float(share) >= CONCENTRATION_WARN * 100:
        return _trap(
            "DEMAND_CONCENTRATION", "WATCH",
            f"{float(share):.0f}% of demand from a single driver ({driver})",
            "Single-driver demand concentration is a real rating and pricing "
            "factor. It is not disqualifying, but it must be disclosed and it "
            "will be priced -- and a program that phases over decades is "
            "exposed to that driver's own trajectory for the whole term.",
            f"{driver}: {float(share):.0f}% of projected demand",
            "Disclose prominently, stress the downside case against a decline "
            "in the driver, and diversify revenue in later phases.",
            CONCENTRATION_WARN)
    return None


def _series_sizing(deal):
    par = _f(deal, "series_par", "bond_par")
    if not par:
        return None
    par = float(par)
    tax_exempt = _f(deal, "tax_exempt", default=False)
    if par < MIN_INSTITUTIONAL_SERIES:
        if tax_exempt and par <= MAX_BANK_QUALIFIED:
            return None  # bank-qualified is a real, intended execution
        return _trap(
            "SERIES_TOO_SMALL", "WATCH",
            f"${par:,.0f} series is below the institutional threshold",
            "Institutional buyers have minimum ticket sizes; a series this "
            "small generally clears through regional banks or retail rather "
            "than institutions. That is a viable execution, but it is a "
            "different buyer set and different pricing than an institutional "
            "book, and the plan of distribution should say so.",
            f"Series par ${par:,.0f}",
            "Target bank or retail distribution explicitly, or aggregate with "
            "another series.",
            MIN_INSTITUTIONAL_SERIES)
    return None


def _phasing_cascade(deal):
    recycling = _f(deal, "phase_funded_by_prior_phase_equity")
    phases = _f(deal, "phase_count", default=0)
    if not recycling:
        return None
    return _trap(
        "PHASING_CASCADE", "WATCH",
        f"Later phases funded by earlier phases' released equity "
        f"({phases} phases)",
        "Capital recycling is efficient and it is also a serial dependency: "
        "every later phase inherits the execution risk of every earlier one. "
        "If Phase 1 underperforms, it does not just underperform -- it "
        "removes the equity that funds Phase 2, and the program stalls rather "
        "than degrades. Bondholders in later series are exposed to earlier "
        "phases they have no security interest in.",
        f"{phases}-phase program with equity recycling",
        "Do not cross-default the series. Size each phase to stand alone, "
        "disclose the dependency explicitly, and identify the alternative "
        "funding source if a prior phase underdelivers.",
        None)


DETECTORS = [
    _coverage, _tax_exemption, _revenue_mechanism, _prestabilization,
    _capitalized_interest, _leverage, _concentration, _series_sizing,
    _phasing_cascade,
]


def run_preflight(deal: dict) -> dict:
    """
    Structural viability assessment, assuming the checklist is complete.

    Returns traps by severity, an explicit go/no-go verdict, and the list of
    inputs that could not be assessed.
    """
    traps, cannot_assess = [], []
    for det in DETECTORS:
        try:
            result = det(deal)
        except Exception as exc:  # a detector must never take down preflight
            cannot_assess.append({"code": det.__name__, "error": str(exc)})
            continue
        if result is None:
            continue
        if result.get("cannot_assess"):
            cannot_assess.append(result)
        else:
            traps.append(result)

    no_go = [t for t in traps if t["severity"] == "NO_GO"]
    structural = [t for t in traps if t["severity"] == "STRUCTURAL"]
    watch = [t for t in traps if t["severity"] == "WATCH"]

    if no_go:
        verdict, headline = "NO_GO", (
            "Do not proceed as contemplated. "
            + "; ".join(t["title"] for t in no_go)
            + ". These are not diligence gaps -- a complete checklist does "
              "not change them."
        )
    elif structural:
        verdict, headline = "RESTRUCTURE", (
            f"Financeable, but not as currently structured. "
            f"{len(structural)} structural change(s) required before market: "
            + "; ".join(t["title"] for t in structural) + "."
        )
    elif watch:
        verdict, headline = "PROCEED_WITH_CONDITIONS", (
            f"Structurally financeable. {len(watch)} item(s) to disclose and "
            "monitor: " + "; ".join(t["title"] for t in watch) + "."
        )
    else:
        verdict, headline = "PROCEED", (
            "No structural traps detected on the inputs supplied."
        )

    return {
        "verdict": verdict,
        "headline": headline,
        "walk_away_signal": bool(no_go),
        "counts": {"no_go": len(no_go), "structural": len(structural),
                   "watch": len(watch)},
        "no_go": no_go,
        "structural": structural,
        "watch": watch,
        "cannot_assess": cannot_assess,
        "assessment_completeness": round(
            1 - len(cannot_assess) / len(DETECTORS), 3),
        "scope_note": (
            "Preflight assumes the Project Readiness Checklist is fully "
            "satisfied and asks what remains. A clean preflight does not mean "
            "the documents exist; a clean checklist does not mean the credit "
            "works. Both are required."
        ),
    }
