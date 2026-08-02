# NEST Glossary — Agents, Engines & Modules

> **Purpose:** the canonical map of every named agent, engine, and product pillar in the platform — what it was *intended* to do, what it *actually* does today (verified, not assumed), what feeds it, what it feeds, and what's broken. Say a codename ("run Sentinel," "call Marshal") and this is what it should resolve to.
>
> **Companion docs, don't duplicate:** `docs/STATE.md` (deployment/infra state, live vs demo tally), `AGENTS.md` (repo charter, session protocol), `agents/desk_registry.py` (the machine-readable org chart this document narrates), `docs/audit/` (prior page-by-page frontend/backend audits).
>
> **Confidence tags** (same convention as `STATE.md`): `verified` (read the code and/or ran it this pass) · `asserted` (stated in docs/comments, not independently re-checked) · `assumed` (inferred, flagged for someone to confirm).
>
> **This is a first pass, not a finished catalog.** The backend has ~160 files; this document covers the ~30 modules directly verified across this session's work plus the full agent roster from `desk_registry.py`. Everything not yet covered is listed at the bottom under "Not yet catalogued" — extend this file, don't fork it.

---

## 0. Executive Summary — how this all works together, concretely

The platform is one deal moving through a sequence of desks. Here's the real, current path — what's actually wired vs. what should be but isn't — walked through on one concrete example.

**Example: a $65M CCRC (senior living) refinancing shows up.**

1. **Sourcing (Eagle Eye / SignalEngine "Steven").** A real SEC EDGAR filing — say an 8-K merger agreement or an S-11 REIT registration for a senior-living operator in Texas — gets picked up by `SignalEngine.scan_edgar_ma_targets()` or `scan_sector_comparables()`. It's scored in real time (NAICS match, revenue-in-range, recency, hot-state) and comes back `HOT` or `WARM`, routed to a desk (`ma`, `cre`, or `bond_desk`). **If this happens** — a real filing scores HOT — **then** it's tagged with a recommended agent (Merlin for M&A, Eagle Eye for CRE) and a next step ("Schedule intro call"). See §3 for the full worked trace.
2. **Promotion to deal (per ADR-0002).** A human (or eventually Bernard) reviews the signal and clicks "Promote to Deal." This is the *only* front door into the `deals` table — nothing else is allowed to insert directly. **If this doesn't happen**, the signal sits in the scanning layer forever; it never becomes a deal NEST can actually work.
3. **Bond sizing.** `deal_flow.py::run_intake()` calls `intelligence_engine.py::size_bond()` — real LTC/LTV/NOI-based sizing math, produces a sources-and-uses, a leverage headroom check, and (as of this session's fix) an honest `equity_gap_usd` if the deal can't be funded by debt alone within the sector's real leverage ceiling. **If** the deal needs more debt than the sector ceiling allows, **then** it now surfaces a real equity gap instead of silently over-levering past the ceiling (Ticket 11 — this was a live, session-verified bug, not hypothetical).
   - **Known gap:** `bond_type_engine.py` — the engine with the actual bond-type-selection logic (which of 16 bond types, sector-aware suitability, real par sizing) — is **not** called here. The live pipeline sizes the deal but never runs it through the real bond-type engine. That engine is only reachable via its own separate route.
4. **Credit underwriting (Maxwell).** `run_credit()` calls the Universal Credit Policy (`intelligence_engine.py::underwrite()`) — real DSCR/leverage/equity/sponsor-experience gates — then generates a credit memo via Claude. **If** the memo generation fails, **then** (as of this session's Gap 2 fix) the real exception is now logged instead of silently producing `credit_memo: None` that looks identical to "no memo needed yet."
5. **Rating (Moody's Mirror / S&P Mirror).** `run_rating()` calls both mirror agents for real predicted ratings — genuinely wired, confirmed this session.
6. **Structuring.** `run_structuring()` builds a covenant package keyed off deal type and credit grade (sector-blind — a real, unfixed dead-parameter bug found this session). This is where `bond_type_engine.py`'s real amortization math (CAB accretion, sculpted DSCR targeting, the 16 bond types) *should* enter but currently doesn't.
7. **Enhancement (Marshal).** If the deal needs a wrap or contract surety, `surety_scout.py` prices it — as of this session, contract-surety products (performance/payment bonds) price off real construction contract value, not full bond face (Ticket 7 fix). Bond insurance pricing (a different product — wrapping the bond itself) uses the real two-writer market (Assured Guaranty ~58%, BAM ~42%) and the real 0.75-1.5% premium range (Ticket 19 addition).
8. **Placement (Sterling / Hawkeye).** Real buyer-scoring and order-book logic exists, but the actual buyer list (`BUYER_UNIVERSE`) is six fictional placeholder firms — **not fixed this session**, needs real business-development relationships, not code.
9. **Coordinated/pooled offering ("Rico," new this session).** If Eagle Eye's `find_comparable_deals()` finds 3+ other real deals with similar LTV/DSCR/leverage/rating in the same sector, the platform can propose bundling them into one coordinated offering instead of placing each separately — the cohort-matching math is built; the actual pooling/tranching structuring layer is the next piece.

**The one-sentence version:** signals get found and scored for real, sizing and underwriting math is real and (as of this session) more honest about its own limits, but the bond-type-selection engine and the real buyer list are the two biggest disconnects between "the math is right" and "the platform actually places a bond."

---

## 1. How to read this

Three tiers exist in this platform, and they get confused with each other constantly:

1. **Codenamed agents** — a persona with a name (Bernard, Maxwell, Sentinel...) mapped to a real Python file in `agents/`, registered in `agents/desk_registry.py`. You "call" these by name.
2. **Platform engines** — real technical infrastructure with a functional (not persona) name (`bond_type_engine.py`, `signal_engine.py`, `credit_engine.py`...). These usually power one or more codenamed agents or product pillars, but aren't themselves addressed by name in conversation.
3. **Product pillars** — client/user-facing subsystem names (Eagle Eye, Hawkeye, Phoenix, Convergence) that bundle multiple engines + routes + frontend pages into one product surface. Listed in `desk_registry.py` under `platform_components`, not `agents`.

Not everything needs a codename. An engine only gets promoted to a codenamed agent if there's a real reason to address it conversationally as a persona (matches this platform's existing convention — see §2).

---

## 2. Codenamed Agent Registry

Source of truth: `agents/desk_registry.py` (14 desks + Orca C-suite). This table adds INTENDED / ACTUAL status this session verified or could not verify — `desk_registry.py` itself only tracks name/role/file, not behavior.

| Codename | Desk | Intended Role | File | Status |
|---|---|---|---|---|
| **Bernard** | Orca C-Suite | CEO / Platform Orchestrator — reads intake, greenlights deal advancement | `bernard.py` | `asserted` real — not directly verified this session |
| **Vector** | Bond Desk | Market signals monitoring, 14 signals every 15 min | `vector_agent.py` | `asserted` real — not directly verified |
| **Apex** | Bond Desk | Rate hedging, short position management | `apex_agent.py` | `asserted` real — not directly verified |
| **Maxwell** | Credit UW | Senior Credit Underwriter — DSCR/LTV/LGD/obligor grading | `maxwell.py` | `verified` real. **Not** a 7th duplicate scorer (Ticket 5) — calls `services/core.py`'s real credit computation and has Claude write narrative around it. Different job from the 6 competing `score_deal()` implementations. |
| **Prometheus** | Structuring | Financial modeling — proforma, stress, feasibility | `prometheus.py` | `asserted` real — not directly verified |
| **Morgan** | Documents | Document drafting, Jimmy Lee tone | `morgan.py` | `asserted` real — not directly verified |
| **Auditor** | Construction Risk | Construction compliance monitoring | `auditor.py` | `asserted` real — not directly verified |
| **Marshal** *(renamed from SuretyScout this session)* | Enhancement | Surety bond sourcing/matching, premium calc | `surety_scout.py` | `verified` real. **Fixed this session (Ticket 7):** `calculate_premium()` priced contract-surety products (performance/payment/bid/maintenance bonds) off full bond face instead of construction contract value — ~2.5x overstatement. Now prices contract-surety products off `construction_contract_value_usd` (defaults to 65% of bond face if not supplied), financial-guarantee products (`cash_surety_sbloc`/`lc`/`parametric`) correctly still price off bond face. |
| **Sterling** | Placement | Investor placement, CRM, book building | `sterling.py` | `asserted` real — not directly verified |
| **LenderScout** | Placement | Direct lender sourcing, 800+ database | `lender_scout.py` | `asserted` real — seed roster (`SEED_LENDERS`) not verified as real vs. placeholder firm names, same risk class as the Hawkeye finding below. **Flagged for verification.** |
| **Bridge** | Operations | Perm debt monitoring, 18mo pre-stabilization | `bridge_agent.py` | `asserted` real — not directly verified |
| **Chain** | Operations | On-chain deal recording | `chain_agent.py` | `asserted` real — not directly verified |
| **Sentinel** | Surveillance | Risk assessment across 7 dimensions, automated alerts | `sentinel.py` | `verified` real. **Fixed this session (Ticket 6):** `score_credit_risk()` used independently-invented DSCR/LTV/Debt-EBITDA cutoffs instead of the real published benchmarks in `rating_benchmarks.py`. Now pulls real thresholds (`STRUCTURING_CRITERIA`, `SECTOR_SCORING_OVERRIDES`, `MOODYS_FINANCIAL_METRICS`) so it can't silently drift from what Maxwell/Architect use for the same deal. |
| **Merlin** | Business Dev | M&A intelligence, NAICS scan, target scoring | `merlin.py` | `verified` real scoring/game-theory logic. **Fixed this session (Ticket 18):** `scan_edgar_for_targets()` silently fabricated entirely fictional acquisition targets ("Landscaping Co #1," random revenue/EBITDA) as an automatic fallback whenever the real EDGAR path (via the now-defunct `jimmy_lee`/`EDGARPlugin`) returned nothing — which was the common case. Now sources real targets via `SignalEngine`; fabricated data requires explicit `allow_synthetic=True` and is tagged `is_demo=True`. |
| **Aria** | Business Dev | Client outreach, cold/warm sequences | `aria.py` | `asserted` real — not directly verified |
| **Quantum** | Treasury | HFT fund optimizer, portfolio management | `quantum.py` | `asserted` real — `get_lc_capacity(aum)` (80% of AUM, phase-tiered) verified as genuinely distinct from `ma_bond_engine.py::lc_capacity_analysis()` (50-70% of a specific deal's B-tranche, seasoning-gated) — not duplicates despite the surface-level name similarity flagged in the build brief. |
| **Rico** *(new this session, per Sean)* | Placement *(proposed)* | Coordinated pooled/multi-deal offering structuring — bundles several comparable deals (same asset class, similar LTV/DSCR/leverage/rating) into one coordinated offering with a shared enhancement partner, modeled conceptually on CMBS/MBS pooling. | `services/eagleeye_scanner.py::find_comparable_deals()` (cohort-matching, built) + pooled-offering structuring layer (**not yet built** — next step) | `in_progress`. Deliberately **not** named `rico_engine.py`/`RicoEngine` in code (see note below) — "Rico" is the callable persona name only, registered in `desk_registry.py`, mapped to a neutrally-named module. |

**Note on "Rico":** the codename references RICO (the federal anti-racketeering statute) as a conceptual shorthand for "charge/bundle the whole organization together, not piecemeal" — Sean's own analogy for why bundling comparable deals into one coordinated offering is structurally stronger than pursuing them one at a time. The underlying module is named neutrally (`pooled_offering_engine.py` or similar) so the statute's name never appears as a literal source-code identifier — avoids an unfortunate-looking artifact in due diligence or code review for what is an entirely legitimate structure.

**Named roles in `desk_registry.py` with `agent_file: None`** — pure org-chart placeholders, nothing built: CFO Agent, COO Agent, CTO Agent, Head of BD, In-House Counsel/CCO, MD Agent, Associate Agent, Analyst Agent, Credit Analyst, Credit Committee, Structuring Analyst, Moody's Mirror Agent *(has a file, see below — registry may be stale)*, S&P Mirror Agent *(same)*, Rating Coordinator, Documents Lead, Version Control Agent, ~10 Legal & Compliance roles, ~5 Trustee Liaison roles, ~9 Construction Risk roles, Enhancement Strategy/LOC Bank/Bond Insurer Liaison/Federal Programs, Pricing Analyst, BD Partner Interface, Debt Service Admin/EMMA Compliance/Covenant Monitor, Refunding ID/Restructuring/Workout Support, Pipeline Tracker, Conference & Brand, Ramp Admin/Draw Manager.

**Registry drift found this session:** `moodys_mirror.py` and `sp_mirror.py` **do exist** (called directly from `deal_flow.py::run_rating()` — verified, real, wired into the live pipeline) despite `desk_registry.py` marking them `"new": True` with no `existing_agent` tag. The registry itself needs a pass to reconcile against what's actually on disk — `desk_registry.py` is asserted, not continuously verified.

---

## 3. Platform Engines (infrastructure, not personas)

These power the codenamed agents and product pillars above/below. Verified this session, with real INTENDED / ACTUAL / FIX status.

**Naming rule for this whole document:** if something has a real codename (§2), it's headed by that codename. If it doesn't, the section header is its plain, current, literal name in the codebase (the `services/xxx.py` path or `ClassName`) — never a placeholder, never an invented label. Every heading below is a real file that exists on disk right now.

### `services/bond_type_engine.py`
- **Intended:** generate every viable bond type × amortization × par combination for a deal, score by suitability, real S&P OPBA math.
- **Actual (verified):** real math throughout. This session added 6 new bond types (Housing Authority, GAN, RAN, TAN, VRDO, Bridge-to-Permanent), real CAB accretion math, sector-aware NAICS-driven eligibility and suitability scoring (`REVENUE_SECTOR_REGISTRY`), dynamic par sizing (was snapping to a fixed $25M-floor ladder, couldn't produce real sub-$25M sizes), and fixed BAN/Mezzanine eligibility gates that were structurally unreachable (thresholds sat on the wrong side of the function's own defaults).
- **Fix needed:** **not wired into the main deal pipeline.** `deal_flow.py::run_full_pipeline()` — the actual orchestrated deal lifecycle — never calls this engine; it uses `intelligence_engine.py::size_bond()` instead. This engine is only reachable via its own standalone route (`routes/bond_workflow.py`). A deal run through the real pipeline never sees any of this engine's bond-type-selection logic. **This is the single highest-value wiring gap found this session.**

### `services/rating_benchmarks.py`
- **Intended:** real S&P/Moody's published benchmark data (anchor matrix, factor weights, DSCR-by-rating, sector overrides) as the shared source of truth for every scorer.
- **Actual (verified):** real, sourced data. Was documented-but-not-computable in one place (`STRUCTURING_CRITERIA["dsrf_sizing"]` was descriptive text, not a function) — added `dsrf_size()` implementing the real IRC 148(d) safe harbor this session. Was not consumed by `architect.py`/`maxwell_engine.py`/`sentinel.py` at all before this session (Ticket 6) — each had independently-invented thresholds instead.
- **Fix needed:** none remaining from this session's scope. `ENHANCEMENT_RATING_MAP`/`ENHANCEMENT_LEARNING_WEIGHTS`/`HAWKEYE_SPREAD_WEIGHTS` are correctly **absent** — those are unsourced proposed weights per the build brief, and building them without real rating-agency criteria would be a regression, not a fix.

### `services/credit_engine.py`
- **Intended:** capital-stack math, LGD scenarios, credit scoring, free-equity/roll-forward calculations.
- **Actual (verified):** `compute_metrics()` had a real silent-failure bug — missing/zero denominators (debt_service, total_assets) defaulted to `1` instead of raising, producing nonsense output (DSCR of 1,278,200× on one real 2027A test) with a confident grade attached. **Fixed this session (Ticket 9)** — now raises on missing/zero required inputs, bounds-checks DSCR/equity_pct. Added real `free_equity()` and `roll_forward_equity()` (Ticket 17/19) — generic, percentage-driven, not hardcoded to any deal, with explicit `as_completed`/`as_is` valuation-basis labeling.
- **Fix needed:** `compute_capital_stack()` is a separate, simpler senior/mezz model with its own independent fee/reserve assumptions — doesn't reconcile against Horn Lake's real confirmed stack ($35M equity/$65M bonds/70% LTC returns $23M equity instead, per the build brief's Ticket 17). Not fixed this session — flagged as needing real per-phase cost data for Phases 2-6 that doesn't exist yet.

### `services/intelligence_engine.py`
- **Intended:** the real bond-sizing/underwriting engine actually wired into `deal_flow.py`'s live pipeline — sizing per deal type, universal credit policy checks, covenant packages.
- **Actual (verified):** real math, self-documents its own gaps honestly (`"note": "Full spec pending Use Case Manual Ch.X"` on several sub-methods rather than pretending completeness). **Fixed this session (Ticket 11):** `size_ma_acquisition()`'s balance check unconditionally added the full sources/uses gap to `bond_amount`, which — because reserves and cost-of-issuance were never included in the original `bond_needed` formula — routinely pushed senior leverage past the sector's real ceiling on essentially every deal, not just edge cases. Now caps the debt increase at real headroom and surfaces any remainder as `equity_gap_usd`.
- **Fix needed:** `build_covenant_package(deal_type, credit_grade, sector)` accepts `sector` but never uses it in the body — dead parameter, covenant terms don't actually vary by sector despite the signature promising it. Not fixed this session (found during the audit pass, out of scope at the time).

### `services/deal_flow.py`
- **Intended:** orchestrate the real deal lifecycle end to end — intake → credit → rating → structuring.
- **Actual (verified):** genuinely real, wired orchestrator — calls `intelligence_engine.py`, `credit_memo_agent.py`, `moodys_mirror.py`/`sp_mirror.py` for real. **Fixed this session (Gap 2):** `run_credit()` and `run_rating()` both caught real errors with bare `except Exception: <swallow>`, making a real failure look identical to "nothing to report." Now logs the real exception via `logger.exception()` before continuing.
- **Fix needed:** doesn't call `bond_type_engine.py` (see above) — the real bond-type/amortization selection logic never enters this pipeline.

### `services/phoenix_engine.py`
- **Intended:** distressed CRE acquisition/rehabilitation pipeline — sourced from Supabase deals with real distress indicators (DSCR<1.5, LTV>70, pipeline status).
- **Actual (verified):** `list_deals()`/`get_deal()` correctly check Supabase first. **Fixed this session (Ticket 8, partial):** `create_deal()`/`update_deal()` only ever wrote to a local in-memory dict — never to Supabase, even when configured — so a deal created via the API silently vanished on restart and never appeared in `list_deals()`. Now both write through to the real `deals` table when configured.
- **Fix needed:** full CRUD unification with `routes/deals.py` (three separate systems maintain deal state — `routes/deals.py`, `routes/phoenix.py`/`phoenix_engine.py`, and Supabase directly) needs a real schema decision from Kevin, not a blind consolidation. Not attempted this session.

### `services/signal_engine.py` — **"Steven" — the real base of the scanning cluster**

- **Intended:** a three-node pipeline — Origination (find real signals) → Qualification (score them against real benchmarks) → Action Routing (assign to a desk + next step) — so a raw EDGAR filing becomes an actionable, prioritized lead instead of a wall of noise.

- **What feeds it (real, verified):**
  - SEC EDGAR full-text search (`efts.sec.gov`) — merger/acquisition agreements, Schedule 13D ownership changes, 10-K revenue-size indicators, S-11/424B5 sector-comparable filings.
  - Census Bureau BPS — state-level residential permit counts.
  - FRED — 10yr treasury, 30yr mortgage, CRE delinquency rate (added this session, merged in from `EagleEyeScanner`).
  - Static real reference data — the construction/bridge loan maturity wall ($162.1B 2026 / $167.7B 2027, also merged in this session).

- **What it feeds:** `routes/signals.py` (the real `/api/signals` REST API), `ConvergenceEngine.add_signals()` (via `AutonomousScanner`), `MerlinAgent.scan_edgar_for_targets()`, and (as of this session's fix) `routes/eagleeye.py::cre_heatmap()`.

- **Concrete worked example — "if this happens, then this happens":**

  1. **Input:** SEC EDGAR publishes an 8-K filing: *"Sunrise Senior Living Partners LLC enters merger agreement, $45M transaction, Austin TX, SIC 6231 (Nursing & Residential Care)."*
  2. **Node 1 — Origination.** `scan_edgar_ma_targets()` queries EDGAR full-text search for `"merger agreement" OR "acquisition agreement"` across recent 8-K/SC 13D filings, finds this hit, and builds a raw signal: `{signal_type: "ma_target", entity: "Sunrise Senior Living Partners LLC", trigger_event: "merger_agreement", naics_hint: "6231", state: "TX", filing_date: <today>, raw_score: 0.0}`.
  3. **Node 2 — Qualification.** `qualify_signals()` calls `_score_ma()`:
     - Revenue mentioned in range ($30-150M band, "$45M" matches) → **+0.4**
     - NAICS `6231` starts with a target prefix (`623` = Nursing & Residential Care, now part of the broadened `_TARGET_NAICS` set built from `emma_engine.SECTOR_NAICS_MAP`) → **+0.2**
     - Filing is recent (0-180 days old) → **+0.1**
     - Trigger is a merger agreement (not Schedule 13D) → **+0** (that bonus is 13D-specific)
     - **Total score: 0.7** → grade = `HOT` (threshold ≥0.7), desk = `ma`.
  4. **Node 3 — Action routing.** `route_signal()` attaches: `{desk: "ma", agent: "merlin", next_step: "Schedule intro call", outreach_template: "ma_intro"}`.
  5. **Output:** the signal is now sitting in `/api/signals` (via `routes/signals.py::list_signals()`) as a `HOT`, `ma`-desk-routed, Merlin-assigned lead with a real EDGAR URL attached — ready for a human (or Bernard) to review and, per ADR-0002, promote to a real Deal.
  6. **If instead** the same filing had been a routine 10-K with no NAICS match and a filing date 400 days old, the score would land under 0.3 (`COLD`), `qualified = False`, and it would **never** reach Node 3 or show up in the API's default signal list at all — this is the real filter that keeps the desk from being flooded with noise.

- **Fixed this session (Ticket 18, full consolidation):** four independent EDGAR client implementations existed before this session (`EagleEyeScanner`, `AutonomousScanner`, `SignalEngine`, `MerlinAgent` each had their own). This is now the real base — `EagleEyeScanner`'s FRED market context, sector-comparable EDGAR search, and maturity-wall coverage were merged in as real, scored/routed methods; `AutonomousScanner._scan_edgar()` and `MerlinAgent.scan_edgar_for_targets()` both now delegate here instead of maintaining duplicate httpx clients. NAICS/sector coverage expanded this session from 4-5 narrow codes (nursing/health care, real estate, data processing) to 13+ real sectors (hospitals, senior living, charter/higher education, multifamily, hospitality, solid waste, water/sewer, electric power, airports, manufacturing, retail, office) — **this narrow coverage was the direct, traced cause of the "why do I only ever see Jacaranda" complaint** (see §4, Eagle Eye).

- **Fix needed:** the frontend's signals surface expects a richer API contract (`/api/signals/query`, `/latest`, `/related`, `/poll/fred`, `/poll/edgar`, `/alerts`, `/vector/latest`, `/vector/history`) than `routes/signals.py` actually implements (`/api/signals`, `/scan`, `/stats`, `/node-status`, `/<id>`, `/<id>/action`). Real contract mismatch, not yet reconciled — deferred wiring-pass item.

### `services/eagleeye_scanner.py`
- **Intended:** autonomous deal-finding across all capital types — the FRED/EDGAR/maturity-wall data source now consolidated into `signal_engine.py` above.
- **Actual (verified):** `scan_for_equity_partners()` (Ticket 11) and `find_comparable_deals()` (Ticket 22 partial, this session) both added — real gap-detection and cohort-matching math, deliberately returning empty results rather than fabricating counterparties/comparable deals when no real roster/candidate data exists (mirrors the Hawkeye fix below).
- **Fix needed:** pooled-offering structuring layer (turn a matched cohort into one structured coordinated offering — "Rico," see §2) not yet built.

### `services/autonomous_scanner.py`
- **Intended:** scheduled background loop pulling FRED + EDGAR, feeding `ConvergenceEngine`, Claude-synthesizing findings.
- **Actual (verified):** real loop/threading, real Claude synthesis step. `_scan_fred()`'s delta/movement detection (flags ≥3bps moves across consecutive observations) is genuinely distinct from `signal_engine.py`'s point-in-time FRED snapshot — correctly left as-is, not a duplicate. `_scan_edgar()` now delegates to `SignalEngine` (Ticket 18) instead of a fourth independent EDGAR client.
- **Fix needed:** none remaining from this session's scope.

### `services/convergence_engine.py`
- **Intended:** watch signal feeds, detect 2-3 signals converging on the same entity, surface HEAT events.
- **Actual (verified, before this session):** **serious finding** — the module unconditionally seeded itself with four entirely fabricated entities ("Meridian Development Partners LLC," "1400 Maritime LLC," etc., fixed random seed 42) on construction, indistinguishable from real detections in the API response. Zero real data source of its own.
- **Fixed this session (Ticket 18):** demo seeding is now opt-in (`seed_demo=True`, default `False` in production per `app.py`), every demo signal/HEAT event tagged `is_demo=True`, and a real `add_signals()` method feeds genuine EDGAR-sourced signals in from `AutonomousScanner`.
- **Fix needed:** none remaining from this session's scope.

### `services/counterparty_db.py`
- **Intended:** real counterparty rosters (broker-dealers, bond counsel, trustees, rating agencies, bond insurers, LOC banks) per the Operating Framework.
- **Actual (verified):** roster names appear real (Piper Sandler, Orrick, U.S. Bank, Moody's, Assured Guaranty, JPMorgan, etc. — not independently verified as current/accurate, but not obviously fabricated placeholders either, unlike the Hawkeye finding below). **Added this session (Ticket 19):** real bond-insurance mechanics — Assured Guaranty (~58%) and BAM (~42%) as the two actually-active writers (Berkshire Hathaway Assurance correctly excluded — selective, not one of the two active writers), premium priced off total scheduled debt service within the real 0.75-1.5% market range, not off bond face.
- **Fix needed:** none remaining from this session's scope.

---

## 4. Product Pillars

### Eagle Eye
- **Intended:** the platform's deal-finding machine across all capital types — bonds, bridge, perm, equity, C&I.
- **Hierarchy:** product pillar → `services/eagleeye_scanner.py` (FRED/maturity-wall/comp-matching) + `services/signal_engine.py` (real scanning base, consolidated this session) + `services/convergence_engine.py` (HEAT detection) → routes `routes/eagleeye.py`, `routes/signals.py`, `routes/convergence.py`, `routes/scanner.py`.
- **What feeds it:** SEC EDGAR (real), FRED (real), Census Bureau BPS permit counts (real). NOT yet real: title reports, UCC filings, CoStar, PropStream, Chicago Title (Ticket 22 — full CRE intelligence expansion, unbuilt).
- **What it feeds:** deal intake (via "Promote to Deal," per `docs/adr/0002`), Hawkeye placement (downstream), the coordinated-offering / "Rico" workflow (upstream via `find_comparable_deals()`).
- **Fixed this session:** the CRE heatmap (`routes/eagleeye.py::cre_heatmap()`) was asking Claude to invent a heatmap from a generic prompt with no real signal data behind it (a `cre_signals` variable was computed but never actually used in the prompt), and fell back to the same static 5-property, 4/5-senior-living list (Jacaranda Trace, Convivial St. Petersburg, Pacific Ridge, Desert Springs, Dominion Edge) whenever Claude was unavailable — which is always true without `ANTHROPIC_API_KEY` configured. **This was the direct cause of the "why do I only ever see Jacaranda" complaint.** Now builds the heatmap from real, qualified `SignalEngine` signals across the full sector registry first; static fallback only fires when the real scan is genuinely empty.
- **Fix needed:** full Ticket 22 CRE intelligence expansion (title reports, UCC/holding-company cross-reference, appraisal engine, regional facility footprint search) — unbuilt, needs real vendor data plugins.
- **Frontend:** `frontend/app/eagleeye/page.tsx`, `frontend/components/EagleEye*.tsx` (canonical — see §6). **Do not confuse with the identically-named components in `frontend-v2/`, which is legacy.**

### Hawkeye
- **Intended:** real buyer-scoring and placement — sector match, ticket-size fit, DSCR vs. risk appetite, yield clearance, relationship weighting, order-book allocation.
- **Actual (asserted, per build brief — not independently re-verified this session):** the matching/allocation logic is real and sophisticated. `BUYER_UNIVERSE`, the fallback buyer list, is six fictional placeholder accounts ("Redwood Family Office," "Cascadia Endowment Fund," etc.) — the same fabrication pattern found and fixed in `ConvergenceEngine` and `MerlinAgent` this session, **but not yet fixed in Hawkeye itself.**
- **Fix needed:** not a code fix — real business-development work to populate the `investors` table with actual named institutional relationships. `routes/hawkeye.py::_get_live_deals()`'s hardcoded fallback figures for Jacaranda Trace ($231M) and Convivial St. Petersburg ($172.5M) also reportedly conflict with figures used elsewhere in the engagement — needs Sean's confirmation on which are current before touching (explicitly deferred).

### Phoenix
- **Intended:** distressed CRE acquisition and rehabilitation — sourcing, underwriting, milestone tracking for workout/discount-purchase deals.
- **Hierarchy:** product pillar → `services/phoenix_engine.py` → `routes/phoenix.py`.
- **Fixed this session:** see `services/phoenix_engine.py` entry in §3 (create/update now write through to Supabase).
- **Fix needed:** full CRUD unification with `routes/deals.py` (Ticket 8 remainder).

### Convergence
- **Intended:** multi-signal detection layer sitting on top of Eagle Eye's raw signals — surfaces when 2-3 independent signals point at the same entity (a real deal forming), not noise.
- **Fixed this session:** see `services/convergence_engine.py` entry in §3 (fabricated demo data no longer auto-seeds in production).

---

## 5. Frontend: canonical vs. legacy — a correction

**This session initially gave incorrect guidance** pointing at `frontend-v2/` (`EagleEyeMain.tsx`, `EagleEyeV2.tsx`) as "the Eagle Eye frontend module." That is **wrong** per `AGENTS.md`, which explicitly states:

> `frontend-v2/` — LEGACY, do not build on. **Never build on `frontend-v2/` or the V2/V3/V4 repos — reference-only (ADR-0003).**

The canonical frontend is `frontend/` (Next.js 14 App Router, deployed to `www.nestadvisors.tech` via Vercel). It has its **own, separate copies** of the same-named components (`frontend/components/EagleEyeMain.tsx`, `EagleEyeV2.tsx`, `EagleEyeCRETab.tsx`, `EagleEyeHeatMap.tsx`, `EagleEyeMATab.tsx`, `EagleEyeScoutDashboard.tsx`, `EagleEyeSignalDetail.tsx`), plus `frontend/app/eagleeye/page.tsx` and `frontend/app/signals/page.tsx`. **This confusion is real and worth noting for the team**, not just this session: an older CTO handoff doc (`docs/handoff/2026-05-29-cto-handoff-keven.md`) asserted the *opposite* — that `frontend-v2/` was canonical ("V4 cinematic") and `frontend/` was "V3 minimalist, deprecated." The canonical designation flipped at some point between 2026-05-29 and the current `AGENTS.md`/`STATE.md` — anyone referencing the older handoff doc for frontend guidance will get it backwards.

---

## 6. Known architecture debt (consolidated)

Cross-referenced from `docs/STATE.md`, `AGENTS.md`, `docs/audit/2026-06-01-white-glove-audit.md`, the CTO handoff, and this session's findings. Not re-verified line-by-line here — see source docs for specifics.

- **001/005 `deals` schema split** — canonical Supabase runs schema 005; some deployed routes still speak 001. Root cause of "everything looks like demo data." Fix reportedly staged, not yet merged (`STATE.md`).
- **`/api/deals` responds without auth** — real, open security gap (`STATE.md`, `AGENTS.md`).
- **Three disconnected deal-CRUD systems** — `routes/deals.py`, `routes/phoenix.py`/`phoenix_engine.py`, Supabase directly (Ticket 8, partially addressed this session — see §3).
- **Six competing `score_deal()` implementations** — `sentinel`, `maxwell_engine`, `risk`, `core`, `credit_engine`, `architect` (Ticket 5, not addressed this session — flagged as landing with Supabase schema consolidation work).
- **Four independent EDGAR scanners** — resolved this session (Ticket 18, see §3).
- **"Three Bernards"** — `routes/bernard.py`, `services/bernard_findme.py` (1,995 lines), `services/preflight_service.py`, `services/intake_brainstorm.py` are four overlapping surfaces (per CTO handoff) — not investigated this session.
- **28 `except Exception: pass` blocks across 17 files** (per backend audit) — this session fixed the two in `deal_flow.py` (Gap 2); the rest are unaddressed.
- **`ConvergenceEngine`/`MerlinAgent` fabrication pattern** — fixed this session. **`Hawkeye`'s `BUYER_UNIVERSE` has the same pattern, not yet fixed** (real business-dev work, not code).

---

## 7. Not yet catalogued

Real, present in the repo, not verified this session — flagged so this document stays honest about its own coverage rather than implying completeness:

`services/nisle_engine.py` (NISLE — "Intelligence Self-Learning Engine," orchestrates 8 DAPT phases per its own docstring; `services/dapt_models.py` backs it with 7 real classes, confirmed present this session; but the docstring's claim of "Phase 8: Agent Injection → inject() methods on Sentinel/Vector/pricing" does **not** appear to be true — no such import was found in `sentinel.py` during this session's other work; NISLE appears referenced only as a preference-weighting label in `services/preference_engine.py` and its own `routes/nisle.py`, not actually injecting into the agents it claims to enrich — **needs a real verification pass, flagged not confirmed**), `engines/architect.py` (real candidate-structure generator, wired into `maxwell_engine.py`, not in `desk_registry.py` under any codename), `services/compliance_engine.py`, `services/licensing.py` (per the build brief: contains real fee data but also non-authoritative personal study-aid content — needs reconciliation), `services/emma_engine.py`, `services/bond_intelligence.py`, `services/ma_bond_engine.py`, `services/phase_bond_engine.py`, and the ~130 remaining backend files not touched this session.
