# GROK HANDOFF — NEST Preflight, Fee Architecture, and the 73 Holdings Deal

**Date:** 2026-08-03
**From:** Sean Gilmore / NEST Advisors
**Purpose:** external research validation of a structural-viability engine, a
gated fee architecture, and the specific findings it produced on a live
$1.405B development program.

**Read this whole file before answering anything.** It contains real numbers
from a live transaction. Wrong-but-plausible output here can mispricing a real
bond or cause a real client to be advised badly.

---

## 0. What we need from you

Five research questions, in priority order. They are stated precisely in
Section 6. Everything before that is the context you need to answer them.

The output contract in Section 7 is mandatory. Tag every claim VERIFIED
(with a named source), PROPOSED (your recommendation), or SPECULATIVE (you are
pattern-matching). "Industry standard" is not a source. If you cannot source a
number, write `NEEDS SOURCING:` and say what document would settle it.

**Do not invent numbers, entities, comparable deals, buyer names, or premium
rates.** This codebase has already had to strip fabricated counterparties out
of six modules.

---

## 1. Who we are and the constraint that shapes everything

NEST Advisors — municipal and project finance arrangement platform. Two
business lines: Bond (origination, structuring, placement, administration) and
Sparrow (structured debt brokerage). Backend is 150+ Python modules.

**The binding constraint: we are not yet a registered placement agent.** Until
registration is effective we cannot accept transaction-based compensation —
no success fees, no placement fees. We expect to be licensed around the time
the first deal closes.

This is not a technicality. It shapes the entire fee architecture: everything
chargeable before licensure must be genuine compensation for **development
work product delivered**, not disguised placement compensation. Equity granted
in lieu of a success fee is precisely the structure that gets recharacterized.

Second constraint, from the client side: **we refuse large upfront retainers.**
The industry norm — take $250K, work for a year, deliver nothing, keep the
money — is the practice we are positioning against. Our fees are pay-on-
delivery against defined gates, with one deliberate exception explained in
Section 4.

---

## 2. The deal: 73 Holdings Institutional Development Series, Vol. I — Horn Lake

Real program, real sponsor, currently being structured.

| | |
|---|---|
| Total program cost | $1,405,000,000 |
| Duration | 25 years, 6 phases |
| Location | Lafayette County / Horn Lake, Mississippi (Oxford market) |
| Primary demand driver | Ole Miss University (~1.4M annual visitors) |
| Equity / debt rule | 35% sponsor equity funds each phase to bankability, 65% bonds |
| Districts | District 73 (Phases I, III, IV, V, VI — 87.2%), District 45 (Phase II — 12.8%) |

### Phase structure

| Phase | Name | Years | Cost | Instrument selected |
|---|---|---|---|---|
| I | Dancy Development | 1–3 | $100M | Special Assessment ($10M, 5.50%) + Taxable Construction ($55M, cap-i deferral) |
| II | Entertainment & Civic District (District 45) | 2–8 | $180M | Special Tax Bond, 7.00% |
| III | UPrepPro Sports & Wellness | 5–10 | $350M | Special Tax Bond, 7.00% — requires enhancement |
| IV | Resort & Hospitality Village | 8–15 | $325M | Special Tax Bond, 7.00% — requires enhancement |
| V | Innovation & Commercial | 12–20 | $250M | Special Tax Bond, 7.00% |
| VI | Legacy Residential | 15–25 | $200M | Special Tax Bond, 7.00% — requires enhancement |

### The series ladder — ten pricings over twelve years

| Series | Par | Type |
|---|---|---|
| 2027A | $10.0M | tax-exempt muni, unrated by design, assessment security |
| 2027B | $55.0M | taxable 144A, construction, capitalized-interest deferral |
| 2028A | $21.5M | muni — first rated series |
| 2029B | $34.0M | 144A |
| 2030A | $19.0M | muni |
| 2031B | $42.0M | 144A |
| 2033B/C | $64.0M | 144A |
| 2035R | refunding | seasoned; enhancement revisited here |
| 2036B | $92.0M | 144A |
| 2039A/B | $54.0M | muni + taxable |

**New-money par: $391.5M across 9 series, plus one refunding.**

### Known internal inconsistencies in the sponsor's own documents

Flag these in your analysis; do not resolve them by picking one.

1. **Bond sizing disagrees by 3.4x.** One version's sources & uses shows bonds
   at $413.25M (29% of cost: $275M tax-exempt + $138.25M taxable). Another
   states 65% bonds ($913.25M). A debt service schedule describes Phase 1 as a
   "$100M Bond Issue" against a $100M phase cost.
2. **Our fee is stated two ways.** The prospectus says "Nest structuring &
   success fees (3.625% blended) — $12.20M". $12.20M at 3.625% implies a base
   of $336.6M, but new-money par is $391.5M. At 3.625% on actual par the fee
   is $14.19M. Separately, our own `bond_type_engine.py` uses a **2.25%**
   arrangement convention. Three numbers, one engagement.

---

## 3. What we built (and need validated)

Six new Python services. All logic is plain Python; the HTTP layer is a thin
wrapper. Full source is in the repo archive accompanying this handoff.

### 3.1 `readiness_checklist.py` — the paperwork question

Parses the client's 272-item, 8-category due diligence checklist
(Organizational, Financial, Commercial, Technical, Legal, Regulatory, Risk
Management, ESG) and scores it exactly as the Development Services Agreement
defines: `complete / applicable`, with justified "Not Applicable" excluded
from **both** numerator and denominator. **N/A without written justification
counts as incomplete** — otherwise "not applicable" becomes a way to inflate
the score by declaring inconvenient items irrelevant.

Move Forward Memorandum issues at ≥80%. Below that, the Gate 1 fee is
refundable in full. RAG banding per process, with green pinned to the 80%
threshold so "green" means "this clears," not "this looks fine."

### 3.2 `preflight.py` — the financeability question **(primary review target)**

The distinction this enforces:

> `readiness_checklist.py` asks **"does the sponsor have the documents?"**
> `preflight.py` asks **"does the credit actually work?"**

These are orthogonal. A sponsor can deliver all 272 items, score 100%, clear
the Move Forward Memorandum — and still be running a financing that cannot be
sold at any price. In that case the checklist has done nothing but document,
in exhaustive detail, why the deal fails.

So preflight **assumes the checklist is complete** and asks what remains.
What remains are structural traps: things no amount of diligence, packaging,
or sponsor effort fixes, because they are properties of the credit rather
than properties of the file.

Three severities:

- **NO_GO** — cannot be done as contemplated. Walking away in week one instead
  of month nine is the single most valuable output of the engine.
- **STRUCTURAL** — requires the structure to change (different instrument,
  different issuer, enhancement, different tax treatment, resizing).
- **WATCH** — real risk, disclose and monitor, not blocking.

**The nine detectors, with the thresholds we chose. These are what we most
need challenged:**

| Code | Fires when | Threshold | Severity |
|---|---|---|---|
| `COVERAGE_FATAL` | Stabilized DSCR below floor | **1.10x** | NO_GO |
| `COVERAGE_THIN` | Below the level where a wrap can reach | **1.20x** | STRUCTURAL |
| `COVERAGE_SUB_IG` | Below investment-grade band | **1.35x** | WATCH |
| `TAX_EXEMPT_INELIGIBLE` | TE assumed on private-use property, private developer, no public purpose | — | STRUCTURAL |
| `NO_CONDUIT_ISSUER` | TE series assumed, no issuer identified | — | NO_GO |
| `UNSEASONED_ASSESSMENT` | Special assessment / special tax not yet seasoned | — | STRUCTURAL |
| `PRESTABILIZATION_RISK` | <30% contracted revenue and <1yr operating history | **30%** | STRUCTURAL |
| `CAPI_EXHAUSTION` | Capitalized interest months < revenue ramp months | — | STRUCTURAL |
| `OVERLEVERED` | Debt / total project cost above ceiling | **75%** | STRUCTURAL |
| `DEMAND_CONCENTRATION` | One driver carries ≥60% of demand | **60%** | WATCH |
| `SERIES_TOO_SMALL` | Below institutional ticket (BQ exempt to $10M) | **$20M / $10M** | WATCH |
| `PHASING_CASCADE` | Later phases funded by earlier phases' released equity | — | WATCH |

Missing inputs produce an explicit "cannot assess" entry rather than a guess,
and the result reports `assessment_completeness`.

### 3.3 `success_predictor.py` — where it stalls

Per-gate clearing probability across ten arrangement gates, with the specific
unmet prerequisite driving each. Identifies the stall point and the
critical-path items that block the most gates.

**Explicitly labeled in code as a transparent structured scorecard, NOT a
statistically calibrated model** — we have no closed-deal dataset to fit
against. Rankings and stall identification are the reliable output; absolute
probabilities are directional.

Three modeling errors we found and fixed by running the real deal, which we
want you to check we fixed correctly:

1. **Procurable vs structural.** Missing a feasibility study scored identically
   to missing a conduit issuer, driving a financeable project to 0%. One you
   go buy; the other can kill the deal. Procurable shortfalls now floor the
   gate at `0.55 × base_rate` scaled by structural share.
2. **Compounding.** Multiplying ten gate probabilities scored even a flawless
   project at 28%. Close probability now blends **weakest-link** with
   **average preparedness** (`0.85 × √weakest × √average`), on the reasoning
   that financings die from one binding constraint rather than ten
   independent coin flips.
3. **Frozen-parameter headline.** Now reports as-is **and** what the deal
   reaches once procurable items are procured — which is the number an
   engagement is actually selling.

### 3.4 `gate_fee_engine.py` — pay-on-delivery ledger

Ten gates mapped to our arrangement silos: intake → structuring → diligence →
enhancement → documentation → rating → packaging → certification → pricing →
closing. Weights within the development pool: 10 / 22 / 11 / 20 / 8 / 16 / 10
/ 3 (enhancement and rating weighted heaviest — that is where the work moves
the client's pricing outcome).

Two enforcement rules in code, not policy:
- A gate **cannot** be marked paid unless it was accepted first.
- Placement gates **refuse to advance** while `placement_licensed` is False,
  and price at zero with the reason surfaced.

`terminate()` computes refunds: a gate paid but never accepted refunds in
full; a gate delivered and accepted is earned, because the client holds the
work product either way.

### 3.5 `engagement_economics.py` — risk-adjusted optimization

Values four compensation channels on one basis so they can be compared:
gated fees (near-certain, early), success fee (large, late, contingent,
license-gated), profits-interest equity, administration.

**Phantom tax modeling.** A Rev. Proc. 93-27 profits interest with a Rev. Proc.
2001-43 election makes the holder report its distributive share of entity
income **whether or not cash is distributed**. In a development SPV that
recycles residual equity into the next phase — which is exactly what this
program does — allocated income and distributed cash diverge for years, and
the holder owes real cash tax on paper income. Modeled as a negative cash
flow.

### 3.6 `deal_preflight_flow.py` — one call, intake to ledger

Chains all of it. **Preflight runs regardless of readiness score** — a
structurally unfinanceable deal should be identified before the sponsor spends
months assembling documents. A NO_GO overrides a clean checklist.

---

## 4. The fee architecture

**Tier schedule** (par-scaled, applied at development level):

| Tier | Indicative par | Rate | Floor | Cap |
|---|---|---|---|---|
| A | < $50M | flat $180,000 | — | — |
| B | $50M–$150M | 45 bp | $180,000 | $675,000 |
| C | $150M–$400M | 30 bp | $675,000 | $1,200,000 |
| D | > $400M | 20 bp | $1,200,000 | $2,000,000 |

Note the rates run **up** as series get smaller — a $10M series is nearly as
much work as a $55M one (same eleven roles, same rating conversation, same
POM). Flat bp loses money on small series.

**The one upfront component — and the reason for it.** Everything else is
pay-on-delivery. The exception is a **Program Architecture Fee**, charged at
engagement, non-refundable. Rationale: the deliverable is the financing
strategy itself — series ladder and sequencing, instrument selection per
revenue mechanism, master indenture architecture, additional-bonds test,
covenant package, gating logic. **That transfers on day one and is portable.**
Once delivered, the client holds a strategy usable by any advisor. It cannot
be structured pay-on-delivery without giving the work product away.

**Master Trust Indenture.** We are proposing a master indenture with an
obligated group and supplemental indentures per series — the architecture
health systems and CCRC operators use. One credit story, one covenant
package, cross-collateralization, and an additional bonds test that lets
Phases II–VI come to market without re-underwriting from zero. Proposed at 25
bp on total program authorization.

---

## 5. What the engine actually returned on Horn Lake

Run with the full checklist assumed and the real program parameters:

```
ACTION: ENGAGE_TO_RESTRUCTURE

STAGE 1  READINESS   57.4%  [AMBER]   116 gaps
  GREEN Organizational  100.0%    GREEN Financial  100.0%    GREEN Legal 100.0%
  RED   Commercial        0.0%    RED   Technical   35.5%
  RED   Regulatory        0.0%    RED   Risk Mgmt    0.0%    RED   ESG    0.0%
  Move Forward Memorandum issues: False

STAGE 2  PREFLIGHT   RESTRUCTURE   walk_away=False
  [STRUCTURAL] $275,000,000 assumed tax-exempt on private-use property
  [STRUCTURAL] Special Tax security is not yet seasoned
  [STRUCTURAL] No operating history and minimal contracted revenue
  [STRUCTURAL] Capitalized interest (24 mo) runs out before revenue arrives (36 mo)
  [WATCH]      70% of demand from a single driver (Ole Miss University)
  [WATCH]      Later phases funded by earlier phases' released equity (6 phases)

STAGE 3  PREDICTION
  38% as-is -> 48% with procurable items in hand; ceiling ~85%
  Stall point: closing
  Critical path: permits (blocks 3), feasibility study (blocks 3),
                 contracted revenue (blocks 2)

STAGE 4  FEE OPTIMIZATION   dev 150bp / success 212.5bp
STAGE 5  LEDGER   $250,000 upfront architecture + $825,000 pay-on-delivery
                  placement gates $0 and locked until licensed
```

**The finding we most need checked is the first one.** The program assumes
$275M tax-exempt — 66% of the bond stack on one sizing. The financed property
is hotel, retail, entertainment, sports, resort and commercial space owned and
operated by a private developer. Our engine says that is private business use
and is taxable absent a governmental issuer financing a qualifying public
purpose. Tax-exempt coupons in the program are modeled at 4.75%–5.75%;
taxable 144A at 7.25%–11.5%. **If we are right, a large part of the capital
stack is mispriced by 250–575 bp.** If we are wrong, we are about to tell a
client to restructure something that did not need restructuring.

---

## 6. The five research questions

**Q1 — Tax-exempt eligibility.** For a mixed-use development in Mississippi
combining public infrastructure (roads, utilities, public realm), a municipal
campus, and private commercial components (hotel, retail, entertainment,
sports academy, resort) under a private developer: which components can
actually support tax-exempt financing, through what issuer structure, and
under what constraints? Address private business use limits, qualified private
activity bond categories, and whether a special assessment or special tax
district changes the analysis. **Cite the Code sections and any relevant IRS
guidance.** This is the highest-value question in this document.

**Q2 — Our preflight thresholds.** Challenge the table in Section 3.2. Are
1.10x / 1.20x / 1.35x the right DSCR breakpoints for *development-stage
project revenue debt* — not stabilized municipal utility debt? Is 75%
debt-to-cost the right ceiling? Is 60% demand concentration the right warning
level? Is $20M a real institutional minimum in the current market? For each,
give the number you would use and the source. **Where our number is defensible,
say so — "this is fine" is a valuable answer and we would rather hear it than
a manufactured correction.**

**Q3 — Missing traps.** What structural failure modes are absent from our nine
detectors that a real municipal desk would catch? We are specifically
uncertain about: arbitrage rebate and spend-down exposure on a 25-year phased
program; continuing disclosure obligations under SEC Rule 15c2-12 across ten
series; additional bonds test design in a master indenture where later phases
depend on earlier phases' equity; and whether special assessment districts in
Mississippi carry state-specific constraints we have not modeled.

**Q4 — Capitalized interest and seasoning.** Phase I pairs a $10M unrated
assessment series with a $55M taxable construction series carrying a 24-month
cap-i deferral against a 36-month revenue ramp. How is that gap normally
solved in practice? What is the market convention for seasoning an assessment
or special tax before it can price to institutional buyers, and what evidence
do buyers actually require?

**Q5 — Fee architecture and the license constraint.** Is a Program
Architecture Fee — charged upfront, non-refundable, for portable strategy IP —
defensible as non-transaction-based compensation for an unregistered advisor?
What is the recharacterization risk, and what contractual terms reduce it?
Separately: is a profits interest granted concurrently with a development
services agreement, vesting on development milestones rather than closings, a
structure that survives scrutiny — and what is the standard mandatory tax
distribution language for a reinvesting SPV?

---

## 7. Output contract

End with exactly this structure.

```
## FINDINGS
For each:
  ID:          F<n>
  QUESTION:    Q1-Q5, or NEW
  TOPIC:       <short>
  CONFIDENCE:  VERIFIED | PROPOSED | SPECULATIVE
  SOURCE:      <required if VERIFIED — Code section, rule number, methodology
                document + year, named market convention. Not "industry standard">
  FINDING:     <one paragraph>
  IMPACT ON NEST: <what specifically we should change>

## THRESHOLD TABLE
Our value | Your value | Confidence | Source | Change?
(one row per threshold in Section 3.2)

## MISSING TRAPS
New detectors we should add. For each: trigger condition, severity
(NO_GO/STRUCTURAL/WATCH), threshold with source, and the reasoning a client
would need to hear.

## WHERE NEST IS ALREADY CORRECT
Name them explicitly. Do not manufacture findings to seem thorough.

## NEEDS SOURCING
Every number or claim you could not source, and precisely what document
would settle it.
```

---

## 8. How results come back

Findings will be verified against the actual code before anything is applied.
Anything SPECULATIVE touching financial math will not land. Anything VERIFIED
will have its cited source checked against the claim. Every applied change
gets a regression test.

That is not a formality — this repo already contains unsourced external LLM
output that was committed as established fact (`ENHANCEMENT_RATING_MAP` rating
uplift values, parts of the bond universe spec). Re-importing that failure
mode at this scale would make the platform worse, not better. Sourcing
discipline is the entire value of this exercise.
