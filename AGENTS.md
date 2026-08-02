# NEST Platform — Agent Charter

> This file is the portable core for any agent or human working in this repo.
> Read it first, then read `docs/STATE.md` for what is actually built and live.

## What this is

NEST is an AI-augmented municipal/CCRC bond structuring and deal-intelligence platform (Arden Edge Capital × Soparrow Capital). Principals: Sean Gilmore (CEO, 18yr JPMorgan), Josh Edwards (Co-Founder, Soparrow Capital), Kevin Olson (Co-Founder & CTO). Two business lines — **Bond** (flagship: origination, structuring, placement, administration) and **Sparrow** (structured debt brokerage). Pilot deal: Jacaranda Trace PLOM (Series 2025, ~$231M, Florida CCRC). Domain vocabulary is canonical in [`CONTEXT.md`](CONTEXT.md) — use its terms, don't drift to synonyms.

## Architecture map

| Layer | What | Canonical production |
|---|---|---|
| Frontend | Next.js 14 App Router in `frontend/` | Vercel team `ardan-edge-capital`, project `nest-platform` → **`www.nestadvisors.tech`** |
| Backend | Flask (Gunicorn + **gevent** worker) in `backend/` | Railway → **`nest-platform-production.up.railway.app`** (`/api/health` = liveness; root `/` has no route and 404s by design) |
| Database | Supabase (Postgres + Auth) | **`tquotedgiapmivitjipn`** (NEST_ADVISORS, Sean's org) — see ADR-0004. Other Supabase projects are non-canonical. |
| AI | OpenRouter + World Labs (`OPENROUTER_API_KEY`, `WORLD_LABS_API_KEY` — set on Railway, verified 2026-06-27) | — |
| Legacy | `api.nestadvisors.ai` → old Railway service wired to `NEST-ADVISORS-V2` repo | reference-only, do not build on (ADR-0003) |

```
NEST-PLATFORM/
├── backend/            Flask — ACTIVE. agents/ services/ routes/ models/ migrations/
├── frontend/           Next.js 14 — ACTIVE (this is what Vercel builds)
├── frontend-v2/        Vite + React — LEGACY, do not build on
├── docs/
│   ├── STATE.md        current built/wired/live state (read at session start)
│   ├── adr/            architectural decision records
│   └── reference/      brand & voice, domain reference, Payload specs
├── CONTEXT.md          domain glossary (canonical vocabulary)
└── supabase/           SQL
```

Local dev ports: backend **8000**, frontend **8100** (CreditFix uses 3000/5000 — don't collide).

## Session protocol

1. **Start:** read this file, then `docs/STATE.md`, then `docs/NEST_GLOSSARY.md` (agent/engine org chart — what's real, what's a placeholder, what feeds what), then any GitHub Issue you're picking up.
2. **Work:** the Issue is the unit of scope. Verify load-bearing claims against ground truth (live endpoints, Supabase, Vercel/Railway dashboards) before high-stakes changes.
3. **Finish (write-back is the definition of done):** if the session changed project state — infra, schema, decisions, what's-wired status — update `docs/STATE.md` **in the same PR**. If the session touched an agent/engine's real behavior (fixed a bug, wired something, found a fabrication issue), update its entry in `docs/NEST_GLOSSARY.md` too. Durable choices get an ADR in `docs/adr/`. That's how two machines converge instead of drifting.

## Git SOP

- All work on short-lived branches named `{person}/{slug}` (e.g. `ko/deal-intake`, `sean/letters`); merge via PR; **never direct-to-main, never force-push**.
- Commit at natural checkpoints with conventional messages (`feat:`, `fix:`, `docs:`, `chore:`).
- Push the branch and open a PR at session end.
- If a session changed project state, update `docs/STATE.md` in the same PR.
- Work tracking: GitHub Issues + PRs on `Businessbear1981/NEST-PLATFORM`. Reference issues from PRs so they auto-link.

## Guardrails (hard rules)

- **Never push to main.** PRs only.
- **Never touch production environment** — Railway/Vercel env vars, DNS, deploy settings, production database DDL — without explicit confirmation from a principal.
- **Never commit secrets.** Keys live in env vars; the repo carries `.env.example` only. If you see a committed secret, flag it immediately.
- **Never reintroduce the 001 `deals` schema column names** (`bond_face`, `state`, `market`). The canonical DB runs the 005 schema (`deal_size`, `location_*`, jsonb) — see gotchas.
- **Never build on `frontend-v2/`** or the V2/V3/V4 repos — reference-only (ADR-0003).
- **Deal data is sensitive** (issuers, dollar amounts, notes). Never widen an endpoint's exposure; auth hardening is in progress.

## Known gotchas

- **Schema split (the "everything is demo" root cause):** canonical Supabase runs the new **005** `deals` schema, but deployed `backend/routes/deals.py` spoke the old **001** schema — DB reads fail silently and the app falls back to hardcoded deals. Fix staged (see `docs/STATE.md`).
- **`/api/deals` currently responds WITHOUT auth** on the canonical backend → unauthenticated deal-data exposure. Real, open security gap; legacy V2 backend correctly 401s.
- **"Backend 404" is a false alarm:** both backends 404 only on root `/` (no route). Health-check `/api/health`, never `/`.
- **Three disconnected deal sources:** `/api/deals` (route `_deals`), `/api/deal-flow/seed-deals` (hardcoded `emma_seed_data.py` — what "Active Deals" shows), and the Supabase `deals` table. Unification pending.
- **CORS is `origins: "*"`** — tighten before real users.
- Backend uses the **gevent** Gunicorn worker, not `sync` — check library compatibility.

## Conventions

- File naming: `backend/agents/[name].py` · `backend/services/[name].py` · `backend/routes/[noun].py` (plural) · `backend/models/[noun].py` (singular) · `frontend/components/[Domain]/`.
- API responses always: `{"success": bool, "data": {}, "error": None|str, "timestamp": iso8601}`.
- Brand, voice, agent fleet, credit benchmarks, capital structure: [`docs/reference/brand-and-voice.md`](docs/reference/brand-and-voice.md) — apply on every UI surface and AI output.

## Where things live

| What | Where |
|---|---|
| Current built/wired/live state | `docs/STATE.md` |
| Agent/engine/product org chart — codenames, what feeds what, INTENDED vs ACTUAL vs FIX-NEEDED | `docs/NEST_GLOSSARY.md` |
| Durable decisions (ADRs) | `docs/adr/` |
| Work tracking | GitHub Issues + PRs on `Businessbear1981/NEST-PLATFORM` |
| Domain glossary | `CONTEXT.md` |
| Brand / voice / benchmarks | `docs/reference/brand-and-voice.md` |
| Operating framework, bible, Payload specs | `docs/` and `docs/reference/` |
