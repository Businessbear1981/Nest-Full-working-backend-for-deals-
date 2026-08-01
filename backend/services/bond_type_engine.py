"""
NEST Bond Type Engine
S&P OPBA scoring, all bond types, all amortization schedules, full option generator.
Real math — no stubs.
"""
from __future__ import annotations
from enum import Enum

from services.emma_engine import SECTOR_NAICS_MAP

# ── ENUMS ─────────────────────────────────────────────────────────────────────

class BondType(Enum):
    REVENUE_BOND        = "Revenue Bond (Tax-Exempt)"
    DUAL_TRANCHE_NEST   = "NEST Dual-Tranche"
    BAN                 = "Bond Anticipation Note"
    GREEN_REVENUE       = "Green Revenue Bond"
    SOCIAL_BOND         = "Social Bond"
    SUSTAINABILITY_BOND = "Sustainability Bond"
    TAX_EXEMPT_PAB      = "Tax-Exempt Private Activity Bond"
    TAXABLE             = "Taxable Bond"
    MEZZANINE           = "Mezzanine Bond"
    RULE_144A           = "Rule 144A Private Placement"
    # Ticket 21 additions — remaining bond types from the Grok bond-universe spec
    HOUSING_AUTHORITY   = "Housing Authority Bond"
    GAN                 = "Grant Anticipation Note"
    RAN                 = "Revenue Anticipation Note"
    TAN                 = "Tax Anticipation Note"
    VRDO                = "Variable Rate Demand Obligation"
    BRIDGE_TO_PERMANENT = "Bridge-to-Permanent"


class AmortizationType(Enum):
    LEVEL_DEBT_SERVICE = "Level Debt Service"
    LEVEL_PRINCIPAL    = "Level Principal"
    BULLET             = "Bullet Maturity"
    SCULPTED           = "Constant DSCR Sculpted"
    DEFERRED           = "Deferred Principal (IO)"
    CAB_ACCRETION      = "Capital Appreciation (Zero-Coupon Accreting)"


# ── S&P OPBA SCORING (Real Math) ───────────────────────────────────────────────

def sp_opba_score(
    dscr: float,
    leverage: float,
    liquidity: float,
    qualitative: float = 0.0,
    weights: dict | None = None,
) -> dict:
    """
    S&P OPBA (Operating Business Profile Assessment).
    Quantitative range 0-12. Total cap 16. Readiness scaled 0-100%.
    Weights are self-learning: adjusted by EMA after each closed deal.
    """
    w = weights or {"dscr": 0.40, "leverage": 0.30, "liquidity": 0.30}

    dscr_c      = dscr * w["dscr"]
    leverage_c  = (1.0 / max(leverage, 0.01)) * w["leverage"]
    liquidity_c = liquidity * w["liquidity"]

    quantitative = dscr_c + leverage_c + liquidity_c
    total        = min(12.0, round(quantitative + qualitative, 2))
    readiness    = round(total / 12.0 * 100.0, 1)

    if   total >= 11: rating = "Aaa"
    elif total >= 9:  rating = "Aa2"
    elif total >= 7:  rating = "A2"
    elif total >= 5:  rating = "Baa2"
    elif total >= 3:  rating = "Ba2"
    else:             rating = "B2"

    return {
        "opba_score":        total,
        "readiness_pct":     readiness,
        "indicative_rating": rating,
        "components": {
            "dscr_contribution":      round(dscr_c, 4),
            "leverage_contribution":  round(leverage_c, 4),
            "liquidity_contribution": round(liquidity_c, 4),
            "qualitative":            qualitative,
        },
        "weights_used":    w,
        "jpm_benchmark":   _jpm_grade(dscr, leverage * 20, liquidity),
    }


def _jpm_grade(dscr: float, ltv: float, liquidity: float) -> str:
    if dscr >= 2.0 and ltv <= 55:  return "A-grade (JPM benchmark exceeded)"
    if dscr >= 1.75 and ltv <= 62: return "BBB+ (JPM mid-tier)"
    if dscr >= 1.50 and ltv <= 70: return "BBB- (JPM minimum IG)"
    return "Sub-IG (DSCR breach — enhancement required)"


# ── COUPON ESTIMATION ──────────────────────────────────────────────────────────

_BASE_COUPON = {
    BondType.REVENUE_BOND:        6.50,
    BondType.DUAL_TRANCHE_NEST:   7.00,
    BondType.BAN:                 9.50,
    BondType.GREEN_REVENUE:       6.10,
    BondType.SOCIAL_BOND:         6.20,
    BondType.SUSTAINABILITY_BOND: 6.25,
    BondType.TAX_EXEMPT_PAB:      6.75,
    BondType.TAXABLE:             7.50,
    BondType.MEZZANINE:          11.50,
    BondType.RULE_144A:           8.00,
    # Housing Authority — often HUD/Section 8-backed, essential-service muni
    # credit, prices tighter than a standalone revenue bond.
    BondType.HOUSING_AUTHORITY:   5.25,
    # GAN/RAN/TAN — short-term cash-flow notes backed by a specific
    # anticipated grant/revenue/tax source (not a future bond takeout like
    # BAN), so they price meaningfully tighter than BAN's speculative-takeout
    # risk despite also being short-term.
    BondType.GAN:                 6.75,
    BondType.RAN:                 6.50,
    BondType.TAN:                 6.25,
    # VRDO — floating-rate, weekly/daily put + remarketing, backed by a
    # liquidity facility (LOC/SBPA). This base is the fixed-rate-equivalent
    # anchor before the variable-rate index adjustment applied below;
    # real VRDO pricing floats off SIFMA + spread, not a fixed coupon.
    BondType.VRDO:                3.25,
    # Bridge-to-Permanent — short bridge leg priced like a construction
    # bridge loan; the permanent takeout leg is a separate, later structure
    # (see bridge_to_permanent_conversion() below), not priced here.
    BondType.BRIDGE_TO_PERMANENT: 8.25,
}

# Real anticipated-repayment source per note type — what a GAN/RAN/TAN is
# actually secured by, distinct from BAN's speculative future-bond takeout.
ANTICIPATION_NOTE_SOURCE = {
    BondType.GAN: "grant_award",
    BondType.RAN: "pledged_revenue",
    BondType.TAN: "property_tax_levy",
}

# Real maturity conventions for short-term/bridge instruments — everything
# else falls back to the standard 25/30yr long-bond default.
_SHORT_TERM_MATURITY_YEARS = {
    BondType.BAN: 5,
    BondType.GAN: 2,
    BondType.RAN: 1,
    BondType.TAN: 1,
    BondType.BRIDGE_TO_PERMANENT: 3,
}

# Bridge-to-Permanent conversion triggers — same real vocabulary
# bond_intelligence.py's BAN conversion_triggers already uses, so a deal's
# stage data means the same thing across both engines.
BRIDGE_TO_PERMANENT_CONVERSION_TRIGGERS = [
    "presales_50pct", "feasibility_complete", "GMP_executed", "all_permits",
]

_AMORT_SPREAD = {
    AmortizationType.LEVEL_DEBT_SERVICE: 0.00,
    AmortizationType.LEVEL_PRINCIPAL:   -0.10,
    AmortizationType.BULLET:             0.50,
    AmortizationType.SCULPTED:          -0.15,
    AmortizationType.DEFERRED:           0.75,
    # CABs typically price with a modest premium over current-interest bonds
    # of the same credit — no reinvestment income to the holder and weaker
    # secondary-market liquidity for long-duration zero-coupon paper.
    AmortizationType.CAB_ACCRETION:      0.20,
}


def calculate_coupon(
    bond_type: BondType,
    amort_type: AmortizationType,
    dscr: float = 1.5,
    ltv: float = 70.0,
    is_green: bool = False,
    sifma_index_bps: float | None = None,
) -> float:
    """
    sifma_index_bps: current SIFMA municipal swap index, in bps. Only used
    for VRDO — real VRDO pricing floats off SIFMA + a remarketing/liquidity
    spread, not a fixed base coupon. When not supplied, VRDO falls back to
    its fixed-rate-equivalent anchor in _BASE_COUPON (clearly an estimate,
    not a real floating quote).
    """
    if bond_type == BondType.VRDO and sifma_index_bps is not None:
        base = round(sifma_index_bps / 100.0, 2) + 0.15  # SIFMA + liquidity/remarketing spread
    else:
        base = _BASE_COUPON.get(bond_type, 7.0)
    a_adj   = _AMORT_SPREAD.get(amort_type, 0.0)
    dscr_a  = -0.25 if dscr >= 1.75 else (0.25 if dscr < 1.35 else 0.0)
    ltv_a   =  0.30 if ltv > 75 else (-0.15 if ltv < 60 else 0.0)
    green_a = -0.40 if (is_green and bond_type != BondType.GREEN_REVENUE) else 0.0
    return round(base + a_adj + dscr_a + ltv_a + green_a, 2)


# ── AMORTIZATION SCHEDULE (Real PMT Math) ─────────────────────────────────────

def generate_amortization_schedule(
    par: float,
    coupon_pct: float,
    maturity_years: int,
    amort_type: AmortizationType,
    noi: float = 0.0,
    target_dscr: float = 1.25,
    io_years: int = 2,
) -> list[dict]:
    r       = coupon_pct / 100.0
    n       = maturity_years
    balance = par
    rows    = []

    if amort_type == AmortizationType.BULLET:
        for yr in range(1, n + 1):
            interest  = balance * r
            principal = par if yr == n else 0.0
            _append(rows, yr, balance, interest, principal, noi)
            balance  -= principal

    elif amort_type == AmortizationType.LEVEL_DEBT_SERVICE:
        pmt = (par * r / (1 - (1 + r) ** -n)) if r > 0 else (par / n)
        for yr in range(1, n + 1):
            interest  = balance * r
            principal = min(pmt - interest, balance)
            _append(rows, yr, balance, interest, principal, noi)
            balance   = max(balance - principal, 0.0)

    elif amort_type == AmortizationType.LEVEL_PRINCIPAL:
        principal = par / n
        for yr in range(1, n + 1):
            interest = balance * r
            _append(rows, yr, balance, interest, principal, noi)
            balance  = max(balance - principal, 0.0)

    elif amort_type == AmortizationType.DEFERRED:
        repay = par / max(n - io_years, 1)
        for yr in range(1, n + 1):
            interest  = balance * r
            principal = 0.0 if yr <= io_years else min(repay, balance)
            _append(rows, yr, balance, interest, principal, noi)
            balance   = max(balance - principal, 0.0)

    elif amort_type == AmortizationType.SCULPTED:
        for yr in range(1, n + 1):
            interest  = balance * r
            ds_target = (noi / target_dscr) if noi > 0 else interest * 1.25
            principal = min(max(ds_target - interest, 0.0), balance)
            _append(rows, yr, balance, interest, principal, noi)
            balance   = max(balance - principal, 0.0)

    elif amort_type == AmortizationType.CAB_ACCRETION:
        # Real CAB math: value accretes at the stated rate, compounded
        # semiannually (standard muni convention) — zero cash debt service
        # until maturity, when the full accreted value comes due as a
        # single lump sum. `balance`/`beg_balance`/`end_balance` here track
        # the growing accreted liability, not a shrinking principal balance
        # the way every other amortization type does.
        for yr in range(1, n + 1):
            accreted_value = par * (1 + r / 2) ** (2 * yr)
            prior_value    = par * (1 + r / 2) ** (2 * (yr - 1))
            if yr < n:
                rows.append({
                    "year":           yr,
                    "beg_balance":    round(prior_value, 2),
                    "interest":       round(accreted_value - prior_value, 2),  # accrued, not paid in cash
                    "principal":      0.0,
                    "total_ds":       0.0,   # no cash debt service until maturity
                    "end_balance":    round(accreted_value, 2),
                    "accreted_value": round(accreted_value, 2),
                    "dscr":           None,  # no cash DS this year to compare against NOI
                })
            else:
                rows.append({
                    "year":           yr,
                    "beg_balance":    round(prior_value, 2),
                    "interest":       round(accreted_value - par, 2),  # total accreted interest, paid at maturity
                    "principal":      round(par, 2),
                    "total_ds":       round(accreted_value, 2),
                    "end_balance":    0.0,
                    "accreted_value": round(accreted_value, 2),
                    "dscr":           round(noi / accreted_value, 3) if accreted_value > 0 and noi > 0 else None,
                })

    return rows


def _append(rows, yr, beg, interest, principal, noi):
    ds      = interest + principal
    end_bal = max(beg - principal, 0.0)
    rows.append({
        "year":        yr,
        "beg_balance": round(beg, 2),
        "interest":    round(interest, 2),
        "principal":   round(principal, 2),
        "total_ds":    round(ds, 2),
        "end_balance": round(end_bal, 2),
        "dscr":        round(noi / ds, 3) if ds > 0 and noi > 0 else None,
    })


# ── SECTOR REGISTRY (Ticket 20) ─────────────────────────────────────────────
# suitability_score previously ranked bond type x amortization combinations
# purely on OPBA readiness + DSCR — no sector, NAICS, or bond-type-to-use-case
# fit entered the calculation, so every sector returned the identical top
# recommendation regardless of whether the deal was a water district or a
# sports facility. This registry gives that a real signal: a covenant-level
# DSCR floor per sector (consistent with emma_engine._static_template's
# per-sector defaults) and which bond types actually fit that sector's real
# financing conventions.

REVENUE_SECTOR_REGISTRY: dict[str, dict] = {
    "water_sewer": {
        "dscr_floor": 1.20,
        "fit_bond_types": {BondType.REVENUE_BOND, BondType.TAX_EXEMPT_PAB, BondType.DUAL_TRANCHE_NEST, BondType.GREEN_REVENUE},
    },
    "electric_power": {
        "dscr_floor": 1.10,
        "fit_bond_types": {BondType.REVENUE_BOND, BondType.TAX_EXEMPT_PAB, BondType.DUAL_TRANCHE_NEST, BondType.GREEN_REVENUE},
    },
    "airports": {
        "dscr_floor": 1.25,
        "fit_bond_types": {BondType.REVENUE_BOND, BondType.TAX_EXEMPT_PAB, BondType.DUAL_TRANCHE_NEST},
    },
    "toll_roads": {
        "dscr_floor": 1.30,
        "fit_bond_types": {BondType.REVENUE_BOND, BondType.TAX_EXEMPT_PAB, BondType.DUAL_TRANCHE_NEST},
    },
    "solid_waste": {
        "dscr_floor": 1.20,
        "fit_bond_types": {BondType.REVENUE_BOND, BondType.TAX_EXEMPT_PAB, BondType.DUAL_TRANCHE_NEST, BondType.SUSTAINABILITY_BOND},
    },
    "higher_education": {
        "dscr_floor": 1.20,
        "fit_bond_types": {BondType.REVENUE_BOND, BondType.TAX_EXEMPT_PAB, BondType.DUAL_TRANCHE_NEST},
    },
    "hospitals": {
        "dscr_floor": 1.25,
        "fit_bond_types": {BondType.REVENUE_BOND, BondType.TAX_EXEMPT_PAB, BondType.DUAL_TRANCHE_NEST},
    },
    "senior_living": {
        "dscr_floor": 1.20,
        "fit_bond_types": {BondType.REVENUE_BOND, BondType.TAX_EXEMPT_PAB, BondType.DUAL_TRANCHE_NEST},
    },
    "charter_schools": {
        "dscr_floor": 1.10,
        "fit_bond_types": {BondType.REVENUE_BOND, BondType.TAX_EXEMPT_PAB, BondType.DUAL_TRANCHE_NEST},
    },
    "affordable_multifamily": {
        "dscr_floor": 1.15,
        "fit_bond_types": {BondType.TAX_EXEMPT_PAB, BondType.REVENUE_BOND},
    },
    "market_rate_multifamily": {
        "dscr_floor": 1.25,
        "fit_bond_types": {BondType.TAXABLE, BondType.RULE_144A, BondType.DUAL_TRANCHE_NEST},
    },
    "hotels_hospitality": {
        "dscr_floor": 1.35,
        "fit_bond_types": {BondType.TAXABLE, BondType.RULE_144A, BondType.MEZZANINE},
    },
    "data_centers": {
        "dscr_floor": 1.25,
        "fit_bond_types": {BondType.TAXABLE, BondType.RULE_144A, BondType.DUAL_TRANCHE_NEST},
    },
    "manufacturing": {
        "dscr_floor": 1.25,
        "fit_bond_types": {BondType.TAX_EXEMPT_PAB, BondType.TAXABLE, BondType.RULE_144A},
    },
    "municipal": {
        "dscr_floor": 1.20,
        "fit_bond_types": {BondType.REVENUE_BOND, BondType.TAX_EXEMPT_PAB, BondType.DUAL_TRANCHE_NEST},
    },
    "corporate": {
        "dscr_floor": 1.20,
        "fit_bond_types": {BondType.TAXABLE, BondType.RULE_144A, BondType.MEZZANINE},
    },
}

# NAICS -> sector resolution: exact 6-digit, then 4/3/2-digit prefix
# fallback, then DEFAULT. Built from emma_engine.SECTOR_NAICS_MAP so the two
# modules can't drift into disagreeing about what NAICS code means what
# sector.
_NAICS_EXACT: dict[str, str] = {
    code: sector for sector, codes in SECTOR_NAICS_MAP.items() for code in codes
}


def resolve_sector(naics_code: str) -> str | None:
    """Resolve a NAICS code to a REVENUE_SECTOR_REGISTRY sector key.

    Tries an exact 6-digit match first, then progressively shorter
    prefixes (4, 3, 2 digits), matched against the same prefix length of
    any known code. Returns None (DEFAULT) if nothing matches.
    """
    code = str(naics_code or "").strip()
    if not code:
        return None
    if code in _NAICS_EXACT:
        return _NAICS_EXACT[code]
    for prefix_len in (4, 3, 2):
        prefix = code[:prefix_len]
        if len(prefix) < prefix_len:
            continue
        for known_code, sector in _NAICS_EXACT.items():
            if known_code[:prefix_len] == prefix and sector in REVENUE_SECTOR_REGISTRY:
                return sector
    return None


# ── FULL OPTION GENERATOR ─────────────────────────────────────────────────────

PAR_VALUES = [
    25_000_000, 50_000_000, 75_000_000, 100_000_000,
    150_000_000, 200_000_000, 250_000_000, 500_000_000,
]

# Bands checked around the actual requested amount, e.g. $10.0M bank-qualified.
# The old approach filtered the fixed PAR_VALUES ladder down to a band around
# bond_face — but for any request below the ladder's floor ($25M), that band
# excluded every rung, so nothing sized under $25M (like a real $10.0M BQ
# issue) could ever be produced. Now the candidates are generated from the
# requested amount itself.
_PAR_BANDS = [0.85, 0.90, 0.95, 1.00, 1.05, 1.10, 1.15]


def _par_candidates(bond_face: float) -> list[float]:
    """Par values to price: bands around the actual requested amount when one
    is given, plus the standard ladder for comparison; the standard ladder
    alone when no amount was requested."""
    if bond_face <= 0:
        return PAR_VALUES

    candidates = {round(bond_face * b / 25_000) * 25_000 for b in _PAR_BANDS}
    candidates |= {p for p in PAR_VALUES if bond_face * 0.40 <= p <= bond_face * 2.50}
    return sorted(candidates)


def generate_all_bond_options(deal_data: dict, weights: dict | None = None) -> dict:
    """
    Generate every viable bond type × amortization × par combination for a deal.
    Returns OPBA score, ranked recommendations, and full option matrix.
    """
    noi       = float(deal_data.get("noi") or 0)
    dscr      = float(deal_data.get("dscr") or 1.35)
    ltv       = float(deal_data.get("ltv") or 70)
    bond_face = float(deal_data.get("bond_face") or 0)
    is_green  = bool(deal_data.get("green_bond", False))
    liquidity = float(deal_data.get("liquidity_ratio") or 0.80)
    naics     = str(deal_data.get("naics_code") or "")
    stage     = str(deal_data.get("stage") or "")
    borrower_type_lc = str(deal_data.get("borrower_type") or "").lower()
    nonprofit = borrower_type_lc in (
        "nonprofit", "501c3", "501(c)(3)", "non-profit",
        "governmental", "municipality", "municipal", "issuer", "conduit"
    )
    # Distinct from `nonprofit` above: TAN specifically requires actual
    # taxing authority (property tax levy), which a 501(c)(3) nonprofit
    # doesn't have even though it shares tax-exempt bond eligibility.
    governmental_issuer = borrower_type_lc in (
        "governmental", "municipality", "municipal", "issuer", "conduit"
    )

    leverage = max((ltv / 100.0) * 5.0, 0.1)
    opba     = sp_opba_score(dscr, leverage, liquidity, weights=weights)

    # Determine eligible bond types
    eligible = {BondType.TAXABLE, BondType.RULE_144A}
    if nonprofit or naics[:4] in ("6231", "6232", "6233", "8011"):
        eligible |= {BondType.REVENUE_BOND, BondType.DUAL_TRANCHE_NEST, BondType.TAX_EXEMPT_PAB}
    if is_green or naics[:4] in ("2211", "2212") or naics[:2] == "23":
        eligible |= {BondType.GREEN_REVENUE, BondType.SUSTAINABILITY_BOND, BondType.SOCIAL_BOND}
    # BAN eligibility aligned with bond_intelligence.assess_rating_readiness(),
    # which lists "BAN (unrated, QIB only)" as achievable whenever the deal
    # hasn't cleared the BBB- bar (dscr >= 1.5) yet, and with
    # get_financing_path(), which recommends BAN outright for pre-development
    # stage deals. The old `dscr < 1.30` gate sat below the 1.35 default DSCR
    # used when no dscr is supplied, so BAN was structurally unreachable.
    if dscr < 1.50 or stage == "pre_development":
        eligible.add(BondType.BAN)
    # Mezzanine fills the gap above bond_intelligence's BBB- LTV ceiling
    # (ltv <= 70) — above that, senior-only financing doesn't reach the
    # requested amount and a subordinate tranche is what closes the gap.
    # The old `ltv > 78` threshold sat above every real profile tested.
    if dscr < 1.50 or ltv > 70:
        eligible.add(BondType.MEZZANINE)

    # Housing Authority — nonprofit/governmental issuer on a housing-sector
    # deal (or explicitly flagged as HUD/Section 8-backed).
    if (nonprofit and naics[:4] in ("5311",)) or deal_data.get("housing_authority_backed"):
        eligible.add(BondType.HOUSING_AUTHORITY)
    # GAN — real grant award pending; not a speculative future-bond takeout
    # like BAN, so it's gated on an actual anticipated grant, not just stage.
    if deal_data.get("anticipated_grant_award"):
        eligible.add(BondType.GAN)
    # RAN — routine muni cash-flow bridge against pledged/anticipated
    # revenue; broadly available to nonprofit/governmental issuers, same
    # population as BAN's tax-exempt eligibility.
    if nonprofit and dscr < 1.75:
        eligible.add(BondType.RAN)
    # TAN — requires actual taxing authority (property tax levy), which
    # only a governmental issuer has, not any 501(c)(3) nonprofit.
    if governmental_issuer:
        eligible.add(BondType.TAN)
    # VRDO — needs a liquidity facility (LOC/SBPA) to be economical, which
    # in practice means a large enough issue to justify the facility fee.
    if nonprofit and (bond_face == 0 or bond_face >= 10_000_000):
        eligible.add(BondType.VRDO)
    # Bridge-to-Permanent — pre-stabilization deals (real estate or muni)
    # that will refinance into permanent long-term debt once stabilized;
    # deals already at/above the A-grade DSCR bar wouldn't need a bridge.
    if dscr < 1.75:
        eligible.add(BondType.BRIDGE_TO_PERMANENT)

    # Ticket 20: sector resolution for the suitability_score sector-fit term
    # below. Explicit "sector" key wins if supplied; otherwise resolved from
    # NAICS via REVENUE_SECTOR_REGISTRY/resolve_sector().
    sector = str(deal_data.get("sector") or "").strip() or resolve_sector(naics)
    sector_info = REVENUE_SECTOR_REGISTRY.get(sector) if sector else None

    options = []
    par_candidates = _par_candidates(bond_face)

    for bt in eligible:
        for at in AmortizationType:
            if at == AmortizationType.BULLET and bond_face > 100_000_000:
                continue

            for par in par_candidates:
                mat_yrs  = _SHORT_TERM_MATURITY_YEARS.get(
                    bt, 30 if at == AmortizationType.BULLET else 25
                )
                coupon   = calculate_coupon(bt, at, dscr, ltv, is_green)
                schedule = generate_amortization_schedule(par, coupon, mat_yrs, at, noi, 1.25)

                yr1_dscr = schedule[0]["dscr"] if schedule else None
                yr1_ds   = schedule[0]["total_ds"] if schedule else None
                dscr_component = min(100.0, max(0.0, ((yr1_dscr or dscr) - 1.0) * 100.0))

                if sector_info:
                    # Sector-aware: readiness + DSCR-fit + real sector fit —
                    # was DSCR-optimal only, so e.g. a Special Tax Bond fitting
                    # a sports facility better than a GO bond never showed up;
                    # the mechanically-best DSCR always won regardless of sector.
                    sector_fit = 100.0 if bt in sector_info["fit_bond_types"] else 0.0
                    dscr_floor_met = 100.0 if (yr1_dscr or dscr) >= sector_info["dscr_floor"] else 0.0
                    suitability = round(
                        opba["readiness_pct"] * 0.45 +
                        dscr_component * 0.25 +
                        sector_fit * 0.20 +
                        dscr_floor_met * 0.10,
                        1,
                    )
                else:
                    # No sector resolved (unknown/unmapped NAICS, no sector
                    # supplied) — DSCR-optimal only, same as before. Callers
                    # should treat this case's "top recommendation" as
                    # DSCR-optimal, not sector-validated.
                    suitability = round(
                        opba["readiness_pct"] * 0.6 + dscr_component * 0.4,
                        1,
                    )

                option = {
                    "bond_type":           bt.value,
                    "amortization":        at.value,
                    "par_value":           par,
                    "par_label":           f"${par / 1_000_000:g}M",
                    "coupon_pct":          coupon,
                    "maturity_years":      mat_yrs,
                    "dscr_yr1":            round(yr1_dscr, 3) if yr1_dscr else dscr,
                    "annual_ds_yr1":       round(yr1_ds, 0) if yr1_ds else None,
                    "suitability_score":   suitability,
                    "sector":              sector,
                    "sector_validated":    sector_info is not None,
                    "green_eligible":      is_green or bt in (BondType.GREEN_REVENUE, BondType.SUSTAINABILITY_BOND),
                    "nest_fee_pct":        2.25,
                    "nest_fee_usd":        round(par * 0.0225, 0),
                    "schedule_preview":    schedule[:5],
                    "jpm_grade":           opba["jpm_benchmark"],
                    "rate_type":           "variable" if bt == BondType.VRDO else "fixed",
                }
                if bt in ANTICIPATION_NOTE_SOURCE:
                    option["anticipated_repayment_source"] = ANTICIPATION_NOTE_SOURCE[bt]
                if bt == BondType.BRIDGE_TO_PERMANENT:
                    option["bridge_conversion_triggers"] = BRIDGE_TO_PERMANENT_CONVERSION_TRIGGERS
                options.append(option)

    options.sort(key=lambda x: x["suitability_score"], reverse=True)

    return {
        "opba":            opba,
        "total_options":   len(options),
        "recommendations": options[:3],
        "all_options":     options,
        "deal_metrics": {
            "dscr": dscr, "ltv": ltv, "noi": noi,
            "bond_face": bond_face, "is_green": is_green,
        },
    }
