# NEST — Brand, Voice & Domain Constants

> Moved from the old fat `CLAUDE.md` (2026-07-14). Apply on every UI surface and AI output.
> Charter/SOP live in `AGENTS.md`; current state in `docs/STATE.md`.

## Brand — always apply

```
Colors:
  --nest-void:    #030A06   (primary background)
  --nest-forest:  #0D2218   (card backgrounds)
  --nest-green:   #1E4A2E   (mid surfaces)
  --nest-pine:    #2D6B3D   (accents)
  --nest-navy:    #060E1A   (deep sections)
  --nest-gold:    #C4A048   (primary accent — all financial figures)
  --nest-gold-hi: #E8C87A   (hover states)
  --nest-sage:    #7A9A82   (secondary text)
  --nest-cream:   #EDE8DC   (primary text)

Fonts:
  Headings:  Cormorant Garamond (serif)
  Body:      Space Grotesk (sans)
  Data/Code: IBM Plex Mono (mono — ALL financial figures use this)
```

## Voice — every AI output

- **Tone:** Jimmy Lee (JPMorgan legend) — direct, decisive, no hedging, no passive voice.
- **Rules:** lead with conclusion · one idea per sentence · numbers are authority.
- **Banned words:** may, might, could, potentially, approximately, it seems.
- **System prompt name:** Morgan (memo/content agent).
- **Every memo references** Jacaranda Trace PLOM as the structural template.

## Agent fleet (15 agents)

```
Vector       — Call/put timing (14 market signals, 15-min intervals)
Apex         — Short position manager (TLT puts, T-note futures, IRS)
Chain        — Blockchain execution (ERC-1400, smart contract calls)
Atlas        — Financial modeling (10yr proforma, stress scenarios)
Morgan       — Memo + marketing writer (Jimmy Lee tone, Claude API)
Sterling     — Investor placement (CRM, book building, AEC token)
Bridge       — Perm debt monitoring (18mo before stabilization)
Quantum      — HFT fund optimizer ($32.4M AUM, 21.3% YTD)
Maxwell      — Credit analyst (DSCR, LTV, LGD, obligor grade)
Aria         — Client + BD outreach (cold/warm, follow-up sequences)
Merlin       — M&A intelligence (NAICS scan, scoring, business plans)
LenderScout  — Direct lender sourcing (800+ lenders, match engine)
Prometheus   — Financial modeling engine (proforma, feasibility, audit sim)
Sentinel     — Risk assessment engine (7 dimensions, automated alerts)
Blaze        — Elite marketing engine (market intel, decks, content calendar)
```

## JP Morgan credit benchmarks (hardcode everywhere)

```
A-grade:  DSCR>2.0, CF_leverage<1.5, BS_leverage<2.0, LTV<55%, D/EBITDA<4.5, ICR>3.5
BBB+:     DSCR>1.75, CF_leverage<1.75, BS_leverage<2.25, LTV<62%, D/EBITDA<5.5, ICR>2.75
BBB-:     DSCR>1.5, CF_leverage<2.0, BS_leverage<2.5, LTV<70%, D/EBITDA<6.5, ICR>2.25
Sub-IG:   DSCR<1.5 (any single breach = sub-investment grade)
```

## Capital structure (NEST model — always use this)

```
Series A:  75% LTC · Investment grade · Hylant surety / LC · 6.5-7.5% coupon
Series B:  +7% (82% CLTV) · B/BBB · Bank managed · 10-14% coupon
IO:        Pre-funded from proceeds · No cash drag during construction
Reserve:   2.5% maturity reserve escrowed · Returned at maturity
HFT Fund:  B tranche AUM → Quantum agent → 15-25% target return
LC Phase:  AUM $0-15M=surety · $15-40M=hybrid · $40-80M=LC dominant · $80M+=self-collateralized
```
