---
name: nest-house-style
description: The locked writing format for any NEST document — client brief, internal brief, design brief, proposal, fee schedule, research handoff, or meeting agenda. Use whenever writing a document that will be read by a client, a partner, Josh, Kevin, or a regulator.
---

# NEST house style — locked

This is not a style guide. It is a control. NEST documents get read by clients,
counterparties, and eventually regulators.

**Applies to:** client briefs, internal briefs, design briefs, proposals, fee
schedules, research handoffs, meeting agendas, and anything else that leaves
this machine.

**Not this skill.** *Which* documents a deal produces — the 60-document
package, its silos and gates — is **`nest-docs`**. This skill governs how a
document is written, not which documents exist.

---

## 1 · Verify before you write

Apply **`nest-truth-shield`** first. It is the single source of truth for the
anti-fabrication rules, the confidence tags (`verified` / `asserted` /
`assumed`), threshold provenance (`HAND_SET` / `RULE_BASED` /
`MARKET_DERIVED`), and the standing list of known-untrue things in this
codebase. Those rules live in one place so changing them is a one-place edit.

The two that bind hardest while drafting:

- **Never invent an entity, number, comparable, or relationship.** Write
  `NEEDS SOURCING: <the document or query that would settle this>` instead. An
  honest gap is publishable; an invented fact is not.
- **Tag every claim, and give every decision-gating number its provenance.**
  NEST has **zero `MARKET_DERIVED` thresholds** — no closed deals, no verified
  EMMA filings. Any document implying market calibration is wrong. Say
  hand-set; clients respect that far more than a false precision they later
  discover.

---

## 2 · Get numbers from the engines, never from memory

NEST documents are full of figures that exist in code. Do not restate them from
recollection — run the engine and quote the output.

```
backend/services/readiness_checklist.py   paperwork completeness, RAG per category
backend/services/preflight.py             structural traps, severity, provenance
backend/services/success_predictor.py     probability of close, stall point
backend/services/stairway.py              remediation pathway, cost, feasibility
backend/services/pom_engine.py            offering-document hours by drafting model
backend/services/document_package.py      60 documents across 10 silos, blocking
backend/services/gate_fee_engine.py       fee ledger, hours, cost recovery
backend/services/engagement_economics.py  risk-adjusted value of a fee mix
backend/services/deal_preflight_flow.py   the whole chain in one call
```

Write a script to the scratchpad, run it, paste real output. If a figure in a
document cannot be traced to an engine run or a cited source, it does not go in.

**Where the document and the code disagree, the code wins.** Fix the document
and say in your summary which claims were wrong.

---

## 3 · Required sections

Every NEST document carries these. Order can flex; presence cannot.

**Header** — what this is, who it is for, the date, and one line on how the
figures were produced.

**What is actually true right now** — the honest status. Working, scaffolding,
or absent. "Built" is not a status; a file existing is not a feature working.

**The body** — whatever the document is for.

**What is NOT built / NOT known** — mandatory, and never omitted because it is
unflattering. Persistence, auth, payment rails, calibration data, closed-deal
history. A document that lists only capabilities is marketing, and we do not
send clients marketing dressed as analysis.

**Decisions required** — if the document asks anyone to do anything, name the
decision, the owner, and why it cannot wait. Do not bury asks in prose.

---

## 4 · Naming

Three tiers, as used in `docs/NEST_GLOSSARY.md`. Do not invent a fourth, and do
not rename an existing engine to make a document read better.

- **Codenamed agents** — Bernard, Maxwell, Sentinel, Atticus, Rico, Steven
- **Platform engines** — the module names above, lowercase with `.py`
- **Product pillars** — EagleEye (origination), Hawkeye (distribution)

If an engine has no glossary entry, add one. Do not work around it.

**Known collision, do not silently resolve:** "silo" means two incompatible
things. The Bible defines 16 *knowledge* silos; `backend/engines/` declares a
14-silo *workflow* architecture, and the numbers conflict (Bible 9 is Credit
Enhancement, engines 9 is Audit Package). Documents should use the ten named
arrangement silos carried on the fee gates — intake, structuring, diligence,
enhancement, documentation, rating, packaging, certification, placement,
closing — and say which scheme they mean.

---

## 5 · Voice

Plain declarative sentences. Short paragraphs. Tables for anything with more
than three parallel facts.

- No hedging on things we know. No false confidence on things we do not.
- Name the uncomfortable thing directly. If a deal is unfinanceable, the
  document says unfinanceable.
- Explain the mechanism, not just the conclusion. "Cap-i runs 24 months against
  a 36-month revenue ramp, and that 12-month hole is the specific mechanism by
  which development bonds default" beats "timing risk."
- No adjectives doing an argument's work. Not "robust," "comprehensive,"
  "cutting-edge."
- Never characterise the client's competence in a client-facing document.

---

## 6 · Client-facing vs internal

**Client-facing** — no internal disagreement, no module names, no test counts,
no fee arithmetic that reveals our own margin. Structural findings stated
plainly, always with the pathway attached. Never deliver a NO_GO without the
alternatives from `stairway.propose_alternatives()`.

**Internal** — everything. Including what is broken, what is fabricated, what
we do not know, and where a previous document was wrong.

**Regulatory-adjacent** (anything touching the licence, fee characterisation,
or equity): add the caveat verbatim —

> This is not legal advice. <specific question> requires securities counsel.

---

## 7 · Before you ship

- [ ] Every number traced to an engine run or a cited source
- [ ] Every claim tagged `verified` / `asserted` / `assumed`
- [ ] Every threshold carries provenance
- [ ] No invented entity, firm, person, buyer, or comparable
- [ ] "What is NOT built" section present and honest
- [ ] Decisions named with owners
- [ ] Client-facing: no NO_GO without a pathway
- [ ] Regulatory: caveat present

**Then write it to `C:\Users\Sean Gilmore\OneDrive\Desktop\` and pin it:**

```bash
attrib +P -U "<filename>"
```

Without the pin, OneDrive makes it a cloud placeholder that cannot be uploaded.
Verify with `attrib "<filename>"` — you want `P`, not `U`.
