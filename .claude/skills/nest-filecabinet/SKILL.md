---
name: nest-filecabinet
description: File what NEST did today into a dated, append-only log — decided, built, found, open. Use at the end of a working session, when asked to write up the day, when preparing a handoff for tomorrow, or when someone asks why a past decision was made.
---

# File Cabinet

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

## File the day

```bash
"C:\Users\Sean Gilmore\AppData\Local\Programs\Python\Python312\python.exe" \
  .claude/skills/nest-filecabinet/file_day.py
```

It reads git for what was **built** and writes a scaffolded entry. Everything
else needs a human: git records what changed, never what was decided or found.

Options: `--date YYYY-MM-DD` to backfill · `--handoff` to also emit tomorrow's
starting prompt · `--print` to write nothing and just look.

---

## The four sections

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

## Rules

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

## Reading it back

- **State of the union** — read the DECIDED and OPEN sections since the last
  one. That is the agenda.
- **Why did we do it this way** — grep DECIDED.
- **What is still broken** — grep FOUND, minus anything a later entry closes.
- **Tomorrow's first prompt** — `--handoff` renders OPEN into a starting brief.

---

## Format

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
