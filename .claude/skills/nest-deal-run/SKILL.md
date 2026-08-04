---
name: nest-deal-run
description: Run a deal end-to-end through every NEST engine — readiness, preflight, success prediction, stairway pathway, POM sizing, document package, and fee ledger — and print one consolidated report. Use whenever asked to "run a deal through NEST", size a fee, assess financeability, or produce the numbers behind a brief.
---

# Run a deal through NEST

One command, the whole chain, real output. This exists because the chain was
being hand-rolled as a throwaway script every time, which meant every brief
risked quoting slightly different numbers.

**Never quote NEST figures from memory. Run this and quote the output.**

---

## Run it

```bash
"C:\Users\Sean Gilmore\AppData\Local\Programs\Python\Python312\python.exe" \
  .claude/skills/nest-deal-run/run_deal.py --deal <path-to-deal.json>
```

With no `--deal` it runs the Horn Lake 2028A reference deal, which is useful
for checking the engines still behave after a change.

Add `--json` to emit machine-readable output for a frontend or an artifact.

Python is not on PATH on this machine. Use the full interpreter path above.

---

## The deal file

JSON. Every field optional — missing inputs produce "cannot assess" rather than
a guess, which is the point. Supply what is true and nothing else.

```json
{
  "name": "73 Holdings — Series 2028A",
  "par_amount": 92000000,
  "sector": "mixed_use",
  "borrower_type": "developer",

  "total_project_cost": 1405000000,
  "total_debt": 1053750000,
  "stabilized_dscr": 1.50,

  "revenue_mechanism": "special_tax",
  "revenue_mechanism_seasoned": false,
  "revenue_contracted_pct": 0,
  "operating_history_years": 0,
  "capitalized_interest_months": 24,
  "revenue_ramp_months": 36,

  "tax_exempt": true,
  "conduit_issuer": null,
  "seeking_rating": true,
  "credit_enhancement": true,

  "capital_stack": true,
  "project_budget": true,
  "site_control": true,
  "org_structure": true,
  "bond_counsel_engaged": false,
  "feasibility_study": false,
  "audited_financials": false
}
```

**Do not pad the file to make the output look better.** A field asserted as
true that is not true produces a brief that is wrong in a way nobody can see.

---

## What comes back, and how to read it

**1 · Readiness** — does the sponsor have the paperwork? Score, RAG per
category, gap count. Move Forward Memorandum issues at ≥80%.

**2 · Preflight** — does the credit work? This assumes the checklist is
complete and asks what remains. Severities:

- `NO_GO` — cannot be done as contemplated. Walking away in week one is the
  correct and cheapest outcome.
- `STRUCTURAL` — financeable, but not as currently structured.
- `WATCH` — disclose and monitor.

**Preflight runs regardless of readiness, and a NO_GO overrides a clean
checklist.** These are orthogonal questions and conflating them is the
expensive mistake.

**3 · Prediction** — probability of close as-is, after procurable items are
procured, and the ceiling. Plus the stall point and the critical path.

**4 · Stairway** — if it fails, the pathway. Ranked steps, who controls each,
feasibility score, and the alternatives (scale down, pilot, bifurcate, bridge,
rephase). **Never deliver a NO_GO to a client without this section.**

**5 · POM** — offering-document hours under all three drafting models, and how
much of the document is writable today. Usually the largest single block of
NEST hours in the engagement.

**6 · Document package** — 60 documents across 10 silos, each BLOCKED or READY,
with what each is waiting on. Inapplicable documents are excluded rather than
counted incomplete.

**7 · Fee ledger** — gates, weights, hours, and whether the series clears cost
recovery. If `development_below_cost` is true, the engine also reports the fee
floor that fixes it.

---

## Reading it honestly

- Every threshold is `HAND_SET` or `RULE_BASED`. **Zero are `MARKET_DERIVED`** —
  no closed deals, no verified EMMA filings. Do not present any output as
  market-calibrated.
- Hours are `HAND_SET_PLANNING_ESTIMATE`, not measured.
- A high readiness score with a preflight `NO_GO` means the checklist has done
  nothing but document, in detail, why the deal fails. Say that out loud.
- The blocking input that appears across the most sections and silos is the
  real critical path, whatever the client thinks it is.

---

## Then what

Feed the output into a document using the `nest-docs` skill, which locks the
format, the confidence tagging, and the anti-fabrication rules.

Do not transcribe numbers by hand between the two. Paste the run output.
