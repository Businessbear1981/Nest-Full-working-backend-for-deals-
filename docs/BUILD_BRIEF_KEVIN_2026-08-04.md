# Build Brief — Kevin

**04 August 2026 · NEST Platform · from Sean Gilmore**

Source: `docs/filecabinet/2026-08-04.md`. Every number below comes from a
committed engine or a git commit, not from recollection. Where something is
unverified it says so.

---

## What this is

Eleven commits landed on `Gilmore_Active_Updates_Fixes` in one day. Three of
them are new engines, three are generators that produce documentation from
code, and one of them audits the platform itself and produced a result you
need to see before you write another line.

Your branch is `kevin/wiring-phase-1`, cut from `29d3612`.

---

## The finding that matters

We ran the platform's own success model against the platform.

| | |
|---|---|
| Backend modules | **156** |
| Reachable from a registered route | 126 (81%) |
| **Unreachable — not in the product** | **30** |
| Route modules the product actually calls | **27 of 58** |
| Frontend components | 208 |

**Reachable** means: starting from the blueprints actually registered on the
app, walk the import graph. If nothing on that walk imports a module, no
frontend work will ever reach it — nothing on the server can call it either.
Thirty modules fail that test, including eleven of twenty-four agents. They
are not unwired. They are absent from the product.

And two routes are worse than unwired. `routes/phoenix.py` exposes fifteen
endpoints across 158 lines and imports no service, no engine, no agent. Every
value it returns is a literal typed into the route file. Sitting next to it is
a 536-line `phoenix_engine.py` that nothing reaches. `routes/treasury.py` has
the same shape across twelve endpoints.

That is the case I want to make plainly, because it is about how work gets
checked rather than about anyone's effort: **end-to-end wiring is not the
finish line.** A hollow route passes every dashboard check we have. It
responds, it returns valid JSON, it looks green. It computes nothing. We had
two of them and did not know.

I'll hold myself to the same standard. My first pass at this audit counted only
`@bp.route()` and missed `@bp.get` and `@bp.post`, so it marked twenty-nine
modules for deletion — including `auth` and `preflight`. After the fix:
deletions 29 → 0, wired 12 → 27. I was confidently wrong until the check was
written down and run. That is the whole argument.

---

## Your worklist, in order

### 1. Fix first — HOLLOW (2 modules)

Connected and empty. These need a body, not a connection.

| Module | Prefix | Endpoints | Tested |
|---|---|---|---|
| `phoenix` | `/api/phoenix` | 15 | no |
| `treasury` | `/api/treasury` | 12 | no |

For `phoenix`, `phoenix_engine.py` already exists and is unreachable. The fix
is likely to import it rather than to write new logic.

### 2. Then — WIRE (11 modules)

Both halves exist. A backend with endpoints, and a component that never calls
it. Cheapest real progress in the codebase.

| Module | Prefix | Endpoints |
|---|---|---|
| `intelligence` | — | 56 |
| `marketing` | `/api/marketing` | 16 |
| `roots` | — | 9 |
| `client_portal` | `/api/client` | 7 |
| `convergence` | `/api/convergence` | 6 |
| `preflight` | `/api/preflight` | 6 |
| `study` | — | 6 |
| `surety` | `/api/surety` | 5 |
| `deal_outcomes` | `/api/deal-outcomes` | 4 |
| `intake_brainstorm` | — | 4 |
| `covenants` | `/api/covenants` | 3 |

Start with `preflight` — it is the structural-viability gate and the deal flow
depends on it. None of the eleven has tests.

### 3. Then — BUILD_FRONTEND (15 modules)

Reachable, endpoints live, no screen was ever built. Highest-value first:
`engines_api` (27 endpoints), `v2_compat` (23, tested), `gate_fees` (21,
tested), then `due_diligence`, `bd`, `documents`, `ma`, `nightvision`,
`scanner`, `blockchain`, `doc_ingestion`, `cns_signals`, `lenders_api`, `cns`,
`investors`.

`gate_fees` is the one I'd take first — it is tested, it is the fee engine, and
`ClientDepositPlatform.tsx` needs to be pointed at `/api/gate-fees/client-view`.

### 4. Decide — UNREACHABLE (30 modules)

Route it or delete it, one at a time, with the decision written down. Carrying
these advertises capability the platform does not have.

Services: `activity`, `atticus_service`, `autonomous_scanner`, `billing_engine`,
`convergence_engine`, `credit_engine`, `deals`, `documents`, `fund_engine`,
`logging_service`, `market_benchmarks`, `migrations`, `phoenix_engine`,
`preference_engine`, `proforma_spreader`, `ramp_connector`, `treasury_engine`.

Agents: `apex_agent`, `aria`, `bridge_agent`, `chain_agent`, `maxwell`,
`prometheus`, `quantum`, `refunding_agent`, `sentinel`, `sterling`,
`vector_agent`.

Engines: `placement`.

(`platform_readiness` also reports unreachable and should stay that way — it is
a build-time tool, not a product surface.)

### 5. Two that are not on any list because they are live problems

- **`routes/hawkeye.py:26`** ships six fabricated institutional buyers carrying
  `"relationship": "existing"`. That is a misrepresentation to a client, in
  production. Delete it.
- **`/api/deals` is unauthenticated.** Four tests have been failing since June.

---

## What shipped today, and why you'd care

**`backend/services/platform_readiness.py`** — the audit above, as an engine.
Weights: reachable 0.30, wired 0.25, substance 0.25, surface 0.05, tests 0.15;
ceiling 0.95. Weakest-link blended with average preparedness, the same method
`success_predictor` uses on deals. Run it:

```bash
python scripts/wiring_audit.py
python scripts/wiring_audit.py --verdict UNREACHABLE
python scripts/build_mapping.py        # regenerates docs/NEST_MODULE_MAP.md
```

Reachability, endpoint counts, registration and wiring are read from source and
are exact. Component matching is by name overlap, produces false pairs, and
never drives a verdict on its own.

**`backend/services/pom_engine.py`** — offering-document hours derived from 23
catalogued sections under a declared drafting model, rather than the old
asserted `196`. Bond counsel drafts the reserved sections; that is enforced in
code as `COUNSEL_RESERVED`, not left to prose.

**`backend/services/document_package.py`** — 60 documents across ten silos,
each joined to a fee gate, with upstream documents allowed to satisfy
downstream inputs and a `NOT_APPLICABLE` gate state. This is the locked design
behind `/nest-docs`.

**`backend/services/gate_fee_engine.py`** — gate hours now scale with par
(45% fixed, remainder on the square root of par against a $100M reference),
and the engine flags a series priced below cost instead of silently producing
a nonsense effective hourly.

**Generators** — `build_dictionary.py` and `build_mapping.py` produce
Operations Manual Volumes 3 and 4B from the Bible and from the code. Both
outputs carry a do-not-hand-edit banner because the code is the source of
truth. `nest_brand.py` wraps any markdown in NEST brand for client delivery.

**Skills** (`.claude/skills/`) — `nest-docs`, `nest-deal-run`,
`nest-house-style`, `nest-truth-shield`, `nest-filecabinet`. These are the
repeatable procedures written down so they run the same way twice.

---

## Ground rules on this branch

- Never push to `main`. PRs only. Never force-push.
- A route that returns a literal is not done. If it imports nothing, it
  computes nothing.
- New thresholds carry provenance: `HAND_SET`, `RULE_BASED`, or
  `MARKET_DERIVED`. We currently have zero `MARKET_DERIVED`, which is itself
  worth knowing.
- If you delete an unreachable module, say so in the commit message and in the
  day's file cabinet entry. If you keep one, write down why.
- Regenerate `docs/NEST_MODULE_MAP.md` before you open the PR. The number that
  matters is 30 → lower and 27/58 → higher.

---

## What I need back

1. A decision on each of the 30 unreachable modules — route or delete.
2. The two hollow routes given bodies.
3. `hawkeye.py:26` and `/api/deals` auth, ahead of everything else.
4. Your read on whether the WIRE list is really eleven, or whether some of
   those components are false name matches. The audit says component matching
   is the one thing it cannot do exactly, and you know that code better.
