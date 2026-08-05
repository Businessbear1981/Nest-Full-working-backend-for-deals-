---
name: kevin
description: Run a cross-working session with Kevin — open with the generated synopsis (code pushed, new modules and terms, backend/frontend integration, what regressed), work under the rebuild-don't-patch rule, close by publishing to the shared workspace. Use when starting or ending a joint session, preparing a handoff for Kevin, or when asked what has changed since you last spoke.
---

# Cross-working session with Kevin

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

## Open

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

## The standing rule

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

## Verdicts, and what each obliges

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

## Ground rules, both directions

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

## Close

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

## Writing to Kevin

Lead with the finding, not the effort. Order the work by what it costs to fix
against what it buys — HOLLOW, then WIRE, then BUILD_FRONTEND, then the
route-or-delete decisions, with anything live and wrong pulled ahead of all of
it.

When the finding is critical of work he did, pair it with one of your own. Not
as softening — because the argument is about writing checks down rather than
eyeballing them, and that argument is only honest if it applies to both of
you.
