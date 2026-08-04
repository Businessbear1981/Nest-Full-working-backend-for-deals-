"""
Build NEST Operations Manual Volume 3 — The Dictionary.

Volume 3 answers, for every term in the transaction: WHAT it is, WHY it
exists, and WHO is responsible. It is the domain, not the platform — every
entry would still be true if NEST did not exist. How NEST handles a thing
belongs in Volume 4 (docs/NEST_GLOSSARY.md).

This is generated rather than written so it stays traceable. Two sources:

  docs/Bible_Pass1_v2.md      Volume 1. Carries fully structured entries --
                              description, "Established by", "Drafted by",
                              "Signed at", "Establishes" -- for 24 documents.
                              These are quoted, not paraphrased.

  backend/services/           The document catalogue: 60 documents with
    document_package.py       category, owner, silo, prerequisites, and the
                              condition each is contingent on. Code-derived
                              fields are facts about the platform and are
                              marked verified.

Where a document exists in code but has no Bible entry, the generator emits
the verified code fields and marks the WHY as NEEDS AUTHORING. It does not
invent a rationale. A dictionary that quietly fabricates the reason a document
exists is worse than one with visible holes.

    python scripts/build_dictionary.py [--out docs/NEST_DICTIONARY.md]
"""
from __future__ import annotations

import argparse
import datetime as dt
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))

from services.document_package import (           # noqa: E402
    DOCUMENT_CATALOGUE, SILOS,
)

BIBLE = REPO / "docs" / "Bible_Pass1_v2.md"

# Bible heading -> catalogue id. Only where the two genuinely name the same
# artifact; a loose match here would attach the wrong rationale to a document,
# which is the failure mode this whole file exists to avoid.
BIBLE_TO_CATALOGUE = {
    "Preliminary Official Statement (POS)": "preliminary_official_statement",
    "Official Statement (OS)": "official_statement",
    "Investor Pitch Book / Roadshow Deck": "investor_pitch_book",
    "Trust Indenture": "trust_indenture",
    "Supplemental Indenture (When Used)": "supplemental_indenture",
    "Loan Agreement (Conduit Deals)": "loan_agreement",
    "Tax Regulatory Agreement (Tax-Exempt Deals)": "tax_regulatory_agreement",
    "Bond Purchase Agreement": "bond_purchase_agreement",
    "Mortgage and Security Agreement": "mortgage_security_agreement",
    "UCC Financing Statements": "ucc_financing_statements",
    "Assignment of Rents and Leases": "assignment_of_rents",
    "Bond Counsel Opinion": "bond_counsel_opinion",
    "Borrower's Counsel Opinion": "borrowers_counsel_opinion",
    "Trustee's Counsel Opinion": "trustees_counsel_opinion",
    "Underwriter's Counsel Opinion": "underwriters_counsel_opinion",
    "Comfort Letter": "comfort_letter",
    "Auditor's Consent Letter": "auditors_consent",
    "Continuing Disclosure Agreement (CDA)": "continuing_disclosure_agreement",
    "Construction Disbursement Agreement (Construction Bonds)":
        "construction_disbursement_agreement",
    "IRS Form 8038 / 8038-G (Tax-Exempt Bonds)": "form_8038",
    "EMMA Filings (Municipal Bonds)": "emma_filing",
}

# Documents Volume 1 defines that the platform does NOT track. The gap runs
# both ways, and the reverse direction is the more dangerous one: a document
# the doctrine says is required but no silo produces.
BIBLE_ONLY_EXPECTED = {
    "Subordination Agreements",
    "Disclosure Counsel Opinion",
    "Regulatory Agreement (Sector-Specific)",
}

FIELD_RE = re.compile(r"\*\*(Established by|Drafted by|Signed at|Used in|"
                      r"Establishes|Filed by|Filed at) —\*\*\s*(.+)")

SILO_NAME = {s["id"]: s["name"] for s in SILOS}
SILO_SEQ = {s["id"]: s["seq"] for s in SILOS}


def parse_bible() -> dict[str, dict]:
    """Pull the structured document entries out of Volume 1."""
    if not BIBLE.exists():
        return {}
    lines = BIBLE.read_text(encoding="utf-8", errors="replace").splitlines()

    entries: dict[str, dict] = {}
    current: str | None = None
    buf: list[str] = []
    fields: dict[str, str] = {}

    def flush():
        if current and (buf or fields):
            entries[current] = {
                "prose": "\n".join(buf).strip(),
                "fields": dict(fields),
            }

    for line in lines:
        h = re.match(r"^### \*\*(.+?)\*\*\s*$", line)
        if h:
            flush()
            current, buf, fields = h.group(1).strip(), [], {}
            continue
        if current is None:
            continue
        if line.startswith("## ") or line.startswith("# "):
            flush()
            current, buf, fields = None, [], {}
            continue
        m = FIELD_RE.search(line)
        if m:
            fields[m.group(1)] = m.group(2).strip()
        elif line.strip():
            buf.append(line.strip())
    flush()
    return entries


def first_sentences(text: str, n: int = 2) -> str:
    """Opening of the Bible prose -- the definition, before the detail."""
    text = re.sub(r"\s+", " ", text).strip()
    parts = re.split(r"(?<=[.!?]) ", text)
    return " ".join(parts[:n]).strip()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=pathlib.Path,
                    default=REPO / "docs" / "NEST_DICTIONARY.md")
    args = ap.parse_args()

    bible = parse_bible()
    by_id = {d["id"]: d for d in DOCUMENT_CATALOGUE}
    cat_to_bible = {v: k for k, v in BIBLE_TO_CATALOGUE.items()
                    if k in bible}

    sourced = [d for d in DOCUMENT_CATALOGUE if d["id"] in cat_to_bible]
    unsourced = [d for d in DOCUMENT_CATALOGUE if d["id"] not in cat_to_bible]

    today = dt.date.today().isoformat()
    out: list[str] = []
    w = out.append

    w("# NEST Operations Manual — Volume 3")
    w("## The Dictionary")
    w("")
    w(f"> **Generated {today}** by `scripts/build_dictionary.py`. "
      "Do not hand-edit — edit the sources and regenerate, or the volume "
      "and the platform drift apart silently.")
    w(">")
    w("> **What this volume is.** For every term in the transaction: what it "
      "is, why it exists, and who is responsible. This is the *domain*. Every "
      "entry here would still be true if NEST did not exist.")
    w(">")
    w("> **What it is not.** How NEST handles any of this — which module, "
      "which engine, which gate — is **Volume 4** (`docs/NEST_GLOSSARY.md`). "
      "Keep the split. A dictionary that describes our software stops being "
      "useful the moment the software changes.")
    w(">")
    w("> **Confidence.** `verified` — quoted from Volume 1 or read from code "
      "this pass. `NEEDS AUTHORING` — the platform tracks this document but "
      "no rationale has been written. Nothing here is invented to fill a gap.")
    w("")
    w("### The manual")
    w("")
    w("| Volume | Title | What it answers | Status |")
    w("|---|---|---|---|")
    w("| I | The Bible | How bond finance works, silo by silo | Exists — "
      "`docs/Bible_Pass1_v2.md` |")
    w("| II | M&A | Corporate transactions | Not in this repo |")
    w("| III | **The Dictionary** | What each term is, why, and whose job | "
      "**This document** |")
    w("| IV | Modules & Process | How NEST handles each | Partial — "
      "`docs/NEST_GLOSSARY.md`, ~30 of ~160 modules |")
    w("")
    w("### Coverage")
    w("")
    w(f"- **{len(DOCUMENT_CATALOGUE)}** documents tracked by the platform")
    w(f"- **{len(sourced)}** carry a full rationale from Volume 1 — `verified`")
    w(f"- **{len(unsourced)}** have verified code fields but **no authored "
      f"rationale**")
    w("")
    w(f"That second number is the work remaining, stated precisely rather "
      f"than hidden. Each gap below names what it needs.")
    w("")
    w("---")
    w("")

    # ---- Entries, grouped by the silo that produces them.
    for silo in SILOS:
        docs = [d for d in DOCUMENT_CATALOGUE if d["silo"] == silo["id"]]
        if not docs:
            continue
        w(f"## {silo['seq']}. {silo['name']}")
        w("")
        w(f"*Produced during the **{silo['id']}** silo. Fee gate "
          f"`{silo['gate_id']}`.*")
        w("")

        for d in docs:
            b = bible.get(cat_to_bible.get(d["id"], ""), {})
            f = b.get("fields", {})
            w(f"### {d['name']}")
            w("")
            w(f"**Category** · {d['category']}  ")
            w(f"**Responsible** · {d['owner'].replace('_', ' ').title()}  ")
            if d.get("only_if"):
                w(f"**Required only when** · the deal is "
                  f"`{d['only_if']}`  ")
            if d.get("composite"):
                w(f"**Composite** · not a single artifact — see the note "
                  f"below  ")
            w("")

            if b:
                w("**What it is.** " + first_sentences(b["prose"], 3))
                w("")
                for label in ("Established by", "Drafted by", "Signed at",
                              "Used in", "Establishes"):
                    if label in f:
                        w(f"- **{label}** — {f[label]}")
                if any(k in f for k in ("Established by", "Drafted by",
                                        "Signed at", "Used in", "Establishes")):
                    w("")
                w("*Source: Volume 1, Silo 4.* `verified`")
            else:
                w("**What it is.** `NEEDS AUTHORING` — the platform tracks "
                  "this document, but Volume 1 carries no entry for it.")
                w("")
                w("**Why it exists.** `NEEDS AUTHORING`")
                w("")
                w("*Verified from code: category, responsible party, silo, "
                  "and prerequisites below.* `verified`")
            w("")

            if d["requires"]:
                needs = ", ".join(f"`{r}`" for r in d["requires"])
                w(f"**Cannot be produced until** · {needs}")
                w("")

            # Who else is waiting on this one.
            downstream = [o["name"] for o in DOCUMENT_CATALOGUE
                          if d["id"] in o["requires"]]
            if downstream:
                w(f"**Blocks** · {', '.join(downstream)}")
                w("")

        w("---")
        w("")

    # ---- The gap list, so the remaining work is a worklist not a vibe.
    w("## Appendix — what still needs authoring")
    w("")
    w("Each of these is tracked by the platform with verified category, "
      "owner, silo and prerequisites, but has no authored definition or "
      "rationale. This is the Volume 3 backlog.")
    w("")
    w("| Document | Silo | Responsible | Needs |")
    w("|---|---|---|---|")
    for d in sorted(unsourced, key=lambda x: (SILO_SEQ[x["silo"]], x["name"])):
        w(f"| {d['name']} | {SILO_NAME[d['silo']]} | "
          f"{d['owner'].replace('_', ' ').title()} | what it is · why it "
          f"exists |")
    w("")
    # The reverse gap: doctrine requires it, no silo produces it.
    missing_in_code = sorted(
        h for h in BIBLE_ONLY_EXPECTED
        if h in bible and h not in BIBLE_TO_CATALOGUE)
    if missing_in_code:
        w("")
        w("## Appendix — defined in Volume 1, not tracked by the platform")
        w("")
        w("**This is the more serious gap.** Volume 1 defines these as part "
          "of a closing. No silo produces them, so no deal will ever show "
          "them as outstanding. A document nobody is tracking is a document "
          "nobody will notice is missing.")
        w("")
        w("| Document | Volume 1 says |")
        w("|---|---|")
        for h in missing_in_code:
            f = bible[h]["fields"]
            says = f.get("Establishes") or f.get("Established by") or "—"
            w(f"| {h} | {says} |")
        w("")
        w("**Decision required:** add each to `DOCUMENT_CATALOGUE` in "
          "`backend/services/document_package.py` with a silo and "
          "prerequisites, or record in Volume 1 why NEST does not track it.")
        w("")

    w("**How to close a gap:** write the entry into Volume 1 "
      "(`docs/Bible_Pass1_v2.md`) using the existing Silo 4 format — prose "
      "definition, then `**Established by —**`, `**Drafted by —**`, "
      "`**Signed at —**`, `**Establishes —**` — add the heading to "
      "`BIBLE_TO_CATALOGUE` in this script, and regenerate. Do not write "
      "entries directly into this file; they will be overwritten.")

    args.out.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"wrote {args.out}")
    print(f"  {len(DOCUMENT_CATALOGUE)} documents")
    print(f"  {len(sourced)} sourced from Volume 1")
    print(f"  {len(unsourced)} need authoring")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
