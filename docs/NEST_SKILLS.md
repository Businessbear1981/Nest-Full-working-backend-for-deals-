# NEST Skills
## The repeatable procedures, in one volume

> **Generated 05 August 2026** by `scripts/build_skills_book.py` from `.claude/skills/`. Do not hand-edit — the skill files are the source of truth.

**What a skill is.** A procedure NEST runs the same way every time, written down once. Before these existed the same work was rebuilt each session — the deal chain hand-rolled as a throwaway script, the document format reconstructed from memory, the verification pass done or skipped depending on how much time was left. Two briefs written a day apart could quote different numbers for the same deal and neither author would know.

A skill is loaded on demand when the work matches its description. It costs nothing until it is needed.

## The set

| Skill | Use it when |
|---|---|
| **`/kevin`** | Run a cross-working session with Kevin — open with the generated synopsis (code pushed, new modules and terms, backend/frontend integration, what… |
| **`/nest-docs`** | The locked design of what a NEST deal produces — 60 documents across ten silos, each with an owner, a gate, and prerequisites |
| **`/nest-deal-run`** | Run a deal end-to-end through every NEST engine — readiness, preflight, success prediction, stairway pathway, POM sizing, document package, and… |
| **`/nest-house-style`** | The locked writing format for any NEST document — client brief, internal brief, design brief, proposal, fee schedule, research handoff, or meeting… |
| **`/nest-truth-shield`** | Verification pass before any NEST claim, number, entity, or status goes to a client, partner, or regulator |
| **`/nest-filecabinet`** | File what NEST did today into a dated, append-only log — decided, built, found, open |

**The intended flow.** `kevin` appears twice because it brackets the others — a session that opens on agreed facts but never closes on a filed record leaves the next one reconstructing both from memory.

```
kevin             →  open the session on generated, agreed facts
nest-docs         →  decide what the silo owes
nest-deal-run     →  produce the numbers by running the engines
nest-house-style  →  format them into a document, tagged and sourced
nest-truth-shield →  verify every claim before it leaves
nest-filecabinet  →  file what was decided, built, found, left open
kevin             →  close the session and publish it
```

## Design rules

**A skill calls the code. It never reimplements it.** The engines in `backend/services/` are the single source of truth for every NEST number. A skill is the *procedure* for invoking them and presenting the result. The moment a skill hardcodes a threshold there are two sources of truth and one of them is silently wrong.

**A skill earns its place by being run more than once.** A procedure used once is a script. Writing it up as a skill adds a maintenance burden and a second thing to keep true.

---

# `/kevin`

> Run a cross-working session with Kevin — open with the generated synopsis (code pushed, new modules and terms, backend/frontend integration, what regressed), work under the rebuild-don't-patch rule, close by publishing to the shared workspace. Use when starting or ending a joint session, preparing a handoff for Kevin, or when asked what has changed since you last spoke.

## Cross-working session with Kevin

**Open with the synopsis. Close with the publisher. Never quote a number that
did not come from a run.**

Two people working the same codebase from memory end up describing different
commits to each other, and neither notices for a week. Everything in the opener
is generated, so nobody prepares it and nobody can be wrong about it in a way
the other has to politely absorb.

Shared workspace: `C:\Users\Sean Gilmore\OneDrive\Desktop\Kevin`
Repo: `C:\Users\Sean Gilmore\Downloads\NEST-PLATFORM-main\NEST-PLATFORM-main`
(two other NEST-PLATFORM clones exist and are stale — see the workspace's
`DRIVE-MAP.md` before trusting a file found elsewhere)

---

### Open

```bash
python scripts/session_open.py --out docs/sessions/YYYY-MM-DD-open.md
```

Run it before anything is discussed, and show the output. Four sections:

1. **Code pushed since we last spoke** — every commit since the last snapshot.
   If it says *Nothing*, that is the first agenda item. It is a legitimate
   answer some weeks; it stops being legitimate the second week running.
2. **New modules, and terms that need defining** — every new module under
   `backend/`. **Each one gets a Volume 3 or 4A entry before the session
   ends**: what it is, why it exists, who owns it. A module without a
   definition is one the other person guesses at, and two guesses become two
   different systems inside six weeks.
3. **Backend ↔ frontend integration** — reachability, routes the product
   actually calls, verdict spread, each with a delta. A level says where you
   are; only a delta says whether the week worked.
4. **What got worse** — `UNREACHABLE`, `HOLLOW`, `REBUILD` rising. **Handled
   before the agenda**, because a regression discussed at the end of a session
   survives it.

No baseline yet? The opener says so rather than inventing one.

---

### The standing rule

**If a process is flawed, rebuild it end to end. Do not patch it.**

A patch keeps the shape of the mistake and hides it behind a fix. That is
exactly how `routes/phoenix.py` came to answer fifteen endpoints correctly
while computing nothing — one reasonable small fix at a time.

Say the test out loud before choosing: *if we were building this today,
knowing what we now know, would we build it this way?* If no, it is a rebuild.
Either way the decision goes in the day's file cabinet entry with the reason,
so the same module is never argued twice.

This applies to your own work identically. Precedent: the wiring audit was
rebuilt, not patched, when it turned out to count only `@bp.route()` and miss
`@bp.get`/`@bp.post` — a bug that had it recommending `auth` and `preflight`
be deleted.

---

### Verdicts, and what each obliges

| Verdict | Means | Obliges |
|---|---|---|
| `WIRED` | A screen calls it, it calls real logic | Nothing |
| `HOLLOW` | Wired end to end, computes nothing | A body, not a connection |
| `WIRE` | Both halves exist, nothing connects them | Cheapest real progress available |
| `BUILD_FRONTEND` | Reachable, endpoints live, no screen | A screen |
| `REACHABLE_UNUSED` | A route imports it; that route has no frontend | Comes free when the route is wired |
| `UNREACHABLE` | No registered route imports it, through any chain | Route it or delete it — written decision either way |
| `REBUILD` | Registered, exposing almost nothing | See the standing rule |

`HOLLOW` is the one to name out loud. It passes every dashboard check: it
responds, returns valid JSON, looks green, computes nothing. **End-to-end
wiring is not the finish line** — it is the thing that makes an empty route
look finished.

---

### Ground rules, both directions

1. Never push to `main`. PRs only. Never force-push.
2. Numbers come from a run — cite the engine or the commit. Not from a prior
   brief, not from a prior chat.
3. A route that imports nothing computes nothing.
4. New thresholds carry provenance: `HAND_SET`, `RULE_BASED`,
   `MARKET_DERIVED`. There are currently zero `MARKET_DERIVED`, worth saying
   whenever someone calls a threshold calibrated.
5. Deleting an unreachable module is a real answer. Carrying it advertises
   capability the platform does not have.
6. Nothing client-facing ships without `/nest-truth-shield`.
7. Disagreement is resolved by running something, not by seniority. If it
   cannot be resolved by running something, that is a finding — the thing is
   not measurable yet, and making it measurable is the work.

---

### Close

```bash
python scripts/session_publish.py
```

Files the day, moves the snapshot baseline forward, brands the session into
`<workspace>/sessions/`. Then write the journal entry — the script will not,
because git records what changed and never what was decided.

The four log sections, middle two being the ones that matter:

- **DECIDED** — what closed an option and what it rules out. Most valuable,
  most skipped, because at the time the reason feels too obvious to write.
- **BUILT** — from git.
- **FOUND** — what is true now that was not true this morning, **especially
  the unwelcome things**. Findings do not expire because they are inconvenient.
- **OPEN** — unresolved, and who it waits on. An item open a week is itself a
  finding.

---

### Writing to Kevin

Lead with the finding, not the effort. Order the work by what it costs to fix
against what it buys — HOLLOW, then WIRE, then BUILD_FRONTEND, then the
route-or-delete decisions, with anything live and wrong pulled ahead of all of
it.

When the finding is critical of work he did, pair it with one of your own. Not
as softening — because the argument is about writing checks down rather than
eyeballing them, and that argument is only honest if it applies to both of
you.

---

# `/nest-docs`

> The locked design of what a NEST deal produces — 60 documents across ten silos, each with an owner, a gate, and prerequisites. Use when asked what documents a deal needs, what is blocked, what a silo owes, who is responsible for a document, when work can start, or how the POM is composed.

## The NEST document package — locked design

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

### Run it

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

### The ten silos

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

### The rules that make the package mean something

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

### The POM is the one composite

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

### Known gaps in the design

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

### Changing the design

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

---

# `/nest-deal-run`

> Run a deal end-to-end through every NEST engine — readiness, preflight, success prediction, stairway pathway, POM sizing, document package, and fee ledger — and print one consolidated report. Use whenever asked to "run a deal through NEST", size a fee, assess financeability, or produce the numbers behind a brief.

## Run a deal through NEST

One command, the whole chain, real output. This exists because the chain was
being hand-rolled as a throwaway script every time, which meant every brief
risked quoting slightly different numbers.

**Never quote NEST figures from memory. Run this and quote the output.**

---

### Run it

```bash
"C:\Users\Sean Gilmore\AppData\Local\Programs\Python\Python312\python.exe" \
  .claude/skills/nest-deal-run/run_deal.py --deal <path-to-deal.json>
```

With no `--deal` it runs the Horn Lake 2028A reference deal, which is useful
for checking the engines still behave after a change.

Add `--json` to emit machine-readable output for a frontend or an artifact.

Python is not on PATH on this machine. Use the full interpreter path above.

---

### The deal file

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

### What comes back, and how to read it

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

### Reading it honestly

- Every threshold is `HAND_SET` or `RULE_BASED`. **Zero are `MARKET_DERIVED`** —
  no closed deals, no verified EMMA filings. Do not present any output as
  market-calibrated.
- Hours are `HAND_SET_PLANNING_ESTIMATE`, not measured.
- A high readiness score with a preflight `NO_GO` means the checklist has done
  nothing but document, in detail, why the deal fails. Say that out loud.
- The blocking input that appears across the most sections and silos is the
  real critical path, whatever the client thinks it is.

---

### Then what

Feed the output into a document using the `nest-docs` skill, which locks the
format, the confidence tagging, and the anti-fabrication rules.

Do not transcribe numbers by hand between the two. Paste the run output.

---

# `/nest-house-style`

> The locked writing format for any NEST document — client brief, internal brief, design brief, proposal, fee schedule, research handoff, or meeting agenda. Use whenever writing a document that will be read by a client, a partner, Josh, Kevin, or a regulator.

## NEST house style — locked

This is not a style guide. It is a control. NEST documents get read by clients,
counterparties, and eventually regulators.

**Applies to:** client briefs, internal briefs, design briefs, proposals, fee
schedules, research handoffs, meeting agendas, and anything else that leaves
this machine.

**Not this skill.** *Which* documents a deal produces — the 60-document
package, its silos and gates — is **`nest-docs`**. This skill governs how a
document is written, not which documents exist.

---

### 1 · Verify before you write

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

### 2 · Get numbers from the engines, never from memory

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

### 3 · Required sections

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

### 4 · Naming

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

### 5 · Voice

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

### 6 · Client-facing vs internal

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

### 7 · Before you ship

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

---

# `/nest-truth-shield`

> Verification pass before any NEST claim, number, entity, or status goes to a client, partner, or regulator. Use when asked "do you agree", before sending anything client-facing, when auditing a module's honesty, or whenever a status indicator claims something is working. Catches fabricated entities, unbacked thresholds, and green lights that measure nothing.

## Truth shield

A verification discipline, not a review. The question is never "does this read
well" — it is **"is each of these things true, and how do I know."**

This exists because the platform has already shipped untrue things. Six modules
had fabricated counterparties stripped. A seventh survived until August 2026:
`routes/hawkeye.py:26` still asserts NEST has `"relationship": "existing"` with
six institutional buyers that do not exist. The EMMA connector hardcodes
`status = CONNECTED` and returns HTTP 403 on every call.

Both would have been caught by the checks below in under five minutes.

---

### The four failure modes, in order of how much damage they do

#### 1 · Fabricated entities

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

#### 2 · Status that measures nothing

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

#### 3 · Numbers without provenance

**Check:** every threshold and every dollar figure carries one of `HAND_SET`,
`RULE_BASED`, `MARKET_DERIVED`, and every claim carries `verified` /
`asserted` / `assumed`.

**NEST currently has zero `MARKET_DERIVED` thresholds** — zero closed deals,
zero verified EMMA filings. Any document, screen, or sentence implying market
calibration is false. This includes softer phrasings: "benchmarked",
"market-tested", "based on comparable transactions".

**Remedy:** say hand-set. It is a stronger position than false precision that
a sophisticated client will find.

#### 4 · Stale claims restated as current

A fact verified months ago, repeated today as though re-checked.

**Check:** does the source carry a verification date, and is the underlying
thing still true? `docs/STATE.md:33` lists the "MSRB/EMMA corpus" under
**genuinely real** — which contradicts the current state of 0 verified filings
and a 403ing connector. That line was true when written and is not true now.

**Remedy:** re-verify or re-tag as `asserted` with the original date. Never
promote an `asserted` claim to `verified` without actually checking.

---

### Procedure

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

### When asked "do you agree?"

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

### Standing red list

Known-untrue things in this codebase. Update as they are fixed; do not let this
list go stale.

| Location | Problem | Status |
|---|---|---|
| `routes/hawkeye.py:26` | Six fabricated buyers with `"relationship": "existing"` | **Open** |
| `services/data_connectors.py:321` | EMMA hardcoded CONNECTED; endpoint returns 403 | **Open** |
| `docs/STATE.md:33` | Lists EMMA corpus as "genuinely real"; contradicted | **Open** |
| `services/emma_engine.py` | 0 verified filings, 10 modeled | Labelled honestly |
| Auth on `/api/deals` | Responds without auth; 4 tests failing | **Open**, known |

---

# `/nest-filecabinet`

> File what NEST did today into a dated, append-only log — decided, built, found, open. Use at the end of a working session, when asked to write up the day, when preparing a handoff for tomorrow, or when someone asks why a past decision was made.

## File Cabinet

**One file per day. Four sections. Append only.**

A single day here produced ten threads, six commits, five desktop documents,
three skills, a manual volume and an audit. By next Tuesday nobody will
remember why `NO_CONDUIT_ISSUER` was left at `NO_GO`, or that Volume 1 had
already answered the POM drafting question.

The file cabinet exists so the state of the union, the client brief, and
tomorrow's first prompt **fall out of the log** instead of being reconstructed
from memory — which is where invented facts come from.

Logs live in `docs/filecabinet/YYYY-MM-DD.md`.

---

### File the day

```bash
"C:\Users\Sean Gilmore\AppData\Local\Programs\Python\Python312\python.exe" \
  .claude/skills/nest-filecabinet/file_day.py
```

It reads git for what was **built** and writes a scaffolded entry. Everything
else needs a human: git records what changed, never what was decided or found.

Options: `--date YYYY-MM-DD` to backfill · `--handoff` to also emit tomorrow's
starting prompt · `--print` to write nothing and just look.

---

### The four sections

**DECIDED** — a choice that closes an option, with the reason. The most
valuable section and the one most often skipped, because at the time the reason
feels obvious. It will not be. One line each: *what was decided, why, what it
rules out.*

**BUILT** — commits, modules, documents. Generated from git.

**FOUND** — anything discovered that was not true before, especially unwelcome:
a fabricated buyer list, a connector reporting healthy while returning 403, a
threshold contradicting another threshold. **Findings do not expire because
they are inconvenient.** A finding filed and unfixed stays on the list until
someone fixes it or writes down why not.

**OPEN** — what is unresolved, and who it is waiting on. This becomes
tomorrow's agenda. An item that has been open for a week is itself a finding.

---

### Rules

**Append, never rewrite.** If yesterday's entry turns out to be wrong, correct
it in *today's* entry and link back. A log that gets edited is a log nobody can
trust to reconstruct a decision.

**File the same day.** A day filed three days later is a day half-invented.

**Never file a number you did not run.** The log feeds briefs; a wrong number
here propagates into a client document. Cite the engine or the commit.

**File the unflattering things.** A log containing only progress is a
newsletter. The audit findings, the four failing auth tests, the module nobody
can vouch for — those are the entries that will matter in three months.

---

### Reading it back

- **State of the union** — read the DECIDED and OPEN sections since the last
  one. That is the agenda.
- **Why did we do it this way** — grep DECIDED.
- **What is still broken** — grep FOUND, minus anything a later entry closes.
- **Tomorrow's first prompt** — `--handoff` renders OPEN into a starting brief.

---

### Format

```markdown
# 2026-08-04

## DECIDED
- Fee schedule settles at 2.75% success fee. Rules out the 3.625% blended
  figure in the prospectus and the 2.25% convention in code.

## BUILT
- `444d762` POM engine — offering-document hours derived, not asserted
- `docs/NEST_DICTIONARY.md` — Operations Manual Volume 3, generated

## FOUND
- `routes/hawkeye.py:26` ships six fabricated institutional buyers carrying
  `"relationship": "existing"`. Live misrepresentation. **Unfixed.**
- EMMA connector hardcodes `status = CONNECTED`; endpoint returns 403.
  `verified 2026-08-04`

## OPEN
- Bond counsel — who, and retained by whom? Blocks 3 silos, 10 documents.
- Reconcile five conflicting fee sources before automating any fee deliverable.
```

