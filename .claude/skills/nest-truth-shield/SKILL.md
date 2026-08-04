---
name: nest-truth-shield
description: Verification pass before any NEST claim, number, entity, or status goes to a client, partner, or regulator. Use when asked "do you agree", before sending anything client-facing, when auditing a module's honesty, or whenever a status indicator claims something is working. Catches fabricated entities, unbacked thresholds, and green lights that measure nothing.
---

# Truth shield

A verification discipline, not a review. The question is never "does this read
well" — it is **"is each of these things true, and how do I know."**

This exists because the platform has already shipped untrue things. Six modules
had fabricated counterparties stripped. A seventh survived until August 2026:
`routes/hawkeye.py:26` still asserts NEST has `"relationship": "existing"` with
six institutional buyers that do not exist. The EMMA connector hardcodes
`status = CONNECTED` and returns HTTP 403 on every call.

Both would have been caught by the checks below in under five minutes.

---

## The four failure modes, in order of how much damage they do

### 1 · Fabricated entities

Any named firm, person, buyer, lender, issuer, trustee, counsel, or comparable
deal that was not verified in this session.

**Check:** for each named entity, can you point to where it came from — a
filing, a search result, a document the user supplied? If the answer is
"it's the kind of name that would be there," it is fabricated.

Worst variant: a fabricated entity carrying a **relationship claim**
(`existing`, `prior client`, `warm intro`). That is not a placeholder, it is a
misrepresentation, and it survives into pitch decks.

**Remedy:** delete. An empty list is honest and publishable. Replace with
`NEEDS SOURCING: <the query or filing that would produce a real list>`.

### 2 · Status that measures nothing

A green light that is hardcoded, defaulted, or catches its own failure.

**Check:** grep the status assignment. Does anything actually probe the
dependency? Then probe it yourself:

```bash
curl -s -o /dev/null -w "%{http_code}\n" -m 20 "<the endpoint the code calls>"
```

Patterns that are always suspect:

- `status = CONNECTED` set in `__init__` rather than by a health check
- `is_configured()` returning a literal `True`
- `except Exception: pass` around a connectivity test
- A feed listed as "real" in a status doc with no date on the verification

**Remedy:** make the status reflect a probe, or mark the feed unavailable. A
red light is information. A false green light destroys trust in every other
light on the board.

### 3 · Numbers without provenance

**Check:** every threshold and every dollar figure carries one of `HAND_SET`,
`RULE_BASED`, `MARKET_DERIVED`, and every claim carries `verified` /
`asserted` / `assumed`.

**NEST currently has zero `MARKET_DERIVED` thresholds** — zero closed deals,
zero verified EMMA filings. Any document, screen, or sentence implying market
calibration is false. This includes softer phrasings: "benchmarked",
"market-tested", "based on comparable transactions".

**Remedy:** say hand-set. It is a stronger position than false precision that
a sophisticated client will find.

### 4 · Stale claims restated as current

A fact verified months ago, repeated today as though re-checked.

**Check:** does the source carry a verification date, and is the underlying
thing still true? `docs/STATE.md:33` lists the "MSRB/EMMA corpus" under
**genuinely real** — which contradicts the current state of 0 verified filings
and a 403ing connector. That line was true when written and is not true now.

**Remedy:** re-verify or re-tag as `asserted` with the original date. Never
promote an `asserted` claim to `verified` without actually checking.

---

## Procedure

1. **List the claims.** Extract every factual assertion, entity, number, and
   status from the artifact under review.
2. **Classify each** against the four modes above.
3. **Verify what can be verified now** — run the engine, probe the endpoint,
   grep the code, read the filing. Prefer five minutes of checking to any
   amount of reasoning about whether it is probably fine.
4. **Report per claim:** the claim, the verdict, and the evidence. Not a
   summary judgment on the document.
5. **Say where it is already correct.** "This is fine, no change" is a real
   finding. Do not manufacture issues to look thorough — that is its own
   dishonesty and it trains people to ignore the output.

---

## When asked "do you agree?"

Answer the question honestly, which usually means partially.

- Verify before agreeing. Agreement that skipped the check is worthless to
  someone making a decision on it.
- Separate what you verified from what you are reasoning about, and label
  which is which.
- If a claim is half right, say which half and why the other half fails. "Half
  right, and the fix is not the one you named" is more useful than yes.
- Bring evidence the person did not have. The value is not the verdict, it is
  the thing they did not know.
- Never soften a real finding to preserve the mood of the conversation. The
  client conversation later is the one that matters.

---

## Standing red list

Known-untrue things in this codebase. Update as they are fixed; do not let this
list go stale.

| Location | Problem | Status |
|---|---|---|
| `routes/hawkeye.py:26` | Six fabricated buyers with `"relationship": "existing"` | **Open** |
| `services/data_connectors.py:321` | EMMA hardcoded CONNECTED; endpoint returns 403 | **Open** |
| `docs/STATE.md:33` | Lists EMMA corpus as "genuinely real"; contradicted | **Open** |
| `services/emma_engine.py` | 0 verified filings, 10 modeled | Labelled honestly |
| Auth on `/api/deals` | Responds without auth; 4 tests failing | **Open**, known |
