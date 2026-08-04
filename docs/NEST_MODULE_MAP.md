# NEST Operations Manual — Volume 4, Part B
## The Module Map

> **Generated 04 August 2026** by `scripts/build_mapping.py` from `backend/services/platform_readiness.py`. Do not hand-edit — the code is the source of truth and a hand edit will be overwritten.
>
> **What this is.** Every backend module, and whether a user can actually reach it. Volume 4 Part A (`docs/NEST_GLOSSARY.md`) says what each module was *intended* to do. This says what is *true*.

## How a module is judged

The platform scores deals on whether they can reach close. This applies the same method to the platform: weakest-link blended with average preparedness, because things fail on one binding constraint rather than on the mean of their parts.

| Factor | Weight | What it asks |
|---|---|---|
| Reachable | 30% | Does a registered route import it, directly or through a chain? |
| Wired | 25% | Does anything in the product call it? |
| Substance | 25% | Does the route call real logic, or return values written in its own file? |
| Surface | 5% | Does a frontend component exist? |
| Tests | 15% | Can it be changed safely? |

**Reachability is weighted highest** because an unreachable module is absent from the product at any level of quality. Weights are `HAND_SET`. Reachability, endpoint counts, registration and wiring are read from source and are exact; component matching is by name overlap and produces false pairs, so it never drives a verdict alone.

**Reachable does not mean correct and wired does not mean working. This measures whether a path exists from a user to the code, not whether the code is right.**

## Where the platform stands

| | |
|---|---|
| Backend modules | **156** |
| Reachable from a registered route | 126 (81%) |
| **Unreachable — not in the product** | **30** |
| Route modules the product calls | **27 of 58** |
| Frontend components | 208 |
| API prefixes actually called | 42 |

### By layer

| Layer | Verdicts |
|---|---|
| `routes` | WIRED **25** · BUILD_FRONTEND **15** · WIRE **11** · REBUILD **5** · HOLLOW **2** |
| `services` | REACHABLE_UNUSED **46** · UNREACHABLE **18** |
| `engines` | REACHABLE_UNUSED **9** · UNREACHABLE **1** |
| `agents` | REACHABLE_UNUSED **13** · UNREACHABLE **11** |

## What each verdict means, and what to do about it

**`WIRED` — In the product** · 25 modules

A screen calls it and it calls real logic. Nothing to do.

**`HOLLOW` — Connected but empty** · 2 modules

Wired end to end and computes nothing — imports no service, engine or agent, so it returns values written in the route file itself. Needs a body, not a connection.

**`WIRE` — Both halves exist** · 11 modules

A backend with endpoints and a frontend component that does not call it. The cheapest real progress available.

**`BUILD_FRONTEND` — Backend with no surface** · 15 modules

Endpoints exist and are reachable. No screen was ever built.

**`REACHABLE_UNUSED` — Alive but idle** · 68 modules

A registered route imports it, but that route has no frontend. Wiring the route brings this with it.

**`UNREACHABLE` — Not in the product** · 30 modules

No registered route imports it, directly or through any chain. No amount of frontend work reaches it because nothing on the server can call it either. Route it or delete it.

**`REBUILD` — Too thin** · 5 modules

Registered but exposing almost nothing.

## Redundancy

One API prefix served by more than one route module. Each is a collision to resolve, not a feature.

| Prefix | Route modules |
|---|---|
| `/api` | `v2_compat`, `health` |
| `/api/cns` | `cns`, `cns_signals` |

## Fix first — connected but empty

These read as working on any dashboard and deliver nothing. The most flattering failure mode the platform has.

| Module | Layer | Prefix | Endpoints | Tested |
|---|---|---|---|---|
| `phoenix` | routes | `/api/phoenix` | 15 | no |
| `treasury` | routes | `/api/treasury` | 12 | no |

## Then — both halves exist, connect them

A backend with endpoints and a component that does not call it. Cheapest real progress in the codebase.

| Module | Layer | Prefix | Endpoints | Tested |
|---|---|---|---|---|
| `intelligence` | routes | — | 56 | no |
| `marketing` | routes | `/api/marketing` | 16 | no |
| `roots` | routes | — | 9 | no |
| `client_portal` | routes | `/api/client` | 7 | no |
| `convergence` | routes | `/api/convergence` | 6 | no |
| `preflight` | routes | `/api/preflight` | 6 | no |
| `study` | routes | — | 6 | no |
| `surety` | routes | `/api/surety` | 5 | no |
| `deal_outcomes` | routes | `/api/deal-outcomes` | 4 | no |
| `intake_brainstorm` | routes | — | 4 | no |
| `covenants` | routes | `/api/covenants` | 3 | no |

## Then — backends that earned a surface

Reachable, endpoints live, no screen was ever built.

| Module | Layer | Prefix | Endpoints | Tested |
|---|---|---|---|---|
| `engines_api` | routes | `/api/engines` | 27 | no |
| `v2_compat` | routes | `/api` | 23 | yes |
| `gate_fees` | routes | `/api/gate-fees` | 21 | yes |
| `due_diligence` | routes | `/api/dd` | 7 | no |
| `bd` | routes | `/api/bd` | 6 | no |
| `documents` | routes | `/api/docs` | 6 | no |
| `ma` | routes | `/api/ma` | 6 | no |
| `nightvision` | routes | `/api/nightvision` | 6 | no |
| `scanner` | routes | `/api/scanner` | 6 | no |
| `blockchain` | routes | `/api/blockchain` | 5 | no |
| `doc_ingestion` | routes | `/api/docs/ingest` | 5 | no |
| `cns_signals` | routes | `/api/cns` | 4 | no |
| `lenders_api` | routes | `/api/lenders-direct` | 4 | no |
| `cns` | routes | `/api/cns` | 3 | no |
| `investors` | routes | `/api/investors` | 3 | no |

## Decide — route it or delete it

No registered route imports these. Carrying them reads as capability the platform does not have.

| Module | Layer | Prefix | Endpoints | Tested |
|---|---|---|---|---|
| `platform_readiness` | services | — | 1 | yes |
| `activity` | services | — | 0 | no |
| `apex_agent` | agents | — | 0 | no |
| `aria` | agents | — | 0 | no |
| `atticus_service` | services | — | 0 | no |
| `autonomous_scanner` | services | — | 0 | yes |
| `billing_engine` | services | — | 0 | no |
| `bridge_agent` | agents | — | 0 | no |
| `chain_agent` | agents | — | 0 | no |
| `convergence_engine` | services | — | 0 | yes |
| `credit_engine` | services | — | 0 | yes |
| `deals` | services | — | 0 | no |
| `documents` | services | — | 0 | no |
| `fund_engine` | services | — | 0 | no |
| `logging_service` | services | — | 0 | no |
| `market_benchmarks` | services | — | 0 | no |
| `maxwell` | agents | — | 0 | no |
| `migrations` | services | — | 0 | no |
| `phoenix_engine` | services | — | 0 | yes |
| `placement` | engines | — | 0 | no |
| `preference_engine` | services | — | 0 | no |
| `proforma_spreader` | services | — | 0 | no |
| `prometheus` | agents | — | 0 | no |
| `quantum` | agents | — | 0 | no |
| `ramp_connector` | services | — | 0 | no |
| `refunding_agent` | agents | — | 0 | no |
| `sentinel` | agents | — | 0 | yes |
| `sterling` | agents | — | 0 | no |
| `treasury_engine` | services | — | 0 | no |
| `vector_agent` | agents | — | 0 | no |

## Full map

### `agents`

| Module | Prefix | Endpoints | Reachable | Wired | Tested | P | Verdict |
|---|---|---|---|---|---|---|---|
| `surety_scout` | — | 0 | yes | no | yes | 0.18 | `REACHABLE_UNUSED` |
| `merlin` | — | 0 | yes | no | yes | 0.18 | `REACHABLE_UNUSED` |
| `bernard` | — | 0 | yes | no | no | 0.17 | `REACHABLE_UNUSED` |
| `bond_optimizer` | — | 0 | yes | no | no | 0.17 | `REACHABLE_UNUSED` |
| `covenant_monitor_agent` | — | 0 | yes | no | no | 0.17 | `REACHABLE_UNUSED` |
| `credit_memo_agent` | — | 0 | yes | no | no | 0.17 | `REACHABLE_UNUSED` |
| `desk_registry` | — | 0 | yes | no | no | 0.17 | `REACHABLE_UNUSED` |
| `lender_scout` | — | 0 | yes | no | no | 0.17 | `REACHABLE_UNUSED` |
| `moodys_mirror` | — | 0 | yes | no | no | 0.17 | `REACHABLE_UNUSED` |
| `_claude` | — | 0 | yes | no | no | 0.16 | `REACHABLE_UNUSED` |
| `auditor` | — | 0 | yes | no | no | 0.16 | `REACHABLE_UNUSED` |
| `morgan` | — | 0 | yes | no | no | 0.16 | `REACHABLE_UNUSED` |
| `sp_mirror` | — | 0 | yes | no | no | 0.16 | `REACHABLE_UNUSED` |
| `sentinel` | — | 0 | **NO** | no | yes | 0.13 | `UNREACHABLE` |
| `apex_agent` | — | 0 | **NO** | no | no | 0.12 | `UNREACHABLE` |
| `bridge_agent` | — | 0 | **NO** | no | no | 0.12 | `UNREACHABLE` |
| `chain_agent` | — | 0 | **NO** | no | no | 0.12 | `UNREACHABLE` |
| `refunding_agent` | — | 0 | **NO** | no | no | 0.12 | `UNREACHABLE` |
| `vector_agent` | — | 0 | **NO** | no | no | 0.12 | `UNREACHABLE` |
| `aria` | — | 0 | **NO** | no | no | 0.11 | `UNREACHABLE` |
| `maxwell` | — | 0 | **NO** | no | no | 0.11 | `UNREACHABLE` |
| `prometheus` | — | 0 | **NO** | no | no | 0.11 | `UNREACHABLE` |
| `quantum` | — | 0 | **NO** | no | no | 0.11 | `UNREACHABLE` |
| `sterling` | — | 0 | **NO** | no | no | 0.11 | `UNREACHABLE` |
### `engines`

| Module | Prefix | Endpoints | Reachable | Wired | Tested | P | Verdict |
|---|---|---|---|---|---|---|---|
| `maxwell_engine` | — | 0 | yes | no | yes | 0.18 | `REACHABLE_UNUSED` |
| `architect` | — | 0 | yes | no | yes | 0.18 | `REACHABLE_UNUSED` |
| `audit_package` | — | 0 | yes | no | no | 0.17 | `REACHABLE_UNUSED` |
| `bridge_surveillance` | — | 0 | yes | no | no | 0.17 | `REACHABLE_UNUSED` |
| `insurance` | — | 0 | yes | no | no | 0.17 | `REACHABLE_UNUSED` |
| `intake` | — | 0 | yes | no | no | 0.17 | `REACHABLE_UNUSED` |
| `modeling` | — | 0 | yes | no | no | 0.17 | `REACHABLE_UNUSED` |
| `sentinel_engine` | — | 0 | yes | no | no | 0.17 | `REACHABLE_UNUSED` |
| `pricing` | — | 0 | yes | no | no | 0.16 | `REACHABLE_UNUSED` |
| `placement` | — | 0 | **NO** | no | no | 0.12 | `UNREACHABLE` |
### `routes`

| Module | Prefix | Endpoints | Reachable | Wired | Tested | P | Verdict |
|---|---|---|---|---|---|---|---|
| `gate_fees` | `/api/gate-fees` | 21 | yes | no | yes | 0.18 | `BUILD_FRONTEND` |
| `v2_compat` | `/api` | 23 | yes | no | yes | 0.18 | `BUILD_FRONTEND` |
| `bd` | `/api/bd` | 6 | yes | no | no | 0.16 | `BUILD_FRONTEND` |
| `blockchain` | `/api/blockchain` | 5 | yes | no | no | 0.16 | `BUILD_FRONTEND` |
| `doc_ingestion` | `/api/docs/ingest` | 5 | yes | no | no | 0.16 | `BUILD_FRONTEND` |
| `documents` | `/api/docs` | 6 | yes | no | no | 0.16 | `BUILD_FRONTEND` |
| `due_diligence` | `/api/dd` | 7 | yes | no | no | 0.16 | `BUILD_FRONTEND` |
| `engines_api` | `/api/engines` | 27 | yes | no | no | 0.16 | `BUILD_FRONTEND` |
| `investors` | `/api/investors` | 3 | yes | no | no | 0.16 | `BUILD_FRONTEND` |
| `lenders_api` | `/api/lenders-direct` | 4 | yes | no | no | 0.16 | `BUILD_FRONTEND` |
| `ma` | `/api/ma` | 6 | yes | no | no | 0.16 | `BUILD_FRONTEND` |
| `nightvision` | `/api/nightvision` | 6 | yes | no | no | 0.16 | `BUILD_FRONTEND` |
| `cns` | `/api/cns` | 3 | yes | no | no | 0.12 | `BUILD_FRONTEND` |
| `cns_signals` | `/api/cns` | 4 | yes | no | no | 0.12 | `BUILD_FRONTEND` |
| `scanner` | `/api/scanner` | 6 | yes | no | no | 0.12 | `BUILD_FRONTEND` |
| `phoenix` | `/api/phoenix` | 15 | yes | yes | no | 0.17 | `HOLLOW` |
| `treasury` | `/api/treasury` | 12 | yes | yes | no | 0.17 | `HOLLOW` |
| `activity` | `/api/activity` | 1 | yes | no | no | 0.16 | `REBUILD` |
| `marketplace` | `/api/marketplace` | 1 | yes | no | no | 0.16 | `REBUILD` |
| `perm` | `/api/perm` | 2 | yes | no | no | 0.16 | `REBUILD` |
| `webhooks` | `/api/webhooks` | 2 | yes | no | no | 0.16 | `REBUILD` |
| `health` | `/api` | 2 | yes | no | yes | 0.15 | `REBUILD` |
| `client_portal` | `/api/client` | 7 | yes | no | no | 0.17 | `WIRE` |
| `covenants` | `/api/covenants` | 3 | yes | no | no | 0.17 | `WIRE` |
| `deal_outcomes` | `/api/deal-outcomes` | 4 | yes | no | no | 0.17 | `WIRE` |
| `intelligence` | — | 56 | yes | no | no | 0.17 | `WIRE` |
| `marketing` | `/api/marketing` | 16 | yes | no | no | 0.17 | `WIRE` |
| `preflight` | `/api/preflight` | 6 | yes | no | no | 0.17 | `WIRE` |
| `roots` | — | 9 | yes | no | no | 0.17 | `WIRE` |
| `study` | — | 6 | yes | no | no | 0.17 | `WIRE` |
| `surety` | `/api/surety` | 5 | yes | no | no | 0.17 | `WIRE` |
| `convergence` | `/api/convergence` | 6 | yes | no | no | 0.13 | `WIRE` |
| `intake_brainstorm` | — | 4 | yes | no | no | 0.13 | `WIRE` |
| `construction` | `/api/construction` | 4 | yes | yes | yes | 0.95 | `WIRED` |
| `deals` | `/api/deals` | 14 | yes | yes | yes | 0.95 | `WIRED` |
| `auth` | `/api/auth` | 4 | yes | yes | yes | 0.21 | `WIRED` |
| `eagleeye` | `/api/eagleeye` | 16 | yes | yes | yes | 0.21 | `WIRED` |
| `bond_structuring` | `/api/bond-structuring` | 4 | yes | yes | no | 0.20 | `WIRED` |
| `bond_tools` | `/api/bond-tools` | 13 | yes | yes | no | 0.20 | `WIRED` |
| `bond_workflow` | `/api/bond-workflow` | 13 | yes | yes | no | 0.20 | `WIRED` |
| `deal_flow` | `/api/deal-flow` | 6 | yes | yes | no | 0.20 | `WIRED` |
| `hawkeye` | `/api/hawkeye` | 9 | yes | yes | no | 0.20 | `WIRED` |
| `intelligence_engine_api` | `/api/intel` | 11 | yes | yes | no | 0.20 | `WIRED` |
| `market` | `/api/market` | 6 | yes | yes | no | 0.20 | `WIRED` |
| `rating_esg` | `/api/rating-esg` | 8 | yes | yes | no | 0.20 | `WIRED` |
| `risk` | `/api/risk` | 3 | yes | yes | no | 0.20 | `WIRED` |
| `surveillance` | `/api/surveillance` | 2 | yes | yes | no | 0.20 | `WIRED` |
| `workflow` | `/api/workflow` | 7 | yes | yes | no | 0.20 | `WIRED` |
| `agents_api` | `/api/agents` | 3 | yes | yes | no | 0.19 | `WIRED` |
| `counterparties` | `/api/counterparties` | 3 | yes | yes | no | 0.19 | `WIRED` |
| `desks` | `/api/desks` | 10 | yes | yes | no | 0.19 | `WIRED` |
| `emma` | `/api/emma` | 9 | yes | yes | no | 0.19 | `WIRED` |
| `fund` | `/api/fund` | 8 | yes | yes | no | 0.19 | `WIRED` |
| `mirror_agents` | `/api/rating` | 5 | yes | yes | no | 0.19 | `WIRED` |
| `napkin` | `/api/napkin` | 4 | yes | yes | no | 0.19 | `WIRED` |
| `nisle` | `/api/nisle` | 11 | yes | yes | no | 0.19 | `WIRED` |
| `powerstrip` | `/api/powerstrip` | 7 | yes | yes | no | 0.19 | `WIRED` |
| `signals` | `/api/signals` | 6 | yes | yes | no | 0.19 | `WIRED` |
### `services`

| Module | Prefix | Endpoints | Reachable | Wired | Tested | P | Verdict |
|---|---|---|---|---|---|---|---|
| `bond_type_engine` | — | 0 | yes | no | yes | 0.18 | `REACHABLE_UNUSED` |
| `compliance_engine` | — | 0 | yes | no | yes | 0.18 | `REACHABLE_UNUSED` |
| `counterparty_db` | — | 0 | yes | no | yes | 0.18 | `REACHABLE_UNUSED` |
| `document_package` | — | 0 | yes | no | yes | 0.18 | `REACHABLE_UNUSED` |
| `emma_engine` | — | 0 | yes | no | yes | 0.18 | `REACHABLE_UNUSED` |
| `engagement_economics` | — | 0 | yes | no | yes | 0.18 | `REACHABLE_UNUSED` |
| `gate_fee_engine` | — | 0 | yes | no | yes | 0.18 | `REACHABLE_UNUSED` |
| `intelligence_engine` | — | 0 | yes | no | yes | 0.18 | `REACHABLE_UNUSED` |
| `ma_bond_engine` | — | 0 | yes | no | yes | 0.18 | `REACHABLE_UNUSED` |
| `phase_bond_engine` | — | 0 | yes | no | yes | 0.18 | `REACHABLE_UNUSED` |
| `pom_engine` | — | 0 | yes | no | yes | 0.18 | `REACHABLE_UNUSED` |
| `preflight` | — | 0 | yes | no | yes | 0.18 | `REACHABLE_UNUSED` |
| `rating_benchmarks` | — | 0 | yes | no | yes | 0.18 | `REACHABLE_UNUSED` |
| `readiness_checklist` | — | 0 | yes | no | yes | 0.18 | `REACHABLE_UNUSED` |
| `signal_engine` | — | 0 | yes | no | yes | 0.18 | `REACHABLE_UNUSED` |
| `eagleeye_scanner` | — | 0 | yes | no | yes | 0.18 | `REACHABLE_UNUSED` |
| `emma_seed_data` | — | 0 | yes | no | yes | 0.18 | `REACHABLE_UNUSED` |
| `stairway` | — | 0 | yes | no | yes | 0.18 | `REACHABLE_UNUSED` |
| `bd_engine` | — | 0 | yes | no | no | 0.17 | `REACHABLE_UNUSED` |
| `bond_grader` | — | 0 | yes | no | no | 0.17 | `REACHABLE_UNUSED` |
| `bond_intelligence` | — | 0 | yes | no | no | 0.17 | `REACHABLE_UNUSED` |
| `bridge_fund` | — | 0 | yes | no | no | 0.17 | `REACHABLE_UNUSED` |
| `client_portal` | — | 0 | yes | no | no | 0.17 | `REACHABLE_UNUSED` |
| `deal_flow` | — | 0 | yes | no | no | 0.17 | `REACHABLE_UNUSED` |
| `deal_preflight_flow` | — | 0 | yes | no | no | 0.17 | `REACHABLE_UNUSED` |
| `forensic_audit` | — | 0 | yes | no | no | 0.17 | `REACHABLE_UNUSED` |
| `napkin_engine` | — | 0 | yes | no | no | 0.17 | `REACHABLE_UNUSED` |
| `nisle_engine` | — | 0 | yes | no | no | 0.17 | `REACHABLE_UNUSED` |
| `preflight_interview` | — | 0 | yes | no | no | 0.17 | `REACHABLE_UNUSED` |
| `project_monitor` | — | 0 | yes | no | no | 0.17 | `REACHABLE_UNUSED` |
| `roots_service` | — | 0 | yes | no | no | 0.17 | `REACHABLE_UNUSED` |
| `self_learning_engine` | — | 0 | yes | no | no | 0.17 | `REACHABLE_UNUSED` |
| `workflow_engine` | — | 0 | yes | no | no | 0.17 | `REACHABLE_UNUSED` |
| `ai_router` | — | 0 | yes | no | no | 0.16 | `REACHABLE_UNUSED` |
| `auth` | — | 2 | yes | no | no | 0.16 | `REACHABLE_UNUSED` |
| `core` | — | 0 | yes | no | no | 0.16 | `REACHABLE_UNUSED` |
| `dapt_models` | — | 0 | yes | no | no | 0.16 | `REACHABLE_UNUSED` |
| `data_connectors` | — | 0 | yes | no | no | 0.16 | `REACHABLE_UNUSED` |
| `database` | — | 0 | yes | no | no | 0.16 | `REACHABLE_UNUSED` |
| `doc_ingestion` | — | 0 | yes | no | no | 0.16 | `REACHABLE_UNUSED` |
| `due_diligence` | — | 0 | yes | no | no | 0.16 | `REACHABLE_UNUSED` |
| `ingestion` | — | 0 | yes | no | no | 0.16 | `REACHABLE_UNUSED` |
| `jimmy_lee` | — | 0 | yes | no | no | 0.16 | `REACHABLE_UNUSED` |
| `licensing` | — | 0 | yes | no | no | 0.16 | `REACHABLE_UNUSED` |
| `sendgrid_service` | — | 0 | yes | no | no | 0.16 | `REACHABLE_UNUSED` |
| `success_predictor` | — | 0 | yes | no | no | 0.16 | `REACHABLE_UNUSED` |
| `convergence_engine` | — | 0 | **NO** | no | yes | 0.14 | `UNREACHABLE` |
| `credit_engine` | — | 0 | **NO** | no | yes | 0.14 | `UNREACHABLE` |
| `phoenix_engine` | — | 0 | **NO** | no | yes | 0.14 | `UNREACHABLE` |
| `platform_readiness` | — | 1 | **NO** | no | yes | 0.14 | `UNREACHABLE` |
| `autonomous_scanner` | — | 0 | **NO** | no | yes | 0.13 | `UNREACHABLE` |
| `atticus_service` | — | 0 | **NO** | no | no | 0.12 | `UNREACHABLE` |
| `billing_engine` | — | 0 | **NO** | no | no | 0.12 | `UNREACHABLE` |
| `deals` | — | 0 | **NO** | no | no | 0.12 | `UNREACHABLE` |
| `fund_engine` | — | 0 | **NO** | no | no | 0.12 | `UNREACHABLE` |
| `market_benchmarks` | — | 0 | **NO** | no | no | 0.12 | `UNREACHABLE` |
| `preference_engine` | — | 0 | **NO** | no | no | 0.12 | `UNREACHABLE` |
| `treasury_engine` | — | 0 | **NO** | no | no | 0.12 | `UNREACHABLE` |
| `activity` | — | 0 | **NO** | no | no | 0.11 | `UNREACHABLE` |
| `documents` | — | 0 | **NO** | no | no | 0.11 | `UNREACHABLE` |
| `logging_service` | — | 0 | **NO** | no | no | 0.11 | `UNREACHABLE` |
| `migrations` | — | 0 | **NO** | no | no | 0.11 | `UNREACHABLE` |
| `proforma_spreader` | — | 0 | **NO** | no | no | 0.11 | `UNREACHABLE` |
| `ramp_connector` | — | 0 | **NO** | no | no | 0.11 | `UNREACHABLE` |

---

## Regenerate

```bash
python scripts/build_mapping.py
python scripts/wiring_audit.py            # same data, terminal
python scripts/wiring_audit.py --verdict UNREACHABLE
```
