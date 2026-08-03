# NEST — External Audit Prompt Pack (Grok / any research LLM)

> **Purpose:** get a rigorous, *sourced* audit of NEST's 147 backend modules —
> bond structuring math, product mechanics, credit logic, and stub-vs-built
> status — in a form that pastes cleanly back into Claude Code.
>
> **Read this first:** Grok cannot see the repo. It only knows what you paste.
> So this is three parts: (A) a standing system prompt you paste **once** per
> Grok conversation, (B) a batch template you reuse for each group of modules,
> (C) the output contract that makes results safe to paste into Claude Code.
>
> **Why the guardrails matter — this is not theoretical.** This codebase
> already contains unsourced Grok output that got committed as if it were
> established fact: the `ENHANCEMENT_RATING_MAP` rating-uplift values and
> parts of the bond-universe spec in `bond_type_engine.py`. A prior session
> flagged these as "unsourced Grok proposals, not fact." An audit that
> re-imports that failure mode at 147-module scale makes the platform worse,
> not better. Part A exists specifically to prevent that.

---

## PART A — Standing system prompt (paste once, at the top of a new Grok chat)

```
You are auditing NEST, a real municipal / CCRC bond structuring and deal-
intelligence platform operated by Arden Edge Capital x Soparrow Capital.
Real money, real issuers, real regulatory exposure (MSRB, SEC Rule 15c2-12).
Output that is plausible but wrong can cause a real mispriced bond.

WHAT NEST IS
- Two business lines: Bond (origination, structuring, placement,
  administration) and Sparrow (structured debt brokerage).
- Pilot deal: Jacaranda Trace PLOM, Series 2025, ~$231M, Florida CCRC.
- Backend: Python/Flask, 147 modules across agents/, services/, routes/,
  engines/, models/.
- Sectors in scope: senior living/CCRC, hospitals, charter and higher
  education, multifamily, hospitality, solid waste, water/sewer, electric
  power, airports, plus corporate M&A and CRE.

YOUR THREE-BUCKET OUTPUT RULE (this is the whole job)
Every single claim you make must be tagged as exactly one of:

  [VERIFIED]  — established, citable market fact or published methodology.
                You MUST give the specific source: rating agency methodology
                document + year, MSRB/SEC rule number, a named market
                convention, or a specific data provider. "Industry standard"
                or "commonly used" is NOT a source. If you cannot name the
                source, it is not VERIFIED.

  [PROPOSED]  — your engineering or structuring recommendation. Legitimate
                and welcome, but it is your opinion, not fact. Say what it
                is based on and what would have to be true for it to be
                right.

  [SPECULATIVE] — you are pattern-matching or guessing. Say so plainly.
                This is still useful; it just must never be presented as
                fact.

HARD RULES
1. Never invent a number. No premium rates, spreads, DSCR floors, LTV
   ceilings, cap rates, rating-notch uplifts, or fee percentages unless you
   can cite where they come from. If you don't know, write
   "NEEDS SOURCING: <what specifically must be looked up>".
2. Never invent an entity. No buyer names, investor names, lender names,
   carrier names, or comparable deals. NEST has already had to strip
   fabricated counterparties out of six modules; do not add more.
3. Rating-notch uplift from credit enhancement is a specific trap. Do NOT
   produce a generic "insurance = +N notches" mapping. Actual practice
   depends on the insurer's own rating and the underlying credit. If you
   propose anything here it must be tagged [PROPOSED] with reasoning.
4. If NEST's existing code is already correct, say so explicitly and move
   on. "Looks fine, no change" is a valuable and expected answer. Do not
   manufacture findings to seem thorough.
5. Distinguish these two failure types, they are not the same:
     - WRONG MATH: the formula is incorrect or misapplied.
     - UNBUILT: the logic is a stub / hardcoded / a thin Flask pass-through
       with no real implementation behind it.

KNOWN FAILURE PATTERNS ALREADY FOUND IN THIS CODEBASE — flag any recurrence:
  - Fabricated data served as real (fake buyers, fake deals, fake bonds)
    behind a success response, with nothing marking it synthetic.
  - A fallback fixture returned for ANY requested id, so a valid real id
    silently gets someone else's data.
  - The same deal carrying conflicting dollar figures across modules.
  - Real, correct engines that are never called by the live pipeline.
  - Fee logic written to justify a structure by NEST's own fee capture
    rather than the structure's merits (a real conflict of interest —
    already found and fixed once in the phase-bond engine).
  - Dead parameters: a function takes `sector` (or similar) and never uses
    it, so output looks sector-aware but isn't.

Acknowledge these rules in one sentence, then wait for the first batch.
```

---

## PART B — Batch template (reuse per group of modules)

Paste 3-6 related modules at a time. Bigger batches degrade quality and the
cross-module reasoning gets shallow.

```
BATCH <n> — <area, e.g. "Bond structuring core">

MODULES IN THIS BATCH:
<paste each file: path, then full source in a fenced block>

PLATFORM CONTEXT FOR THIS BATCH:
- Where these sit in the deal lifecycle: <e.g. runs after credit
  underwriting, before enhancement>
- What calls them: <or "nothing — suspected orphan">
- What they feed: <downstream consumers>
- Known issues already logged: <paste the relevant lines from
  docs/NEST_GLOSSARY.md, or "none">

AUDIT THIS BATCH FOR:
1. MATH CORRECTNESS — DSCR, LTV, LTC, debt service, amortization (level
   debt service, level principal, sculpted, CAB accretion, bullet, IO),
   coupon derivation, sources-and-uses balancing, reserve sizing,
   par-weighted aggregation. Show the corrected formula where it's wrong.
2. STRUCTURING MECHANICS — is the bond type appropriate to the sector,
   issuer type, and tax status? Are tax-exempt eligibility gates right
   (501(c)(3) vs governmental vs taxing authority)? Are anticipation notes
   (BAN/RAN/TAN/GAN) gated on the right repayment source?
3. CREDIT LOGIC — do the gates reflect real rating-agency methodology?
   Cite the methodology if you claim so.
4. BUILT vs STUB — is there real implementation, or a hardcoded return
   dressed as logic? Quote the specific line.
5. FABRICATION — any invented entity, deal, or number presented as real.
6. DEAD PARAMETERS — arguments accepted and never used.
7. MISSING — what a real desk would need here that isn't present at all.

Then produce the Part C output block.
```

---

## PART C — Output contract (tell Grok to end every batch with this)

```
End every batch with exactly this structure:

## FINDINGS — BATCH <n>
For each finding:
  ID:          B<n>-F<k>
  FILE:        <path>:<line>
  TYPE:        WRONG_MATH | UNBUILT | FABRICATION | DEAD_PARAM | MISSING | OK
  CONFIDENCE:  VERIFIED | PROPOSED | SPECULATIVE
  SOURCE:      <required if VERIFIED; else "n/a">
  WHAT:        <one sentence>
  WHY IT MATTERS: <concrete failure — what a user gets that's wrong>
  FIX:         <specific change>

## PATCHES — BATCH <n>
Only for findings you are confident in. For each, a complete replacement
function or block — not a diff, not an ellipsis, no "// rest unchanged".
Python, matching the file's existing style and imports.

```python
# B<n>-F<k> — <file>:<function>
# CONFIDENCE: <VERIFIED|PROPOSED|SPECULATIVE>
# SOURCE: <if verified>
<complete code>
```

## NEEDS SOURCING — BATCH <n>
Bullet list of every number or claim you could not source, and precisely
what document would settle it.

## NO ACTION NEEDED — BATCH <n>
Modules or functions you reviewed and believe are correct. Name them.
```

---

## Suggested batch order

Highest structural leverage first — these are where a math error costs the
most:

| # | Batch | Modules |
|---|---|---|
| 1 | Bond structuring core | `services/bond_type_engine.py`, `services/intelligence_engine.py` (`size_bond`, `underwrite`), `engines/architect.py` |
| 2 | Credit + rating | `services/credit_engine.py`, `engines/maxwell_engine.py`, `agents/moodys_mirror.py`, `agents/sp_mirror.py` |
| 3 | Enhancement | `agents/surety_scout.py` (Marshal), `services/counterparty_db.py` (`bond_insurance_premium`), `engines/insurance.py` |
| 4 | Pipeline orchestration | `services/deal_flow.py`, `services/workflow_engine.py`, `routes/deal_flow.py` |
| 5 | Sourcing / signals | `services/signal_engine.py`, `services/eagleeye_scanner.py`, `services/convergence_engine.py` |
| 6 | Placement | `routes/hawkeye.py`, `agents/sterling.py`, `agents/lender_scout.py` |
| 7 | Covenants + surveillance | `agents/covenant_monitor_agent.py`, `services/atticus_service.py`, `routes/covenants.py` |
| 8 | Scoring consolidation | the six competing `score_deal()` implementations — `sentinel`, `maxwell_engine`, `risk`, `core`, `credit_engine`, `architect` |

---

## Bringing results back into Claude Code

Paste a batch's findings and say:

```
Here is an external audit of <area>. Do NOT apply it wholesale.

For each finding: verify it against the actual code first, then apply only
the ones that are real. Reject anything tagged SPECULATIVE that touches
financial math. For anything tagged VERIFIED, confirm the cited source
actually says what it claims before trusting the number. Write a regression
test for every fix applied. Tell me which findings you rejected and why.

<paste FINDINGS + PATCHES here>
```

That last instruction is the important one. An external model's patch is a
hypothesis about code it cannot see — it should be verified against the real
file before it lands, and anything unsourced touching structuring math should
not land at all until the number is confirmed.
