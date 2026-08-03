"""
NEST Gate Fee Engine — pay-on-delivery fee ledger for arrangement engagements.

Why this exists, stated plainly: the standard advisory model takes a large
retainer up front, and if the deal stalls the client has paid for a year and
holds nothing. NEST's position is the opposite -- no fee is due until the
deliverable behind that gate is actually delivered and accepted. A client can
open this ledger at any time and see exactly where the deal is, what has been
paid, what it bought, and what the next payment is for.

This is deliberately NOT services/billing_engine.py's model. That module bills
85% of the fee at closing, which (a) back-loads everything into a single
success event and (b) is transaction-based compensation, unavailable to an
unlicensed advisor. This engine bills work as it lands.

Two fee classes, kept separate on purpose:

  DEVELOPMENT gates  -- compensation for work product delivered before any
                        securities placement. Available pre-license.
  PLACEMENT gates    -- pricing and closing fees. Transaction-based; these
                        are gated behind `placement_licensed` and will not
                        accrue until it is set True.

Nothing here fabricates a payment status. A gate is `pending` until something
real marks it delivered.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

# ---------------------------------------------------------------------------
# Gate definitions
#
# `silo` maps each gate onto the NEST arrangement pipeline so the client-facing
# ledger and the internal workflow use the same vocabulary. `weight` is the
# share of the development fee pool earned at that gate; weights within each
# class sum to 1.0.
#
# Enhancement and Rating carry the heaviest weights because that is where the
# work actually moves the client's pricing outcome -- an enhancement term sheet
# or a rating uplift is worth materially more to the issuer than a data room.
# ---------------------------------------------------------------------------

DEVELOPMENT_GATES = [
    {
        "id": "g1_readiness", "seq": 1, "silo": "intake",
        "name": "Project Readiness Assessment",
        "buys": "Secure data room, item-by-item readiness checklist with gap "
                "analysis, sponsor diligence memorandum, and a written "
                "go/no-go recommendation.",
        "hours_estimate": 80,
        "weight": 0.10,
    },
    {
        "id": "g2_capital_stack", "seq": 2, "silo": "structuring",
        "name": "Capital Stack Architecture",
        "buys": "Tranche-by-tranche capital stack with tenor, indicative "
                "coupon, ranking and security package; counterparty long-list; "
                "funding strategy memorandum; financial model gap analysis.",
        "hours_estimate": 180,
        "weight": 0.22,
    },
    {
        "id": "g3_diligence", "seq": 3, "silo": "diligence",
        "name": "Independent Diligence Coordination",
        "buys": "Executed engagements with feasibility consultant, independent "
                "engineer and technical consultants; integrated critical-path "
                "diligence workplan; monthly status reporting.",
        "hours_estimate": 90,
        "weight": 0.11,
    },
    {
        "id": "g4_enhancement", "seq": 4, "silo": "enhancement",
        "name": "Credit Enhancement Term Sheet",
        "buys": "Information memorandum to credit enhancers, full insurance "
                "underwriting report, and an indicative term sheet from at "
                "least one named enhancer with pricing and attachment point.",
        "hours_estimate": 160,
        "weight": 0.20,
    },
    {
        "id": "g5_counsel", "seq": 5, "silo": "documentation",
        "name": "Bond Counsel Engagement",
        "buys": "Bond counsel engaged, tax status analysis, preliminary "
                "structure opinion, and documentation workplan.",
        "hours_estimate": 60,
        "weight": 0.08,
    },
    {
        "id": "g6_rating", "seq": 6, "silo": "rating",
        "name": "Rating Agency Pre-Marketing",
        "buys": "NRSRO engagement, rating agency information package and "
                "presentation, rating committee presentation conducted, and a "
                "written indicative rating letter.",
        "hours_estimate": 130,
        "weight": 0.16,
    },
    {
        "id": "g7_pom", "seq": 7, "silo": "packaging",
        "name": "Preliminary Offering Memorandum",
        "buys": "Full preliminary offering memorandum reviewed and approved by "
                "bond counsel, including risk factors, use of proceeds, "
                "capitalization, market analysis and tax considerations.",
        "hours_estimate": 200,
        "weight": 0.10,
    },
    {
        "id": "g8_bond_ready", "seq": 8, "silo": "certification",
        "name": "Bond-Ready Certification",
        "buys": "Written certification that all conditions precedent to launch "
                "are satisfied, with rating letter, enhancer commitment, "
                "trustee engagement, legal opinions and permits matrix.",
        "hours_estimate": 40,
        "weight": 0.03,
    },
]

PLACEMENT_GATES = [
    {
        "id": "g9_pricing", "seq": 9, "silo": "placement",
        "name": "Pricing",
        "buys": "Investor outreach and book-building through the placement "
                "agent, order book, allocation and final pricing.",
        "hours_estimate": 120,
        "weight": 0.25,
    },
    {
        "id": "g10_closing", "seq": 10, "silo": "closing",
        "name": "Closing",
        "buys": "Settlement, delivery of securities, funding of proceeds and "
                "reserve accounts, and closing document set.",
        "hours_estimate": 100,
        "weight": 0.75,
    },
]

VALID_STATUSES = ("pending", "in_progress", "delivered", "accepted",
                  "paid", "waived", "refunded")

# Senior-banker hours per gate. HAND_SET planning estimates -- NEST has not
# run enough engagements to have measured these, and they are labeled wherever
# they surface. They exist so a fee can be sanity-checked against the work
# behind it: a schedule that implies $4,000/hour is not a fee schedule, it is
# a success fee wearing a work-fee label, and that is exactly the
# characterization we cannot afford pre-license.
HOURS_PROVENANCE = "HAND_SET_PLANNING_ESTIMATE"

# A gate is only invoiceable once the client has accepted the deliverable.
INVOICEABLE_FROM = ("accepted", "paid")


class GateFeeError(ValueError):
    """Raised on an invalid gate id or status transition."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _effort_summary(gates: list[dict], dev_pool: float,
                    placement_pool: float) -> dict:
    """
    Hours behind the fee, and what that implies per hour.

    Reported so a fee can be defended as compensation for work rather than
    asserted. If the implied rate is absurd in either direction, the schedule
    is wrong and this makes that visible before a client does.
    """
    dev = [g for g in gates if g["fee_class"] == "development"]
    plc = [g for g in gates if g["fee_class"] == "placement"]
    dev_hours = sum(g.get("hours_estimate") or 0 for g in dev)
    plc_hours = sum(g.get("hours_estimate") or 0 for g in plc)
    return {
        "development_hours": dev_hours,
        "placement_hours": plc_hours,
        "total_hours": dev_hours + plc_hours,
        "development_effective_hourly": (round(dev_pool / dev_hours, 2)
                                         if dev_hours else None),
        "placement_effective_hourly": (round(placement_pool / plc_hours, 2)
                                       if plc_hours and placement_pool else None),
        "hours_provenance": HOURS_PROVENANCE,
        "note": (
            "Senior-banker hours, planning estimates. The effective hourly is "
            "the sanity check: a development fee implying an implausible rate "
            "is a success fee wearing a work-fee label, which is the "
            "characterization an unlicensed advisor cannot afford."
        ),
    }


class GateFeeEngine:
    """Builds and reads a pay-on-delivery fee ledger for one series."""

    def build_ledger(
        self,
        *,
        series_name: str,
        par: float,
        development_fee_bp: float,
        placement_fee_bp: float = 0.0,
        placement_licensed: bool = False,
        development_fee_floor: float = 0.0,
        development_fee_cap: float | None = None,
        program_architecture_fee: float = 0.0,
    ) -> dict:
        """
        Create the full gate ledger for a single bond series.

        `par` drives both pools. Fees scale with the par being arranged
        rather than being flat, so a $10M series and a $92M series are not
        billed the same for the same work.

        No fee is dated or due at signing -- every gate starts `pending` and
        becomes invoiceable only on acceptance of its deliverable.
        """
        if par <= 0:
            raise GateFeeError("par must be positive to size a fee ledger")

        dev_pool = par * development_fee_bp / 10_000
        if development_fee_floor:
            dev_pool = max(dev_pool, development_fee_floor)
        if development_fee_cap:
            dev_pool = min(dev_pool, development_fee_cap)

        placement_pool = par * placement_fee_bp / 10_000 if placement_licensed else 0.0

        gates: list[dict] = []
        for g in DEVELOPMENT_GATES:
            gates.append({
                **g,
                "fee_class": "development",
                "amount": round(dev_pool * g["weight"], 2),
                "effective_hourly": (round(dev_pool * g["weight"] / g["hours_estimate"], 2)
                                     if g.get("hours_estimate") else None),
                "status": "pending",
                "delivered_at": None,
                "accepted_at": None,
                "paid_at": None,
                "available_pre_license": True,
            })
        for g in PLACEMENT_GATES:
            gates.append({
                **g,
                "fee_class": "placement",
                "amount": round(placement_pool * g["weight"], 2),
                "effective_hourly": (round(placement_pool * g["weight"] / g["hours_estimate"], 2)
                                     if g.get("hours_estimate") and placement_pool else None),
                "status": "pending",
                "delivered_at": None,
                "accepted_at": None,
                "paid_at": None,
                "available_pre_license": False,
                # Surfaced so the client ledger explains a $0 line rather
                # than silently showing zero.
                "blocked_reason": None if placement_licensed else (
                    "Transaction-based fee. Not chargeable until NEST's "
                    "placement agent registration is effective."
                ),
            })

        return {
            "series_name": series_name,
            "par": par,
            "created_at": _now(),
            "placement_licensed": placement_licensed,
            "fee_pools": {
                "development": round(dev_pool, 2),
                "development_bp": development_fee_bp,
                "placement": round(placement_pool, 2),
                "placement_bp": placement_fee_bp if placement_licensed else 0.0,
            },
            # The one legitimately upfront item. Everything else is
            # pay-on-delivery; this is not, because the deliverable itself is
            # delivered on day one and is portable. See PROGRAM_ARCHITECTURE
            # note below.
            "effort": _effort_summary(gates, dev_pool, placement_pool),
            "upfront_due": round(program_architecture_fee, 2),
            "program_architecture_fee": {
                "amount": round(program_architecture_fee, 2),
                "earned_at": "engagement",
                "refundable": False,
                "buys": (
                    "The financing strategy itself: series ladder and "
                    "sequencing across the program, instrument selection per "
                    "revenue mechanism, master indenture architecture, "
                    "additional-bonds test and covenant package, and the "
                    "gating logic that determines when each series can price."
                ),
                "why_not_gated": (
                    "This deliverable transfers on day one and is portable -- "
                    "once delivered, the client holds a financing strategy "
                    "usable by any advisor. It cannot be structured as "
                    "pay-on-delivery without giving away the work product for "
                    "free. It is the only non-refundable, non-contingent "
                    "component; every other fee in this ledger is earned only "
                    "as its deliverable lands."
                ),
            } if program_architecture_fee else None,
            "gates": gates,
            "terms": (
                "No fee is payable in advance of delivery. Each gate becomes "
                "invoiceable only when its deliverable has been delivered and "
                "accepted by the client. Third-party direct costs (feasibility, "
                "audit, rating agency, legal, engineering) are contracted and "
                "paid by the client directly and are not marked up."
            ),
        }

    def advance_gate(self, ledger: dict, gate_id: str, status: str) -> dict:
        """
        Move one gate to a new status. Mutates and returns the ledger.

        Enforces the real ordering -- a gate cannot be marked paid before it
        was accepted, and a placement gate cannot advance at all while
        unlicensed. Both would otherwise let the ledger show revenue that
        isn't earned or isn't lawful to charge.
        """
        if status not in VALID_STATUSES:
            raise GateFeeError(f"unknown status '{status}'")

        gate = next((g for g in ledger["gates"] if g["id"] == gate_id), None)
        if gate is None:
            raise GateFeeError(f"unknown gate '{gate_id}'")

        if gate["fee_class"] == "placement" and not ledger.get("placement_licensed"):
            raise GateFeeError(
                "Placement gates cannot advance until placement_licensed is set. "
                "Pricing and closing fees are transaction-based compensation."
            )

        if status == "paid" and gate["status"] not in INVOICEABLE_FROM:
            raise GateFeeError(
                f"gate '{gate_id}' cannot be paid from status '{gate['status']}' "
                "-- the deliverable must be accepted first"
            )

        gate["status"] = status
        stamp = _now()
        if status == "delivered":
            gate["delivered_at"] = stamp
        elif status == "accepted":
            gate["accepted_at"] = stamp
            if not gate["delivered_at"]:
                gate["delivered_at"] = stamp
        elif status == "paid":
            gate["paid_at"] = stamp
        return ledger

    def terminate(self, ledger: dict, *, reason: str = "") -> dict:
        """
        Terminate the engagement and compute what must be refunded.

        This is what makes "no upfront" more than a slogan. A gate that was
        paid but whose deliverable was never accepted is refundable in full --
        NEST holds cash for work the client did not receive, and it goes back.
        A gate that was delivered and accepted is earned and stays earned;
        the client has the work product regardless of whether the deal
        proceeds.

        Gates never reached were never billed, so there is nothing to refund
        on them -- which is the whole point of the structure.
        """
        refundable, earned = [], []
        for g in ledger["gates"]:
            if g["status"] != "paid":
                continue
            # accepted_at is set on acceptance; its absence means the client
            # paid for something never accepted.
            if g.get("accepted_at"):
                earned.append(g)
            else:
                refundable.append(g)

        refund_total = sum(g["amount"] for g in refundable)
        for g in refundable:
            g["status"] = "refunded"
            g["refunded_at"] = _now()

        ledger["terminated_at"] = _now()
        ledger["termination_reason"] = reason
        ledger["refund_due"] = round(refund_total, 2)

        return {
            "series_name": ledger["series_name"],
            "terminated_at": ledger["terminated_at"],
            "reason": reason,
            "refund_due": round(refund_total, 2),
            "refundable_gates": [
                {"gate": g["name"], "amount": g["amount"],
                 "why": "Paid but deliverable never accepted."}
                for g in refundable
            ],
            "earned_and_retained": [
                {"gate": g["name"], "amount": g["amount"],
                 "why": "Deliverable was delivered and accepted; the client "
                        "holds the work product."}
                for g in earned
            ],
            "never_billed": [
                {"gate": g["name"], "amount": g["amount"]}
                for g in ledger["gates"]
                if g["status"] in ("pending", "in_progress", "delivered")
            ],
            "ledger": ledger,
        }

    def client_view(self, ledger: dict) -> dict:
        """
        The client-facing answer to 'where is my deal and what am I paying for?'

        Deliberately reports what is NOT yet earned as prominently as what is.
        """
        gates = ledger["gates"]
        paid = [g for g in gates if g["status"] == "paid"]
        invoiceable = [g for g in gates if g["status"] == "accepted"]
        in_flight = [g for g in gates if g["status"] in ("in_progress", "delivered")]
        remaining = [g for g in gates if g["status"] == "pending"]

        next_gate = min(
            (g for g in gates if g["status"] not in ("paid", "waived")),
            key=lambda g: g["seq"], default=None,
        )

        total_fees = sum(g["amount"] for g in gates)
        paid_total = sum(g["amount"] for g in paid)

        return {
            "series_name": ledger["series_name"],
            "par": ledger["par"],
            "position": {
                "gates_complete": len(paid),
                "gates_total": len(gates),
                "pct_complete": round(len(paid) / len(gates) * 100, 1) if gates else 0.0,
                "current_gate": next_gate["name"] if next_gate else "Complete",
                "current_silo": next_gate["silo"] if next_gate else None,
            },
            "money": {
                "paid_to_date": round(paid_total, 2),
                "invoiceable_now": round(sum(g["amount"] for g in invoiceable), 2),
                "work_in_flight_not_yet_billable": round(
                    sum(g["amount"] for g in in_flight), 2),
                "not_yet_earned": round(sum(g["amount"] for g in remaining), 2),
                "total_if_all_gates_clear": round(total_fees, 2),
                "upfront_paid": 0.0,
            },
            "next_payment": None if next_gate is None else {
                "gate": next_gate["name"],
                "amount": next_gate["amount"],
                "buys": next_gate["buys"],
                "status": next_gate["status"],
                "blocked_reason": next_gate.get("blocked_reason"),
            },
            "ledger": [
                {
                    "seq": g["seq"], "gate": g["name"], "silo": g["silo"],
                    "fee_class": g["fee_class"], "amount": g["amount"],
                    "status": g["status"], "buys": g["buys"],
                    "paid_at": g["paid_at"],
                    "blocked_reason": g.get("blocked_reason"),
                }
                for g in sorted(gates, key=lambda x: x["seq"])
            ],
            "terms": ledger["terms"],
        }

    def program_rollup(self, ledgers: list[dict]) -> dict:
        """
        Aggregate several series ledgers into one program view.

        Reports gate coverage honestly: a program total is only meaningful
        alongside how many of its series have actually started.
        """
        if not ledgers:
            return {"series_count": 0, "note": "No series ledgers supplied."}

        views = [self.client_view(l) for l in ledgers]
        started = [v for v in views if v["position"]["gates_complete"] > 0]

        return {
            "series_count": len(views),
            "series_started": len(started),
            "total_par": round(sum(v["par"] for v in views), 2),
            "paid_to_date": round(sum(v["money"]["paid_to_date"] for v in views), 2),
            "invoiceable_now": round(sum(v["money"]["invoiceable_now"] for v in views), 2),
            "not_yet_earned": round(sum(v["money"]["not_yet_earned"] for v in views), 2),
            "total_if_all_gates_clear": round(
                sum(v["money"]["total_if_all_gates_clear"] for v in views), 2),
            "upfront_paid": 0.0,
            "series": [
                {
                    "series_name": v["series_name"], "par": v["par"],
                    "pct_complete": v["position"]["pct_complete"],
                    "current_gate": v["position"]["current_gate"],
                    "paid_to_date": v["money"]["paid_to_date"],
                }
                for v in views
            ],
        }


gate_fee_engine = GateFeeEngine()
