"""
NEST Stairway — codename "Stairway to Heaven". The pathway to financeable.

services/preflight.py tells a client what is wrong. On its own that is a
diagnosis without a treatment, and "not financeable" is almost never the whole
truth. Nearly every deal has a pathway; what differs is the cost of that
pathway, how long it takes, and how much of it the client actually controls.

This module maps that pathway. For each trap preflight found, it produces the
concrete remediation steps, who owns each one, what it costs, how long it
takes, what it unlocks, and what it depends on. Then it sequences them into a
critical path and scores whether the pathway is realistically walkable.

THE HONESTY THAT MAKES THIS USEFUL RATHER THAN SALES COPY:

1. CONTROL IS REPORTED SEPARATELY FROM EFFORT. A step the sponsor can execute
   by writing a check is fundamentally different from one requiring a county
   board to pass an inducement resolution. Both appear on the path; only one
   is within anyone's control. The feasibility score is driven by that split,
   not by step count.

2. SOME PATHWAYS LEAD TO A DIFFERENT DEAL. If coverage requires cutting debt
   40%, the pathway exists -- but what emerges is not the transaction the
   client brought in. That is stated plainly as `changes_the_deal`, because a
   client who is told "there's a path" and later discovers the path led
   somewhere else was misled.

3. COSTS ARE PLANNING ESTIMATES, NOT QUOTES. Every cost carries a range and a
   provenance tag, the same discipline preflight uses for thresholds. NEST has
   not procured these services at scale and does not have real vendor pricing.
   Anything shown to a client must say so.

Nothing here promises an outcome. A pathway is a plan, and the brief says so.
"""
from __future__ import annotations

from typing import Any

# Who has to act. This drives the feasibility score, because a pathway made of
# steps nobody controls is not a pathway.
CONTROL = {
    "SPONSOR": "Client can execute directly -- money and decision are theirs.",
    "NEST": "NEST executes as part of the engagement.",
    "VENDOR": "Procurable from a third party for a fee. Reliable, just costs.",
    "COUNTERPARTY": "Requires another commercial party to agree. Negotiable "
                    "but not controllable.",
    "GOVERNMENTAL": "Requires a public body to act. Political, not financial "
                    "-- cannot be bought or accelerated with certainty.",
    "MARKET": "Depends on conditions nobody controls.",
}

# Steps by control type, scored for how reliably they can actually be walked.
CONTROL_RELIABILITY = {
    "SPONSOR": 0.95, "NEST": 0.95, "VENDOR": 0.90,
    "COUNTERPARTY": 0.65, "GOVERNMENTAL": 0.50, "MARKET": 0.55,
}

# Planning cost ranges in USD. HAND_SET -- NEST has not procured these at
# scale. They exist so a brief can carry an order of magnitude, and every one
# is labeled as an estimate wherever it surfaces.
COST_PROVENANCE = "HAND_SET_PLANNING_ESTIMATE"


def _step(sid, action, control, cost_low, cost_high, weeks_low, weeks_high,
          unlocks, why, depends_on=None, changes_the_deal=False, note=None,
          alternative_to=None):
    return {
        # Steps that are OR-branches, not additional requirements. Modeling an
        # alternative as mandatory compounds risk from a step the client would
        # never take -- it made a bridgeable seasoning constraint read as if
        # the governmental route were unavoidable.
        "alternative_to": alternative_to or [],
        "id": sid,
        "action": action,
        "control": control,
        "control_meaning": CONTROL[control],
        "cost_usd_range": [cost_low, cost_high],
        "cost_provenance": COST_PROVENANCE,
        "duration_weeks_range": [weeks_low, weeks_high],
        "unlocks": unlocks,
        "why": why,
        "depends_on": depends_on or [],
        "changes_the_deal": changes_the_deal,
        "note": note,
        "reliability": CONTROL_RELIABILITY[control],
    }


# ---------------------------------------------------------------------------
# Remediation builders, one per trap code. Each returns the ordered steps that
# actually clear that trap. Several are deal-aware and quantify the gap.
# ---------------------------------------------------------------------------

def _fix_coverage_fatal(deal, trap):
    from services.preflight import DSCR_ABSOLUTE_FLOOR, DSCR_INVESTMENT_GRADE
    dscr = float(deal.get("stabilized_dscr") or deal.get("projected_dscr") or 0)
    debt = float(deal.get("total_debt") or deal.get("bond_par") or 0)
    steps = []

    # Quantify the actual gap rather than saying "reduce debt".
    resize_note = None
    if dscr > 0 and debt > 0:
        target = DSCR_INVESTMENT_GRADE
        supportable = debt * (dscr / target)
        reduction = debt - supportable
        resize_note = (
            f"At {dscr:.2f}x on ${debt:,.0f} of debt, the revenue supports "
            f"about ${supportable:,.0f} at a {target:.2f}x target -- a "
            f"reduction of ${reduction:,.0f} ({reduction/debt:.0%}). That gap "
            f"must be closed by less debt, more equity, or more revenue."
        )

    steps.append(_step(
        "COV-1", "Re-underwrite the revenue model against independent feasibility",
        "VENDOR", 75_000, 250_000, 8, 16, ["COVERAGE_FATAL", "COVERAGE_THIN"],
        "Coverage this thin is usually a projection problem before it is a "
        "structure problem. An independent feasibility study either supports "
        "the revenue or establishes that it does not -- and that answer "
        "determines whether the rest of the pathway is worth walking.",
        note=resize_note))
    steps.append(_step(
        "COV-2", "Resize the debt to supportable coverage", "NEST",
        0, 0, 2, 4, ["COVERAGE_FATAL"],
        "Sizing to what the revenue actually covers is the only remedy that "
        "always works. It reduces proceeds, which is why it is resisted, but "
        "no enhancement or packaging substitutes for coverage.",
        depends_on=["COV-1"], changes_the_deal=True,
        note="Reduces proceeds. The financing that results is smaller than "
             "the one contemplated."))
    steps.append(_step(
        "COV-3", "Increase sponsor equity or bring subordinate capital",
        "SPONSOR", 0, 0, 8, 26, ["COVERAGE_FATAL", "OVERLEVERED"],
        "The alternative to less debt is more equity beneath it. This keeps "
        "project scope intact but dilutes sponsor returns.",
        depends_on=["COV-1"], changes_the_deal=True))
    return steps


def _fix_coverage_thin(deal, trap):
    return [
        _step("CVT-1", "Fund a debt service reserve from bond proceeds", "NEST",
              0, 0, 2, 4, ["COVERAGE_THIN"],
              "A funded DSRF is the standard structural answer to thin "
              "coverage. It does not create revenue, but it gives buyers a "
              "cushion against timing mismatches and is expected on project "
              "revenue credits."),
        _step("CVT-2", "Sculpt amortization to the revenue ramp", "NEST",
              0, 0, 2, 4, ["COVERAGE_THIN"],
              "Level debt service against a ramping revenue curve manufactures "
              "a coverage shortfall in early years that does not reflect the "
              "asset. Sculpting to the actual curve raises minimum coverage "
              "without changing total debt."),
        _step("CVT-3", "Obtain enhancement indication once coverage clears 1.20x",
              "COUNTERPARTY", 0, 0, 6, 12, ["COVERAGE_THIN"],
              "Enhancement is a rating improvement, not a rescue. Approach "
              "only after the structural fixes above have moved coverage into "
              "reach, or the file gets a declination on record.",
              depends_on=["CVT-1", "CVT-2"]),
    ]


def _fix_tax_exempt(deal, trap):
    return [
        _step("TAX-1", "Bond counsel tax analysis and component-level opinion",
              "VENDOR", 50_000, 150_000, 4, 10, ["TAX_EXEMPT_INELIGIBLE"],
              "Tax-exempt eligibility turns on the use of the financed "
              "property, not on who issues the paper. Only bond counsel can "
              "resolve which components qualify, and that opinion has to "
              "exist before the capital stack is published -- not after a "
              "buyer's counsel finds the problem."),
        _step("TAX-2", "Bifurcate the capital stack into qualifying and taxable "
              "components", "NEST", 0, 0, 3, 6, ["TAX_EXEMPT_INELIGIBLE"],
              "Genuinely public components -- roads, utilities, public realm, "
              "municipal campus -- can carry tax-exempt debt. Private "
              "commercial space generally cannot. Splitting them is the fix; "
              "the cost is that the private portion reprices to taxable.",
              depends_on=["TAX-1"], changes_the_deal=True,
              note="Repricing the private components to taxable materially "
                   "raises blended cost of funds. Model this before it is "
                   "presented as a solved problem."),
        _step("TAX-3", "Re-run pricing on the bifurcated stack", "NEST",
              0, 0, 1, 3, ["TAX_EXEMPT_INELIGIBLE"],
              "The whole point of the exercise is knowing the real blended "
              "cost. Publish the corrected number, not the original.",
              depends_on=["TAX-2"]),
    ]


def _fix_no_issuer(deal, trap):
    return [
        _step("ISS-1", "Identify candidate conduit issuers and confirm programs",
              "NEST", 0, 0, 2, 4, ["NO_CONDUIT_ISSUER"],
              "County authorities, state conduit authorities and development "
              "finance corporations each have their own eligible-project "
              "rules. Establishing which will even consider the project is "
              "the first gate."),
        _step("ISS-2", "Secure an inducement resolution from the issuer",
              "GOVERNMENTAL", 15_000, 75_000, 8, 26, ["NO_CONDUIT_ISSUER"],
              "This is a political decision by a public body, not a financial "
              "one. It cannot be bought, and it cannot be reliably "
              "accelerated. Until it exists, the tax-exempt portion of the "
              "capital stack does not exist either.",
              depends_on=["ISS-1"],
              note="The single least controllable step on most pathways. "
                   "Start it first regardless of where it sits in the plan."),
        _step("ISS-3", "Fallback: restructure fully taxable", "NEST",
              0, 0, 2, 4, ["NO_CONDUIT_ISSUER"],
              "If no issuer is willing, the deal is still financeable as a "
              "taxable transaction -- at a materially wider coupon. This is "
              "the pathway that always exists, and it should be priced up "
              "front so the client knows the cost of the political risk.",
              depends_on=["ISS-1"], changes_the_deal=True,
              alternative_to=["ISS-2"]),
    ]


def _fix_unseasoned(deal, trap):
    return [
        _step("SEA-1", "Levy the assessment or special tax", "GOVERNMENTAL",
              25_000, 100_000, 12, 40, ["UNSEASONED_ASSESSMENT"],
              "The district has to be formed and the levy actually imposed "
              "before there is anything to season. This is public process."),
        _step("SEA-2", "Collect at least one full cycle", "GOVERNMENTAL",
              0, 0, 52, 104, ["UNSEASONED_ASSESSMENT"],
              "Assessment and special tax bonds are bought on collection "
              "history. One cycle of actual collections converts a projection "
              "into a record, which is what widens the buyer set.",
              depends_on=["SEA-1"],
              note="This is a calendar constraint. It cannot be shortened by "
                   "spending money or working harder."),
        _step("SEA-3", "Alternative: bridge with taxable construction debt, "
              "refund into the assessment series once seasoned", "NEST",
              0, 0, 4, 8, ["UNSEASONED_ASSESSMENT"],
              "The standard way around the calendar. Costs more in the "
              "interim -- taxable construction pricing for the bridge period "
              "-- but it removes seasoning from the critical path entirely.",
              alternative_to=["SEA-1", "SEA-2"],
              note="Usually the right answer when the calendar is the binding "
                   "constraint. Price the carry before committing."),
    ]


def _fix_prestabilization(deal, trap):
    return [
        _step("PRE-1", "Pre-lease or contract revenue to a stated threshold",
              "COUNTERPARTY", 0, 0, 26, 78, ["PRESTABILIZATION_RISK"],
              "Signed revenue is what converts a projection into an "
              "underwritable credit. Nothing else in this list substitutes "
              "for it; the others only manage the gap until it exists."),
        _step("PRE-2", "Verify offtaker or anchor tenant creditworthiness",
              "NEST", 0, 0, 2, 6, ["PRESTABILIZATION_RISK"],
              "Contracted revenue is only as good as who signed it. Buyers "
              "will underwrite the counterparty, so NEST should first.",
              depends_on=["PRE-1"]),
        _step("PRE-3", "Size capitalized interest to the downside absorption "
              "case", "NEST", 0, 0, 2, 4,
              ["PRESTABILIZATION_RISK", "CAPI_EXHAUSTION"],
              "Cap-i sized to the base case is the mechanism by which "
              "development bonds default. Size to the downside curve and fund "
              "it from proceeds."),
        _step("PRE-4", "Obtain a sponsor completion guarantee", "SPONSOR",
              0, 0, 4, 10, ["PRESTABILIZATION_RISK"],
              "Puts sponsor balance sheet behind construction completion, "
              "which is the risk buyers price hardest pre-stabilization."),
    ]


def _fix_capi(deal, trap):
    capi = float(deal.get("capitalized_interest_months") or 0)
    ramp = float(deal.get("revenue_ramp_months") or 0)
    gap = max(0.0, ramp - capi)
    ds = float(deal.get("annual_debt_service") or 0)
    extra = (ds * (gap / 12.0)) if ds else None
    return [
        _step("CAP-1", f"Extend capitalized interest by at least {gap:.0f} months "
              f"plus a downside cushion", "NEST", 0, 0, 2, 4,
              ["CAPI_EXHAUSTION"],
              "Capitalized interest defers the problem, it does not solve it. "
              "If funded interest ends before the asset earns, the borrower "
              "pays debt service out of an asset that is not yet earning -- "
              "which is how these deals default. Close the gap and add "
              "cushion for absorption slipping.",
              note=(f"Additional proceeds required: roughly ${extra:,.0f} at "
                    f"stated debt service, before cushion."
                    if extra else
                    "Supply annual_debt_service to size the additional "
                    "proceeds required.")),
        _step("CAP-2", "Re-test the absorption curve against the downside case",
              "VENDOR", 25_000, 75_000, 4, 8, ["CAPI_EXHAUSTION"],
              "The gap is only as trustworthy as the ramp assumption behind "
              "it. An independent absorption view is what makes the extended "
              "cap-i period defensible to a buyer.",
              depends_on=["CAP-1"]),
    ]


def _fix_overlevered(deal, trap):
    return [
        _step("LEV-1", "Increase sponsor equity contribution", "SPONSOR",
              0, 0, 8, 26, ["OVERLEVERED"],
              "Buyers of construction-period paper underwrite the equity "
              "cushion as much as the revenue. Thin equity means overruns and "
              "absorption delay land directly on bondholders.",
              changes_the_deal=True),
        _step("LEV-2", "Introduce mezzanine or preferred capital beneath the "
              "bonds", "COUNTERPARTY", 0, 0, 12, 26, ["OVERLEVERED"],
              "Achieves the same cushion without sponsor cash, at a higher "
              "blended cost.", alternative_to=["LEV-1"]),
        _step("LEV-3", "Phase the debt into smaller increments", "NEST",
              0, 0, 3, 6, ["OVERLEVERED"],
              "Each series funds a smaller increment against proven progress, "
              "which lowers effective leverage at any point in time."),
    ]


def _fix_concentration(deal, trap):
    return [
        _step("CON-1", "Stress the downside against a decline in the primary "
              "driver", "NEST", 0, 0, 2, 4, ["DEMAND_CONCENTRATION"],
              "Concentration is priced, not prohibited. What buyers punish is "
              "concentration that has not been stressed and disclosed."),
        _step("CON-2", "Disclose prominently in the offering document", "NEST",
              0, 0, 1, 2, ["DEMAND_CONCENTRATION"],
              "A risk factor found by a buyer is worth far more spread than "
              "one disclosed by the issuer.",
              depends_on=["CON-1"]),
        _step("CON-3", "Diversify revenue in later phases", "SPONSOR",
              0, 0, 52, 156, ["DEMAND_CONCENTRATION"],
              "Structural, long-dated, and the only real remedy rather than "
              "a disclosure."),
    ]


def _fix_series_size(deal, trap):
    return [
        _step("SIZ-1", "Target bank-qualified or regional bank distribution",
              "NEST", 0, 0, 2, 6, ["SERIES_TOO_SMALL"],
              "A small series is not a defect, it is a different buyer set. "
              "Say so in the plan of distribution rather than marketing it "
              "into an institutional book that will not take it."),
        _step("SIZ-2", "Aggregate with an adjacent series", "NEST",
              0, 0, 3, 8, ["SERIES_TOO_SMALL"],
              "Combining series reaches institutional ticket size, at the "
              "cost of tying two phases' timing together.",
              changes_the_deal=True),
    ]


def _fix_phasing(deal, trap):
    return [
        _step("PHA-1", "Size each phase to stand alone without prior-phase "
              "equity", "NEST", 0, 0, 4, 8, ["PHASING_CASCADE"],
              "Capital recycling is efficient and it is also a serial "
              "dependency. If a phase underperforms it does not merely "
              "underperform -- it removes the equity funding the next phase, "
              "and the program stalls rather than degrades.",
              changes_the_deal=True),
        _step("PHA-2", "Do not cross-default the series", "NEST",
              0, 0, 1, 2, ["PHASING_CASCADE"],
              "Later bondholders should not be exposed to earlier phases they "
              "hold no security interest in. This is a drafting decision with "
              "large consequences."),
        _step("PHA-3", "Identify committed alternative funding if a prior "
              "phase underdelivers", "SPONSOR", 0, 0, 8, 20,
              ["PHASING_CASCADE"],
              "The disclosure question every buyer will ask: what funds Phase "
              "N+1 if Phase N releases less equity than modeled?"),
    ]


BUILDERS = {
    "COVERAGE_FATAL": _fix_coverage_fatal,
    "COVERAGE_THIN": _fix_coverage_thin,
    "COVERAGE_SUB_IG": _fix_coverage_thin,
    "TAX_EXEMPT_INELIGIBLE": _fix_tax_exempt,
    "NO_CONDUIT_ISSUER": _fix_no_issuer,
    "UNSEASONED_ASSESSMENT": _fix_unseasoned,
    "PRESTABILIZATION_RISK": _fix_prestabilization,
    "CAPI_EXHAUSTION": _fix_capi,
    "OVERLEVERED": _fix_overlevered,
    "DEMAND_CONCENTRATION": _fix_concentration,
    "SERIES_TOO_SMALL": _fix_series_size,
    "PHASING_CASCADE": _fix_phasing,
}


def build_pathway(deal: dict, preflight_result: dict | None = None) -> dict:
    """
    Map the pathway from where this deal stands to financeable.

    Returns the ordered steps, cost and duration ranges, a feasibility score,
    and an explicit statement of what the client does and does not control.
    """
    if preflight_result is None:
        from services.preflight import run_preflight
        preflight_result = run_preflight(deal)

    traps = (preflight_result.get("no_go", [])
             + preflight_result.get("structural", [])
             + preflight_result.get("watch", []))

    steps: list[dict] = []
    seen: set[str] = set()
    for trap in traps:
        builder = BUILDERS.get(trap["code"])
        if not builder:
            continue
        for st in builder(deal, trap):
            if st["id"] in seen:
                continue
            seen.add(st["id"])
            st["addresses"] = trap["code"]
            st["severity"] = trap["severity"]
            steps.append(st)

    if not steps:
        return {
            "codename": "Stairway",
            "pathway_exists": True,
            "steps": [],
            "verdict": "NO_REMEDIATION_REQUIRED",
            "brief": "Preflight found no structural traps on the inputs "
                     "supplied. There is nothing to remediate.",
        }

    # Order: severity first, then dependencies before dependents.
    sev_rank = {"NO_GO": 0, "STRUCTURAL": 1, "WATCH": 2}
    steps.sort(key=lambda s: (sev_rank.get(s["severity"], 3), len(s["depends_on"])))
    for i, s in enumerate(steps, 1):
        s["sequence"] = i

    cost_low = sum(s["cost_usd_range"][0] for s in steps)
    cost_high = sum(s["cost_usd_range"][1] for s in steps)

    # Duration is not the sum -- much runs in parallel. The honest figure is
    # the longest dependent chain, which is what actually gates the timeline.
    by_id = {s["id"]: s for s in steps}

    def chain_weeks(step, idx=1):
        own = step["duration_weeks_range"][idx]
        deps = [chain_weeks(by_id[d], idx) for d in step["depends_on"] if d in by_id]
        return own + (max(deps) if deps else 0)

    crit_low = max(chain_weeks(s, 0) for s in steps)
    crit_high = max(chain_weeks(s, 1) for s in steps)

    controls: dict[str, int] = {}
    for s in steps:
        controls[s["control"]] = controls.get(s["control"], 0) + 1

    uncontrollable = [s for s in steps
                      if s["control"] in ("GOVERNMENTAL", "MARKET")
                      and s["id"] not in {sid for x in steps
                                          for sid in x["alternative_to"]}]
    deal_changing = [s for s in steps if s["changes_the_deal"]]

    # Feasibility over REQUIRED steps only. A step with a stated alternative
    # is not required -- the client takes whichever branch is more reliable,
    # so the pathway inherits the better of the two, not the product of both.
    superseded = {sid for s in steps for sid in s["alternative_to"]}
    required = [s for s in steps if s["id"] not in superseded]

    # Where an alternative exists, credit the more reliable branch.
    for alt in [s for s in steps if s["alternative_to"]]:
        replaced = [s for s in steps if s["id"] in alt["alternative_to"]]
        if replaced and alt["reliability"] > min(r["reliability"] for r in replaced):
            alt["supersedes_note"] = (
                "Removes " + ", ".join(r["id"] for r in replaced) +
                " from the critical path -- those depend on public process "
                "that cannot be accelerated."
            )

    score = 1.0
    for s in required:
        score *= s["reliability"]
    best = 0.95 ** len(required)
    feasibility = min(1.0, score / best) if best else 0.0

    if feasibility >= 0.75:
        verdict = "CLEAR_PATHWAY"
    elif feasibility >= 0.45:
        verdict = "PATHWAY_WITH_EXTERNAL_DEPENDENCIES"
    else:
        verdict = "PATHWAY_DEPENDS_ON_FACTORS_OUTSIDE_CLIENT_CONTROL"

    brief = _brief(steps, cost_low, cost_high, crit_low, crit_high,
                   uncontrollable, deal_changing, feasibility, verdict)

    return {
        "codename": "Stairway",
        "pathway_exists": True,
        "verdict": verdict,
        "feasibility_score": round(feasibility, 3),
        "step_count": len(steps),
        "cost_usd_range": [cost_low, cost_high],
        "cost_provenance": COST_PROVENANCE,
        "critical_path_weeks_range": [crit_low, crit_high],
        "critical_path_months_range": [round(crit_low / 4.33, 1),
                                       round(crit_high / 4.33, 1)],
        "control_breakdown": controls,
        "required_step_count": len(required),
        "steps_avoidable_via_alternative": [
            {"id": s["id"], "action": s["action"],
             "superseded_by": [a["id"] for a in steps
                               if s["id"] in a["alternative_to"]]}
            for s in steps if s["id"] in superseded
        ],
        "steps_outside_client_control": [
            {"id": s["id"], "action": s["action"], "control": s["control"],
             "why_it_matters": s["control_meaning"]}
            for s in uncontrollable
        ],
        "steps_that_change_the_deal": [
            {"id": s["id"], "action": s["action"], "note": s["note"]}
            for s in deal_changing
        ],
        "steps": steps,
        "brief": brief,
        "disclaimer": (
            "Costs are planning estimates, not quotes -- NEST has not procured "
            "these services at scale and holds no vendor pricing. Durations "
            "assume normal process and no appeal or contested proceeding. A "
            "pathway is a plan, not a commitment that the financing closes."
        ),
    }


def _brief(steps, cost_low, cost_high, crit_low, crit_high,
           uncontrollable, deal_changing, feasibility, verdict) -> dict:
    """The client-facing preflight turndown brief."""
    lines = []
    lines.append(
        f"This financing is not currently marketable, and it is also not "
        f"dead. {len(steps)} identified steps move it from where it stands to "
        f"a structure that can be sold."
    )
    lines.append(
        f"Estimated cost of the pathway: ${cost_low:,.0f} to ${cost_high:,.0f} "
        f"in third-party and process costs. Estimated elapsed time: "
        f"{crit_low/4.33:.0f} to {crit_high/4.33:.0f} months on the critical "
        f"path -- much of the work runs in parallel, so this is materially "
        f"shorter than the sum of the individual steps."
    )
    if uncontrollable:
        lines.append(
            f"{len(uncontrollable)} of those steps are not within your control "
            f"or ours: " + "; ".join(s["action"] for s in uncontrollable[:3])
            + ". These depend on public bodies or market conditions. They "
            "should be started first precisely because they cannot be "
            "accelerated later."
        )
    if deal_changing:
        lines.append(
            f"{len(deal_changing)} steps would change the transaction rather "
            "than merely prepare it -- resizing, bifurcating, or restructuring. "
            "A pathway exists, but what emerges at the end of it is not "
            "identical to what was brought in. That should be understood now "
            "rather than discovered later."
        )
    lines.append(
        f"Pathway feasibility: {feasibility:.0%}. This reflects how much of "
        f"the path is controllable, not how hard the work is."
    )
    return {
        "verdict": verdict,
        "narrative": lines,
        "next_three_actions": [
            {"sequence": s["sequence"], "action": s["action"],
             "owner": s["control"], "why": s["why"],
             "cost_usd_range": s["cost_usd_range"],
             "duration_weeks_range": s["duration_weeks_range"]}
            for s in steps[:3]
        ],
    }


# ---------------------------------------------------------------------------
# Alternative structures.
#
# Remediation asks "how do we make THIS deal financeable?" Sometimes the
# better answer is a different deal: a smaller first series that proves the
# credit, a re-phased program, or the same project financed with a different
# instrument. A client is owed those options explicitly rather than being
# walked down a 36-month remediation path when a 9-month restructure reaches
# the market sooner.
#
# Every alternative is quantified from the client's own numbers. Nothing here
# invents a comparable or asserts a market clearing level.
# ---------------------------------------------------------------------------

def propose_alternatives(deal: dict, preflight_result: dict | None = None) -> list[dict]:
    """Structurally different versions of the project that reach market sooner."""
    if preflight_result is None:
        from services.preflight import run_preflight
        preflight_result = run_preflight(deal)

    from services.preflight import DSCR_INVESTMENT_GRADE

    codes = {t["code"] for t in (preflight_result.get("no_go", [])
                                 + preflight_result.get("structural", [])
                                 + preflight_result.get("watch", []))}
    out: list[dict] = []

    debt = float(deal.get("total_debt") or deal.get("bond_par") or 0)
    cost = float(deal.get("total_project_cost") or 0)
    dscr = float(deal.get("stabilized_dscr") or deal.get("projected_dscr") or 0)
    te_par = float(deal.get("tax_exempt_par") or 0)
    phases = int(deal.get("phase_count") or 0)
    series_par = float(deal.get("series_par") or 0)

    # 1 -- Scale to what coverage actually supports today.
    if dscr and debt and dscr < DSCR_INVESTMENT_GRADE:
        supportable = debt * (dscr / DSCR_INVESTMENT_GRADE)
        out.append({
            "id": "ALT-SCALE",
            "name": "Scaled to supportable coverage",
            "structure": (
                f"Size the program to ${supportable:,.0f} of debt rather than "
                f"${debt:,.0f} -- a {1 - supportable/debt:.0%} reduction -- and "
                f"fund the balance with equity or defer scope."),
            "why": (
                "Coverage is the binding constraint and it is the one thing no "
                "structure fixes. Sizing to it is the version that can be sold "
                "now rather than after a remediation cycle."),
            "trade_off": "Less proceeds. Scope must shrink or equity must grow.",
            "reaches_market": "Immediately -- no external dependency.",
            "quantified": {"debt_today": debt, "debt_supportable": supportable,
                           "reduction": debt - supportable},
        })

    # 2 -- Prove the credit with a small first series.
    if phases >= 3 or "PRESTABILIZATION_RISK" in codes:
        pilot = min(series_par or 0, 25_000_000) or 25_000_000
        out.append({
            "id": "ALT-PILOT",
            "name": "Pilot series first, then scale",
            "structure": (
                f"Issue a single small series (order of ${pilot:,.0f}) against "
                f"the most contracted, most seasoned component only. Bring the "
                f"remaining phases once that series has an operating and "
                f"collection record."),
            "why": (
                "Pre-stabilization risk is the trap enhancement is expensive "
                "for and rating agencies punish hardest. One performing series "
                "converts the whole program from projection to record, and "
                "every later phase prices off that."),
            "trade_off": (
                "Slower total deployment. The sponsor funds more of the early "
                "phases from equity."),
            "reaches_market": "Fastest path to a first close.",
            "quantified": {"pilot_series_par": pilot,
                           "phases_deferred": max(0, phases - 1)},
        })

    # 3 -- Split public from private and finance them differently.
    if "TAX_EXEMPT_INELIGIBLE" in codes and te_par:
        out.append({
            "id": "ALT-BIFURCATE",
            "name": "Public infrastructure tax-exempt, private components taxable",
            "structure": (
                "Finance roads, utilities, public realm and any municipal "
                "campus through a governmental issuer as tax-exempt. Finance "
                "hotel, retail, entertainment and commercial space as taxable "
                "144A. Two credits, two buyer sets, one project."),
            "why": (
                "Tax-exempt eligibility follows the use of the financed "
                "property. Bifurcating stops a private-use problem from "
                "contaminating the portion that genuinely qualifies, and it is "
                "the structure bond counsel is most likely able to opine on."),
            "trade_off": (
                f"The private portion reprices to taxable. On ${te_par:,.0f} of "
                f"currently-assumed tax-exempt par the blended cost of funds "
                f"rises materially -- model it before presenting."),
            "reaches_market": "After bond counsel opinion, order of 3 months.",
            "quantified": {"tax_exempt_par_at_risk": te_par},
        })

    # 4 -- Take seasoning off the critical path.
    if "UNSEASONED_ASSESSMENT" in codes:
        out.append({
            "id": "ALT-BRIDGE",
            "name": "Taxable construction bridge, refund when seasoned",
            "structure": (
                "Fund construction with taxable debt now. Levy and season the "
                "assessment in parallel. Refund into the permanent assessment "
                "series once a collection record exists."),
            "why": (
                "Seasoning is a calendar constraint controlled by a public "
                "body -- it cannot be bought or accelerated. Bridging removes "
                "it from the critical path entirely, which is worth more than "
                "the interim carry on most timelines."),
            "trade_off": "Taxable carry during the bridge, plus refunding costs.",
            "reaches_market": "Near-term. Removes 12-26 months of public process.",
            "quantified": {},
        })

    # 5 -- Re-phase so no phase depends on the one before it.
    if "PHASING_CASCADE" in codes and cost and phases:
        out.append({
            "id": "ALT-REPHASE",
            "name": "Independently-financeable phases",
            "structure": (
                f"Restructure the {phases} phases so each is sized and secured "
                f"to stand alone, with no phase depending on released equity "
                f"from the phase before it. No cross-default between series."),
            "why": (
                "Serial dependency means an underperforming phase does not "
                "degrade the program, it stalls it -- and later bondholders "
                "carry risk from phases they hold no security interest in. "
                "Independent phases deploy more slowly and sell far more "
                "easily."),
            "trade_off": (
                "Loses the capital efficiency of recycling. Requires more "
                "sponsor equity committed up front across phases."),
            "reaches_market": "Restructuring only -- no external dependency.",
            "quantified": {"phases": phases, "program_cost": cost},
        })

    for i, a in enumerate(out, 1):
        a["rank"] = i
        a["basis"] = ("Derived from the client's own stated figures. No market "
                      "comparable or clearing level is asserted.")
    return out


def stairway_full(deal: dict) -> dict:
    """Preflight + remediation pathway + alternative structures, in one call."""
    from services.preflight import run_preflight
    pre = run_preflight(deal)
    pathway = build_pathway(deal, pre)
    alternatives = propose_alternatives(deal, pre)
    return {
        "preflight": {
            "verdict": pre["verdict"],
            "walk_away_signal": pre["walk_away_signal"],
            "headline": pre["headline"],
            "counts": pre["counts"],
        },
        "pathway": pathway,
        "alternative_structures": alternatives,
        "recommendation": (
            "Compare the remediation pathway against the alternative "
            "structures on time-to-market, not just cost. A 36-month "
            "remediation and a 9-month restructure that reach the same capital "
            "are not equivalent, and the client should choose knowingly."
        ),
    }
