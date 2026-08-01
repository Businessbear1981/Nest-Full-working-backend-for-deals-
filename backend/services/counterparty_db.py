"""
NEST Counterparty Database — Seeded from Operating Framework Appendix E.

Major counterparties in the middle-market bond ecosystem by role.
The platform's intelligence layer maintains current data;
this provides the baseline per the Operating Framework.
"""

BROKER_DEALERS = [
    {"name": "Piper Sandler", "specialty": "Healthcare, senior living, education", "tier": "major"},
    {"name": "Stifel Financial", "specialty": "Broad middle-market coverage", "tier": "major"},
    {"name": "Hilltop Securities", "specialty": "Texas municipal, middle-market", "tier": "major"},
    {"name": "Raymond James", "specialty": "Broad coverage, strong Southeast", "tier": "major"},
    {"name": "BOK Financial Securities", "specialty": "Central US, energy, muni", "tier": "regional"},
    {"name": "RBC Capital Markets", "specialty": "Canadian cross-border, broad US", "tier": "major"},
    {"name": "Robert W. Baird", "specialty": "Midwest, healthcare, muni", "tier": "major"},
    {"name": "Janney Montgomery Scott", "specialty": "Mid-Atlantic, muni", "tier": "regional"},
    {"name": "B.C. Ziegler", "specialty": "Healthcare and senior living specialist", "tier": "specialty"},
    {"name": "HJ Sims", "specialty": "Senior living specialist", "tier": "specialty"},
]

BOND_COUNSEL = [
    {"name": "Orrick Herrington & Sutcliffe", "specialty": "National, all sectors", "tier": "elite"},
    {"name": "Hawkins Delafield & Wood", "specialty": "National, muni specialist", "tier": "elite"},
    {"name": "Squire Patton Boggs", "specialty": "National, broad coverage", "tier": "major"},
    {"name": "Norton Rose Fulbright", "specialty": "National, energy, infrastructure", "tier": "major"},
    {"name": "Kutak Rock", "specialty": "National, healthcare, housing", "tier": "major"},
    {"name": "Chapman and Cutler", "specialty": "Chicago, national muni", "tier": "major"},
    {"name": "Mintz", "specialty": "National, healthcare, technology", "tier": "major"},
    {"name": "Greenberg Traurig", "specialty": "National, broad coverage", "tier": "major"},
    {"name": "Ballard Spahr", "specialty": "National, muni, housing", "tier": "major"},
    {"name": "Hunton Andrews Kurth", "specialty": "Southeast, energy, infrastructure", "tier": "major"},
    {"name": "McCall Parkhurst & Horton", "specialty": "Texas specialist", "tier": "regional"},
    {"name": "Stradling Yocca Carlson & Rauth", "specialty": "California specialist", "tier": "regional"},
]

TRUSTEE_BANKS = [
    {"name": "U.S. Bank", "specialty": "Largest muni trustee, national coverage", "tier": "dominant"},
    {"name": "BNY Mellon", "specialty": "National, large issuances", "tier": "dominant"},
    {"name": "Wilmington Trust", "specialty": "National, structured finance", "tier": "major"},
    {"name": "UMB Bank", "specialty": "Midwest, growing national", "tier": "major"},
    {"name": "Zions Bank", "specialty": "Western US", "tier": "regional"},
    {"name": "Computershare Trust Company", "specialty": "National, corporate trust", "tier": "major"},
    {"name": "Regions Trust", "specialty": "Southeast", "tier": "regional"},
    {"name": "Truist", "specialty": "Southeast (formerly BB&T/SunTrust)", "tier": "major"},
]

RATING_AGENCIES = [
    {"name": "Moody's Investors Service", "code": "moodys", "specialty": "Dominant in most muni sectors", "nrsro": True},
    {"name": "S&P Global Ratings", "code": "sp", "specialty": "Dominant in most muni sectors", "nrsro": True},
    {"name": "Fitch Ratings", "code": "fitch", "specialty": "Third rating, common as supplemental", "nrsro": True},
    {"name": "Kroll Bond Rating Agency (KBRA)", "code": "kbra", "specialty": "Charter schools, senior living, healthcare specialty", "nrsro": True},
    {"name": "DBRS Morningstar", "code": "dbrs", "specialty": "CMBS, structured finance, growing muni", "nrsro": True},
]

BOND_INSURERS = [
    {"name": "Assured Guaranty (AGM)", "rating": "AA", "outlook": "Stable", "specialty": "Largest active insurer, broad coverage", "active_writer": True, "market_share_pct": 58},
    {"name": "Assured Guaranty (AGC)", "rating": "AA", "outlook": "Stable", "specialty": "Subsidiary, different risk appetite", "active_writer": True, "market_share_pct": 0},  # subsidiary of AGM above — market share counted under AGM
    {"name": "Build America Mutual (BAM)", "rating": "AA", "outlook": "Stable", "specialty": "Mutual model, competitive pricing", "active_writer": True, "market_share_pct": 42},
    {"name": "Berkshire Hathaway Assurance", "rating": "AA+", "outlook": "Stable", "specialty": "Selective, large deals", "active_writer": False, "market_share_pct": 0},
]

# Real two-writer market structure — Assured Guaranty and BAM are the only
# two active new-issue municipal bond insurers today; everyone else
# (Berkshire Hathaway Assurance included) writes selectively if at all.
BOND_INSURANCE_ACTIVE_WRITERS = [i for i in BOND_INSURERS if i["active_writer"] and i["market_share_pct"] > 0]

# Real premium range for municipal bond insurance, priced off total
# scheduled debt service (principal + interest over the bond's life) — not
# off bond face like the construction-surety pricing bug fixed in Ticket 7.
# Actual quotes vary within this band based on credit quality; this is the
# real market range, not a single "recommended" number to hard-quote.
BOND_INSURANCE_PREMIUM_PCT_RANGE = {"min": 0.75, "max": 1.50}


def bond_insurance_premium(total_debt_service: float, credit_quality: str = "average") -> dict:
    """Real bond insurance premium mechanics: priced as a percentage of
    total scheduled debt service (principal + interest), within the real
    0.75-1.5% market range — not a single hardcoded rate, and not priced
    off bond face.

    credit_quality: "strong" prices toward the low end of the range,
    "weak" toward the high end, "average" at the midpoint. This maps
    quality to a position in the real range; it does not invent a new
    pricing model.
    """
    position = {"strong": 0.0, "average": 0.5, "weak": 1.0}.get(credit_quality, 0.5)
    lo, hi = BOND_INSURANCE_PREMIUM_PCT_RANGE["min"], BOND_INSURANCE_PREMIUM_PCT_RANGE["max"]
    premium_pct = lo + (hi - lo) * position
    return {
        "premium_pct_of_total_debt_service": round(premium_pct, 3),
        "premium_usd": round(total_debt_service * premium_pct / 100.0),
        "total_debt_service": round(total_debt_service),
        "range_used": BOND_INSURANCE_PREMIUM_PCT_RANGE,
        "active_writers": [
            {"name": i["name"], "rating": i["rating"], "outlook": i["outlook"], "market_share_pct": i["market_share_pct"]}
            for i in BOND_INSURANCE_ACTIVE_WRITERS
        ],
    }

LOC_BANKS = [
    {"name": "JPMorgan Chase", "st_rating": "A-1+", "specialty": "Largest LOC provider"},
    {"name": "Bank of America", "st_rating": "A-1+", "specialty": "Broad muni coverage"},
    {"name": "Wells Fargo", "st_rating": "A-1+", "specialty": "Strong West Coast"},
    {"name": "Citi", "st_rating": "A-1", "specialty": "National, large deals"},
    {"name": "PNC Bank", "st_rating": "A-1", "specialty": "Mid-Atlantic, Midwest"},
    {"name": "TD Bank", "st_rating": "A-1+", "specialty": "Northeast, Canadian-backed"},
    {"name": "Royal Bank of Canada", "st_rating": "A-1+", "specialty": "Canadian, cross-border"},
    {"name": "Mizuho", "st_rating": "A-1", "specialty": "Japanese, selective US muni"},
    {"name": "MUFG", "st_rating": "A-1", "specialty": "Japanese, growing US presence"},
]

FEASIBILITY_CONSULTANTS = {
    "senior_living": [
        {"name": "Kaufman Hall", "specialty": "Market study, financial feasibility"},
        {"name": "Plante Moran", "specialty": "Financial advisory, feasibility"},
        {"name": "Ziegler", "specialty": "Senior living specialist"},
        {"name": "CliftonLarsonAllen", "specialty": "Financial advisory"},
        {"name": "SmithGroup", "specialty": "Architecture + feasibility"},
        {"name": "Continuum Development Services", "specialty": "Development advisory"},
    ],
    "affordable_housing": [
        {"name": "Novogradac", "specialty": "LIHTC, PAB specialist"},
        {"name": "CohnReznick", "specialty": "Housing finance advisory"},
        {"name": "Plante Moran", "specialty": "Financial advisory"},
    ],
    "hospitals": [
        {"name": "Kaufman Hall", "specialty": "Healthcare strategic advisory"},
        {"name": "Crowe", "specialty": "Healthcare consulting"},
        {"name": "BDO USA", "specialty": "Healthcare advisory"},
        {"name": "Vizient Advisory Solutions", "specialty": "Healthcare operations"},
        {"name": "ECG Management Consultants", "specialty": "Physician advisory"},
    ],
    "charter_schools": [
        {"name": "EdTec", "specialty": "Charter school financial management"},
        {"name": "Charter School Capital", "specialty": "Charter finance specialist"},
        {"name": "Building Hope", "specialty": "Charter facility development"},
        {"name": "IFF", "specialty": "Nonprofit lending, charter schools"},
    ],
    "hospitality": [
        {"name": "STR Inc.", "specialty": "Hotel data and analytics"},
        {"name": "HVS", "specialty": "Hotel valuation and consulting"},
        {"name": "CBRE Hotels Advisory", "specialty": "Hotel investment advisory"},
        {"name": "Pinnacle Advisory Group", "specialty": "Hotel management advisory"},
    ],
    "data_centers": [
        {"name": "Cushman & Wakefield Data Center Advisory", "specialty": "Data center consulting"},
        {"name": "JLL Data Centers", "specialty": "Data center advisory"},
        {"name": "CBRE Data Center Solutions", "specialty": "Data center investment"},
    ],
}

CONSTRUCTION_MONITORS = [
    {"name": "Partner Engineering and Science", "specialty": "National, broad coverage"},
    {"name": "EMG", "specialty": "National, environmental + construction"},
    {"name": "ECS Limited", "specialty": "Mid-Atlantic, Southeast"},
    {"name": "Adams Engineering", "specialty": "Regional"},
    {"name": "Inspection Services Inc.", "specialty": "National"},
    {"name": "Crawford and Company", "specialty": "National, claims + monitoring"},
    {"name": "Construction Risk Management", "specialty": "Specialty construction risk"},
]

VERIFICATION_AGENTS = [
    {"name": "Robert Thomas CPA", "specialty": "Arbitrage rebate verification"},
    {"name": "Causey Demgen & Moore", "specialty": "Arbitrage rebate, yield restriction"},
    {"name": "Bingham Arbitrage Rebate Services", "specialty": "Arbitrage rebate specialist"},
    {"name": "Grant Thornton", "specialty": "Verification, broad coverage"},
    {"name": "Crowe LLP", "specialty": "Verification, healthcare expertise"},
]

DISSEMINATION_AGENTS = [
    {"name": "Digital Assurance Certification (DAC)", "specialty": "Largest EMMA dissemination agent"},
    {"name": "Lumesis", "specialty": "Continuing disclosure management"},
    {"name": "BLX (Bond Logistix)", "specialty": "Post-issuance compliance"},
    {"name": "Acacia Financial Group", "specialty": "Municipal advisory + dissemination"},
]

QOE_FIRMS = [
    {"name": "Riveron", "specialty": "Mid-market QofE specialist"},
    {"name": "RSM", "specialty": "National, broad middle-market"},
    {"name": "Crowe", "specialty": "Healthcare expertise"},
    {"name": "BDO", "specialty": "National, broad coverage"},
    {"name": "Eisner Amper", "specialty": "Mid-Atlantic, technology"},
    {"name": "FTI Consulting", "specialty": "Large, complex transactions"},
    {"name": "Alvarez & Marsal", "specialty": "Restructuring + QofE"},
    {"name": "BRG (Berkeley Research Group)", "specialty": "Complex disputes + QofE"},
    {"name": "Stout", "specialty": "Valuation + QofE"},
    {"name": "CohnReznick", "specialty": "Real estate, housing"},
]


def get_counterparties_by_role(role: str) -> list[dict]:
    """Get counterparties by role type."""
    role_map = {
        "broker_dealer": BROKER_DEALERS,
        "bond_counsel": BOND_COUNSEL,
        "trustee": TRUSTEE_BANKS,
        "rating_agency": RATING_AGENCIES,
        "bond_insurer": BOND_INSURERS,
        "loc_bank": LOC_BANKS,
        "construction_monitor": CONSTRUCTION_MONITORS,
        "verification_agent": VERIFICATION_AGENTS,
        "dissemination_agent": DISSEMINATION_AGENTS,
        "qoe_firm": QOE_FIRMS,
    }
    return role_map.get(role, [])


def get_feasibility_consultants(sector: str) -> list[dict]:
    """Get feasibility consultants for a specific sector."""
    return FEASIBILITY_CONSULTANTS.get(sector, [])


def get_all_counterparties() -> dict:
    """Return full counterparty database."""
    return {
        "broker_dealers": BROKER_DEALERS,
        "bond_counsel": BOND_COUNSEL,
        "trustee_banks": TRUSTEE_BANKS,
        "rating_agencies": RATING_AGENCIES,
        "bond_insurers": BOND_INSURERS,
        "loc_banks": LOC_BANKS,
        "feasibility_consultants": FEASIBILITY_CONSULTANTS,
        "construction_monitors": CONSTRUCTION_MONITORS,
        "verification_agents": VERIFICATION_AGENTS,
        "dissemination_agents": DISSEMINATION_AGENTS,
        "qoe_firms": QOE_FIRMS,
        "total_count": (
            len(BROKER_DEALERS) + len(BOND_COUNSEL) + len(TRUSTEE_BANKS) +
            len(RATING_AGENCIES) + len(BOND_INSURERS) + len(LOC_BANKS) +
            len(CONSTRUCTION_MONITORS) + len(VERIFICATION_AGENTS) +
            len(DISSEMINATION_AGENTS) + len(QOE_FIRMS) +
            sum(len(v) for v in FEASIBILITY_CONSULTANTS.values())
        ),
    }
