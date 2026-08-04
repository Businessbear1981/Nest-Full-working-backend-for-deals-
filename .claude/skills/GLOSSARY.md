# nest-skills glossary

Terms a skill may use without redefining them. Where a term has a precise
meaning inside NEST that differs from its loose industry usage, the NEST
meaning governs and is marked **[NEST]**.

Confidence convention throughout: `verified` (checked in session, date stated) ·
`asserted` (stated, not re-checked) · `assumed` (best guess).

---

## The two questions NEST keeps separate

**Readiness** **[NEST]** — Does the sponsor have the documents? Measured by the
272-item Project Readiness Checklist across 8 categories.
`services/readiness_checklist.py`

**Preflight** **[NEST]** — Does the credit actually work? Assumes the checklist
is complete and asks what remains. `services/preflight.py`

**Orthogonality** **[NEST]** — The platform's core architectural claim: the two
questions above are independent. A sponsor can score 100% readiness and still
be running a financing unsellable at any price, in which case the checklist has
documented in exhaustive detail why the deal fails. Preflight runs regardless
of readiness score; a NO_GO overrides a clean checklist.

---

## Severities and states

**NO_GO** — The financing cannot be done as contemplated. Not harder — cannot.
Identifying it in week one instead of month nine is the single most valuable
thing the platform does.

**STRUCTURAL** — A real trap requiring the structure to change: different
instrument, different issuer, enhancement, different tax treatment, resizing.
Solvable, but not by working harder on the current plan.

**WATCH** — A genuine risk to disclose and monitor; not itself blocking.

**BLOCKED / READY** **[NEST]** — Document states. A document is READY when its
inputs exist, BLOCKED when they do not. Not a measure of effort.

**LOCKED / OPEN / COMPLETE / NOT_APPLICABLE** **[NEST]** — Silo gate states. A
silo with no applicable documents is NOT_APPLICABLE, never LOCKED — an
unenhanced deal has no enhancement work pending, it has none.

---

## Provenance

**HAND_SET** — Someone chose the number. Judgment, not measurement.

**RULE_BASED** — Derived from a stated rule, code section, or structural
constraint (e.g. cap-i months versus ramp months is arithmetic).

**MARKET_DERIVED** — Fitted to real market data, with the dataset and sample
size named. **NEST currently has zero of these.**

**HAND_SET_PLANNING_ESTIMATE** — Hours. NEST has not closed enough deals to
have measured them.

---

## Structure

**Silo** **[NEST]** — *Ambiguous term; always say which scheme.* The Bible
defines 16 **knowledge** silos (a reference taxonomy). `backend/engines/`
declares a 14-silo **workflow** architecture. **The numbers conflict** — Bible
9 is Credit Enhancement, engines 9 is Audit Package. Skills and documents use
the **ten named arrangement silos** carried on the fee gates: intake,
structuring, diligence, enhancement, documentation, rating, packaging,
certification, placement, closing.

**Gate** **[NEST]** — A point where a defined deliverable is produced,
accepted, and only then invoiced. Ten total: eight development, two placement.

**POM / POS** — Preliminary Offering Memorandum / Preliminary Official
Statement. **[NEST]** treats it as a *composite*: 23 sections across six
owners, not one document. The largest single block of NEST hours in an
engagement. `services/pom_engine.py`

**Drafting model** **[NEST]** — Who holds the pen on the POM:
`counsel_drafts` · `market_standard` · `nest_drafts_all`. Chosen on control of
how the credit is characterised, not on hours.

**Master Trust Indenture / Obligated Group** — Single master indenture with
supplemental indentures per series; the obligated group is the set of entities
jointly liable.

**Additional Bonds Test (ABT)** — The coverage test a credit must meet to issue
further parity debt.

---

## Credit and structure terms that recur

**DSCR** — Debt service coverage ratio. NEST bands: 1.10 absolute floor · 1.20
enhancement reach · 1.35 investment-grade proxy. All HAND_SET.

**LTC** — Loan to cost. NEST flags overleverage above 75% debt-to-cost.

**Cap-i** — Capitalized interest: bond proceeds set aside to pay interest
before revenue arrives. **Cap-i exhaustion** is when the cap-i period is
shorter than the revenue ramp — the specific mechanism by which development
bonds default.

**Seasoning** — Demonstrated collection history on a special assessment or
special tax before institutional buyers will price it.

**Conduit issuer** — The governmental entity that issues on behalf of a private
borrower, required for tax-exempt treatment.

**Private business use** — The IRC constraint limiting tax-exempt financing of
property used in a private trade or business.

**GMP** — Guaranteed Maximum Price construction contract.

**Procurable vs structural** **[NEST]** — A shortfall you can go buy (feasibility
study, audit, appraisal) versus one that is a property of the credit. Conflating
them drove an early version of the predictor to score a financeable deal at 0%.

---

## Compensation

**Pay-on-delivery** **[NEST]** — No fee is due at signing. Every gate starts
pending and becomes invoiceable only on acceptance of its deliverable. Deliberately
opposed to the retainer model.

**Program Architecture Fee** **[NEST]** — The single upfront, non-refundable
line. The deliverable is the financing strategy itself, which transfers on day
one and is portable — it cannot be pay-on-delivery without giving the work
product away.

**Transaction-based compensation** — Compensation contingent on a securities
transaction closing. The SEC's strongest indicator of broker activity. **NEST
cannot accept it until placement agent registration is effective**, regardless
of whether it is paid in cash or equity.

**Profits interest** — Rev. Proc. 93-27 partnership interest in future profits
only.

**Phantom income** — Cash tax owed on allocated but undistributed income. Under
Rev. Proc. 2001-43 with an §83(b) election, the holder reports distributive
share whether or not cash arrives — which can make a profits interest
cash-negative in a reinvesting SPV.

---

## Products

**EagleEye** — Pillar 1, origination: finding deals.

**Hawkeye** — Pillar 4, distribution: matching buyers.

*These are genuinely different functions at opposite ends of the deal. They
duplicate a data substrate, which argues for extracting a shared market-signal
layer — not for merging them. Merging origination with distribution rebuilds a
wall that matters once NEST is a registered placement agent.*

**Stairway to Heaven** **[NEST]** — The pathway engine. Every deal has a
pathway; what differs is cost, duration, and how much of it the client
controls. Never deliver a NO_GO without it. `services/stairway.py`

---

## External sources

**EMMA** — MSRB Electronic Municipal Market Access. Official statements,
continuing disclosures, material event notices. **The intended spine of NEST's
counterparty and calibration strategy** — every official statement names its
bond counsel, underwriter, trustee, and feasibility consultant on the cover.
**Currently inaccessible:** the connector returns HTTP 403 and MSRB blocks
server-side access. `verified 2026-08-04`

**FRED** — Federal Reserve Economic Data. Rates. Requires `FRED_API_KEY`,
**not set**. `verified 2026-08-04`

**EDGAR** — SEC filings. No key required; needs a real pull to confirm working.
`asserted`
