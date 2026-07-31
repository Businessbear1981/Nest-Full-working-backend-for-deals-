# ADR-0003: NEST-PLATFORM is the canonical repo; V2 and split repos are reference-only

**Status:** Accepted · decided 2026-06-18, recorded in-repo 2026-07-14
**Deciders:** Kevin Olson (CTO), with Sean Gilmore (production `.tech` frontend already deployed from this repo)

## Context

Multiple repos existed: `Businessbear1981/NEST-ADVISORS-V2` (Vite `frontend-v2` + Flask — the EagleEye era), later `V3`/`V4` split repos, and `Businessbear1981/NEST-PLATFORM` (single monorepo: Next.js 14 `frontend/` + Flask `backend/`, 15-stage deal lifecycle, dual-tranche bonds).

## Decision

`Businessbear1981/NEST-PLATFORM` is canonical. `NEST-ADVISORS-V2` and the V3/V4 splits are reference-only — mine them (e.g. port EagleEye signal intelligence), never build on them. Inside this repo, `frontend/` (Next.js) is the active frontend; `frontend-v2/` (Vite) is legacy.

## Why

- It is what actually serves production: `www.nestadvisors.tech` → `nest-platform-production.up.railway.app`.
- Single monorepo with the richer domain model (15-stage lifecycle) vs. the fragmented V2 era.

## Consequences

- All new work lands here; the old `api.nestadvisors.ai` Railway service (wired to V2) is legacy.
- Signal intelligence (EDGAR connector, correlation engine, signal_service) must be **ported** from V2, not extended in place.
- Issue tracking lives on this repo (older docs referencing `NEST-ADVISORS-V3` issues are superseded).
