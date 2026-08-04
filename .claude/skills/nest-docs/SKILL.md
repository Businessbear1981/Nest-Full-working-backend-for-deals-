---
name: nest-docs
description: The locked design of what a NEST deal produces — 60 documents across ten silos, each with an owner, a gate, and prerequisites. Use when asked what documents a deal needs, what is blocked, what a silo owes, who is responsible for a document, when work can start, or how the POM is composed.
---

# The NEST document package — locked design

**60 documents. Ten silos. Every one with an owner, a gate, and a stated
reason it cannot start yet.**

This is the design of what NEST delivers. It is locked in code, not in a
document that drifts:

```
backend/services/document_package.py    the catalogue and the gate logic
backend/services/pom_engine.py          the POM, which is 23 sections not 1
docs/NEST_DICTIONARY.md                 Volume 3 — what each document is and why
```

**Never answer "what documents does this deal need" from memory.** Run it.

---

## Run it

```bash
"C:\Users\Sean Gilmore\AppData\Local\Programs\Python\Python312\python.exe" -c "..."
```

or over HTTP:

```
POST /api/gate-fees/documents/package     {"deal": {...}, "statuses": {...}}
POST /api/gate-fees/documents/silo/<id>   one silo, drilled down
GET  /api/gate-fees/documents/catalogue   the design itself, deal-independent
POST /api/gate-fees/pom/compare           the POM under all three drafting models
```

`nest-deal-run` calls all of this and prints it. Prefer that for a whole deal.

---

## The ten silos

Sequence matters. Each is a checklist gate.

| # | Silo | Docs | Gate opens when |
|---|---|---|---|
| 1 | Intake and Readiness | 4 | — front door |
| 2 | Capital Stack Architecture | 5 | project budget |
| 3 | Independent Diligence | 6 | capital stack |
| 4 | Credit Enhancement | 3 | capital stack + feasibility |
| 5 | Documentation and Counsel | 10 | **bond counsel engaged** |
| 6 | Rating Agency | 3 | feasibility + projections |
| 7 | Offering Document | 3 | **bond counsel engaged** |
| 8 | Bond-Ready Certification | 3 | trust indenture |
| 9 | Placement and Pricing | 5 | POM |
| 10 | Closing and Settlement | 17 | priced |

---

## The rules that make the package mean something

**A document is READY when its inputs exist, BLOCKED when they do not.** Not a
measure of effort — a measure of whether work can begin. An input is satisfied
by a deal fact *or* by an upstream document reaching a terminal status. The
closing binder genuinely cannot precede the opinions inside it.

**Gate states:** `LOCKED` (prerequisites unmet) · `OPEN` (work can start) ·
`COMPLETE` (every required document accepted) · `NOT_APPLICABLE` (no applicable
documents — an unenhanced deal has no enhancement work *pending*, it has none).

**Delivered is not accepted.** A document only counts complete at `accepted` or
`waived`. This is the same discipline as the fee ledger: NEST does not mark its
own homework.

**Inapplicable documents are excluded, never counted incomplete.** A taxable
private placement has no Form 8038 and no blue sky filing. Counting them as
outstanding would make every deal look permanently behind and quietly
understate every percentage on a client screen. The engine reports how many it
excluded so a low total is explainable.

**Bond counsel is the critical path.** On a typical deal `bond_counsel_engaged`
blocks 6 of 23 POM sections, locks 3 silos, and gates 10 documents. Nothing
else comes close. Whether counsel is retained by NEST with the client's money
or by the client directly is commercial; identifying the universe and driving
the engagement is NEST's job either way.

---

## The POM is the one composite

Not a document — **23 sections across six owners**, and the largest single
block of NEST hours in an engagement. It delegates to `pom_engine.py`.

Who holds the pen is an **input, not an assumption**:

| Model | NEST hours | Sections NEST drafts |
|---|---|---|
| `counsel_drafts` | ~153 | 0 |
| `market_standard` | ~246 | 8–9 |
| `nest_drafts_all` | ~284 | 15–16 |

**Choose on control, not hours.** The sections NEST drafts are the ones that
characterise the credit — plan of finance, security and sources of payment,
coverage, bondholders' risks. Handing those to counsel is cheaper and cedes the
narrative.

**Volume 1 already states NEST's doctrine:** *"Nest platform first draft,
finalized by disclosure counsel."* Cite that before treating the model as an
open question.

Sections counsel must originate — tax matters, form of opinion, summary of
principal documents — are never assigned to NEST under any model.

---

## Known gaps in the design

State these when the package is presented as complete; it is not.

- **Volume 1 defines three documents the platform does not track:**
  Subordination Agreements, the Disclosure Counsel Opinion, and the
  sector-specific Regulatory Agreement. No silo produces them, so no deal will
  ever flag them missing. This is the more dangerous direction of the gap.
- **39 of 60 documents have no authored rationale** in Volume 3. Their
  category, owner, silo and prerequisites are verified from code; what they are
  and why they exist is not yet written.
- **No frontend.** Zero components call these endpoints. The package is
  API-only today.

---

## Changing the design

The catalogue is the design. Editing it changes what NEST delivers, so:

1. Add or amend the entry in `DOCUMENT_CATALOGUE`, with `silo`, `owner`,
   `category` (a Bible Silo 4 category), `requires`, and `only_if` where the
   document is contingent.
2. Add a test in `backend/tests/test_document_package.py`. Conditional
   documents need a test proving they are *excluded* when inapplicable.
3. Write the Volume 3 entry into `docs/Bible_Pass1_v2.md` in the Silo 4 format,
   map the heading in `scripts/build_dictionary.py`, and regenerate.

Never add a document to a brief that is not in the catalogue. If it belongs in
the deal, it belongs in the design.
