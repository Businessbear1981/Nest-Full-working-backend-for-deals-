# ADR-0004: Canonical Supabase is `tquotedgiapmivitjipn` (NEST_ADVISORS)

**Status:** Accepted · established 2026-06-27, recorded in-repo 2026-07-14
**Deciders:** Kevin Olson (CTO); consolidation coordination with Sean Gilmore pending

## Context

Three Supabase projects were in play: Kevin's `slypsbwnwinxmtoddogr` (`nest-advisors` — 20 tables, EagleEye signal work, 3 demo deals), Sean's `gvwstkarllsfykdvblac` (old 001 schema, mostly-empty rows loaded by mistake), and Sean's `tquotedgiapmivitjipn` (NEST_ADVISORS). The live Railway backend's `SUPABASE_URL` points at `tquotedgiapmivitjipn` (verified 2026-06-27); it runs the new 005 `deals` schema and is seeded with 5 real deals.

## Decision

`tquotedgiapmivitjipn` is the canonical database. Everything consolidates onto it. The other two projects are non-canonical: `slypsbwnwinxmtoddogr` holds signal-work history to be migrated/ported; `gvwstkarllsfykdvblac` is dead weight to be retired.

## Why

- It is what the production backend actually reads — ground truth already voted.
- It carries the current 005 schema; pointing code elsewhere would resurrect the 001/005 split that caused the "everything is demo" failure.

## Consequences

- Deal intake and all new persistence wire to `tquotedgiapmivitjipn`.
- RLS on the canonical project is still wide open (`USING(true)`) — closing it is auth-hardening scope.
- Kevin's Supabase access cannot see Sean's org — canonical-DB work needs Sean-side access or coordination.
- Never reintroduce 001 column names (`bond_face`, `state`, `market`); the canonical schema is 005 (`deal_size`, `location_*`, jsonb).
