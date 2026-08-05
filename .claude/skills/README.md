# nest-skills

Repeatable NEST procedures, packaged so they run the same way every time.

**The problem this solves.** The same work was being redone from scratch every
session — the deal chain hand-rolled as a throwaway script, the document format
reconstructed from memory, the verification pass done or skipped depending on
how much time was left. Two briefs written a day apart could quote different
numbers for the same deal, and neither author would know.

A skill is loaded on demand when the work matches its description. It does not
consume context until it is needed.

---

## The skills

| Skill | Use it when | What it locks |
|---|---|---|
| **`nest-docs`** | Designing what a silo owes a client | The 60-document package, ten silos, each joined to a fee gate |
| **`nest-house-style`** | Producing any document that leaves this machine | Format, confidence tagging, threshold provenance, anti-fabrication rules |
| **`nest-deal-run`** | Running a deal through NEST, sizing a fee, assessing financeability | One script, the whole engine chain, real output |
| **`nest-truth-shield`** | Before anything goes to a client; when asked "do you agree" | Verification before assertion; the standing red list |
| **`nest-filecabinet`** | End of a working session; writing up the day; asking why a past decision was made | One dated file, four sections, append-only |
| **`kevin`** | Opening or closing a cross-working session with Kevin | The generated synopsis, the rebuild-don't-patch rule, publishing to the shared workspace |

They compose. The intended flow:

```
kevin             →  open the session on agreed, generated facts
nest-docs         →  decide what the silo owes
nest-deal-run     →  produce the numbers by running the engines
nest-house-style  →  format them into a document, tagged and sourced
nest-truth-shield →  verify every claim before it leaves
nest-filecabinet  →  file what was decided, built, found, and left open
kevin             →  close the session and publish it
```

`kevin` brackets the others: it is the only skill that appears twice, because
a session that opens on agreed facts and never closes on a filed record leaves
the next one reconstructing both from memory.

---

## Design rules for anything added here

**1 · A skill calls the code. It never reimplements it.**
The engines in `backend/services/` are the single source of truth for every
NEST number. A skill is the *procedure* for invoking them and presenting the
result. The moment a skill hardcodes a threshold, there are two sources of
truth and one of them is silently wrong.

**2 · Earn the slot.** Add a skill when the same work has been done from
scratch three or more times, or when getting it wrong is expensive. Three
skills that get used beat fifteen that are ignored — and an ignored skill
directory trains people to stop reading it.

**3 · A skill that only restates what the code does is waste.** The value is
the judgment around the code: which model to choose, what the output means,
what not to say to a client, where the number is hand-set.

**4 · Encode the honesty rules, not just the happy path.** Every skill here
carries the anti-fabrication discipline, because the failure mode this platform
actually has is confident output that is not true.

---

## Deliberately not skills yet

Considered and rejected for now, so nobody re-proposes them without new
reasoning:

- **`nest-client-brief`** — this is `nest-deal-run` plus `nest-docs` with a
  different section order. Would duplicate both.
- **`nest-fee-schedule`** — already the fee ledger section of `nest-deal-run`.
- **`nest-emma-pull`** — cannot be written honestly until the EMMA access
  question is resolved. The connector returns 403 and MSRB blocks server-side
  access. A skill wrapping a broken feed is worse than no skill.

---

## Extracting to a standalone repo

These live in `.claude/skills/` because that is where Claude Code loads project
skills from. If they are to be shared across repositories, the pattern already
in use here is `skills-lock.json`, which pins external skills by source and
content hash — see the `supabase` entries.

To extract: move this directory to a `nest-skills` repository, then reference
it from each consuming project's `skills-lock.json` with a pinned hash. Pin the
hash. Skills that change under you silently are worse than no skills, for the
same reason a hardcoded status is worse than a red light.

Until there is a second repository that needs them, extraction is premature.
