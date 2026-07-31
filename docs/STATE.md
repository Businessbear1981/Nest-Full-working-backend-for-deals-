# NEST Platform — State

> **Status:** LIVE (production frontend + backend healthy); real open items = auth hardening + deals-schema reconcile + Supabase consolidation
> **Last updated:** 2026-07-14 (agent-infra install; state seeded from the 2026-06-24/27/30 verification passes) · **Last verified:** 2026-06-30
> **One-liner:** the canonical NEST monorepo — Next.js 14 frontend + Flask backend, serving `www.nestadvisors.tech`.
> **Current state:** platform is live end-to-end, but most modules render demo data; the two blockers to "real" are the 001/005 deals-schema split (fix staged) and the unauthenticated `/api/deals` exposure.
> **Links:** `AGENTS.md` (charter/SOP) · `docs/adr/` (ADRs) · GitHub Issues on `Businessbear1981/NEST-PLATFORM` (work tracking)

This is the shared, repo-level context document — what is actually built, wired, and live.
It is updated **via PR, in the same PR as the change that moved the state**. Read it at
session start; never re-explain history that's already recorded here.

Confidence tags: `verified` (checked against ground truth on the stated date) · `asserted` (stated, not re-checked) · `assumed` (best guess).

---

## Live topology (verified 2026-06-24)

| Service | Where | Status |
|---|---|---|
| Frontend (canonical) | Vercel team `ardan-edge-capital`, project `nest-platform` → **`www.nestadvisors.tech`** — builds `frontend/` (Next.js 14) | live |
| Backend (canonical) | Railway → **`nest-platform-production.up.railway.app`** — Flask `v2.0.0`, `service=nest-backend` | live, `/api/health` = 200 |
| Backend (legacy) | `api.nestadvisors.ai` → old Railway service wired to the `NEST-ADVISORS-V2` repo (last deploy May 26) | live but legacy — reference only (ADR-0003) |
| Database (canonical) | Supabase **`tquotedgiapmivitjipn`** (NEST_ADVISORS) — what the Railway backend's `SUPABASE_URL` points at (verified 2026-06-27) | live (ADR-0004) |
| Domains | `.tech` runs the platform; `nestadvisors.ai` serves a separate marketing page | consolidation decision pending |

Health-check `/api/health`, never `/` — root has no route and 404s by design.

## What is real vs. demo (verified 2026-06-30, full-platform probe)

Tally across 57 blueprints / 64 pages: **5 🟢 real · 36 🟡 demo · 12 🟠 empty · 4 ⚪/🔴 stub or broken**. All 64 frontend pages render.

- **Genuinely real:** FRED market rates · MSRB/EMMA corpus · AI providers (OpenRouter + World Labs, keys set on Railway, verified 2026-06-27) · health/infra.
- **Simulations presented as live:** `fund` and `blockchain` modules.
- **Broken:** `/api/lenders-direct` returns a live 500.
- **Deal data:** `/api/deals` returns 4 hardcoded in-memory deals — NOT the Supabase-seeded ones (the schema split below). The "Active Deals" screen reads `/api/deal-flow/seed-deals` (hardcoded `emma_seed_data.py`).

## Database

- Canonical project `tquotedgiapmivitjipn` runs the **005** `deals` schema (`deal_size`, `location_*`, jsonb) and is seeded with **5 real deals** (`source_channel='migrated_demo'`) — verified 2026-06-27.
- Deployed `backend/routes/deals.py` still speaks the old **001** schema (`bond_face`, `state`, `market`) → DB reads fail silently → hardcoded fallback. **Fix staged locally + verified, not yet merged** (the deals-schema reconcile workstream).
- RLS is wide open (`deals_open USING(true)`) — closing it is part of auth hardening. `asserted` (last checked 2026-06-27).
- Non-canonical Supabase projects exist (Kevin's `slypsbwnwinxmtoddogr` signal-work history; Sean's `gvwstkarllsfykdvblac` dead weight) — consolidate onto the canonical, see ADR-0004.

## Known gaps that will bite

1. **`/api/deals` (and likely sibling routes) respond WITHOUT auth** on the canonical backend → unauthenticated exposure of deal data (issuers, $-amounts, notes). Legacy V2 backend correctly 401s. Verified 2026-06-24/30.
2. **001/005 schema split** (above) — until the staged fix merges, everything deal-shaped is demo data.
3. **CORS is `origins: "*"`** — tighten before real users.
4. Auth is JWT but not Supabase GoTrue end-to-end; MFA/RBAC not yet built.
5. Two domains and three Supabase projects pending consolidation decisions (Sean + Kevin).

## Active work

Work tracking moves to **GitHub Issues on this repo** (per `AGENTS.md`). Current workstreams, in priority order:

1. **Deals-schema reconcile** — staged fix for `routes/deals.py` + repoint `DealsPage.tsx` to `/api/deals`; merging it makes the platform stop showing demo deals.
2. **Auth hardening** — close the `/api/deals` exposure, then Supabase Auth + RBAC, RLS ownership policies, CORS allowlist.
3. **Data-model unification** — three disconnected layers (Python models, SQL schema, demo registry) → one Supabase-backed system; 15-stage lifecycle canonical.
4. **Deal intake (Stages 0–3)** — Jacaranda Trace pilot: CRUD, stage progression, readiness scoring, sizing formulas.
5. **Port signal intelligence from V2** — EDGAR connector, correlation engine, signal_service (mine V2, don't build on it).

---

## Version history (compact — do not re-litigate)

| Era | What happened |
|---|---|
| V1 | Full backend logic on wrong frontend design. Deleted. |
| V2 (`NEST-ADVISORS-V2`) | Correct look, demo-stub modules; EagleEye signal intelligence lives here — port it, don't extend it. |
| V3/V4 split repos | Superseded. |
| **NEST-PLATFORM (current)** | Canonical monorepo since 2026-06-18 (ADR-0003): `frontend/` Next.js 14 + `backend/` Flask, 15-stage deal lifecycle, dual-tranche bonds. `frontend-v2/` (Vite) is legacy — do not build on. |

The old root `STATE.md` (dated 2026-06-09, pre-monorepo-adoption) described `frontend-v2/` as active — superseded by this document.
