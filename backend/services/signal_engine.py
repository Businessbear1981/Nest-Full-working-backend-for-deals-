"""
NEST Three-Node Signal Intelligence Engine

Pipeline:
  Node 1 (Origination) — scans EDGAR and Census permits for trigger events
  Node 2 (Qualification) — scores every signal against NEST benchmarks
  Node 3 (Action) — routes qualified signals to the right desk

Ticket 18 consolidation: this is the real base of the scanning/signal
cluster — the strongest qualification/routing logic of the four
independent EDGAR implementations that used to exist. EagleEyeScanner's
broader FRED market-context, sector-comparable EDGAR search, and
maturity-wall coverage are merged in below (scan_sector_comparables(),
get_fred_market_context(), scan_maturity_wall()) rather than left as a
separate, unscored data source. AutonomousScanner and MerlinAgent now
delegate their EDGAR scanning here instead of maintaining their own
httpx clients — see services/autonomous_scanner.py and agents/merlin.py.

No imports from routes/. Uses only httpx and stdlib.
"""
from __future__ import annotations

import os
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Callable

import httpx

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_EDGAR_HEADERS = {
    "User-Agent": "NEST-Advisors/1.0 sean.gilmore@ardanedgecapital.com",
    "Accept": "application/json",
}

# NAICS codes NEST cares about:
# 623 = Nursing & Residential Care
# 621 = Ambulatory Health Care
# 531 = Real Estate
# 518 = Data Processing / Hosting
_TARGET_NAICS = {"623", "621", "531", "518"}

_HOT_STATES = {"TX", "FL", "CA", "WA", "OR", "CO", "AZ"}

# Ported from EagleEyeScanner.search_edgar_comparables() — sector-specific
# search terms for EDGAR full-text comparable filing search.
_SECTOR_COMPARABLE_TERMS = {
    "senior_living": '"senior living" OR "continuing care retirement" OR "CCRC"',
    "healthcare": '"healthcare" OR "hospital" OR "medical center"',
    "multifamily": '"multifamily" OR "apartment complex" OR "residential rental"',
    "data_centers": '"data center" OR "colocation facility"',
    "industrial": '"industrial park" OR "warehouse" OR "logistics center"',
}

# Real reference figures on the construction/bridge loan maturity wall —
# ported from EagleEyeScanner.scan_maturity_wall(). Static market-context
# data, not a live scan (same nature as emma_engine's sector defaults).
_MATURITY_WALL_CONTEXT = {
    "total_maturities_2026": 162_100_000_000,
    "total_maturities_2027": 167_700_000_000,
    "multifamily_share": 0.33,
}
_MATURITY_WALL_MARKET_DATA = {
    "austin": {
        "market": "Austin, TX",
        "vacancy_rate": 0.142,
        "concession_weeks": "6-12",
        "modified_loan_share": "above national average",
        "outlook": "Gradual recovery late 2026-2027",
        "distressed_signals": [
            {"type": "construction_exit", "description": "Multiple new builds below 80% occupancy"},
            {"type": "maturity_wall", "description": "Banks extending maturities hoping for recovery"},
            {"type": "distressed", "description": "Concessions 6-12 weeks indicate absorption challenges"},
        ],
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _days_since(date_str: str) -> int:
    """Return calendar days between date_str (YYYY-MM-DD) and today. -1 on error."""
    try:
        dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
        return (datetime.utcnow() - dt).days
    except Exception:
        return -1


def _extract_state(text: str) -> str:
    """Best-effort: find a two-letter US state abbreviation in text."""
    _STATES = {
        "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
        "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
        "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
        "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
        "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
        "DC",
    }
    # Try "City, ST" pattern first
    m = re.search(r",\s*([A-Z]{2})\b", text)
    if m and m.group(1) in _STATES:
        return m.group(1)
    # Fall back to any bare state code
    for token in re.findall(r"\b([A-Z]{2})\b", text):
        if token in _STATES:
            return token
    return ""


def _revenue_in_range(text: str) -> bool:
    """Return True if text contains a revenue figure between ~$30M and $150M."""
    text_lower = text.lower()
    # Look for explicit million-dollar amounts in range
    for m in re.finditer(r"\$?\s*(\d+(?:\.\d+)?)\s*(?:million|mn|m\b)", text_lower):
        try:
            val = float(m.group(1))
            if 30 <= val <= 150:
                return True
        except ValueError:
            pass
    # Also check for bare numbers like "30 million" written differently
    for phrase in ["30 million", "50 million", "75 million", "100 million",
                   "120 million", "150 million"]:
        if phrase in text_lower:
            return True
    return False


def _ebitda_sub_20m(text: str) -> bool:
    """Return True if text hints EBITDA < $20M."""
    text_lower = text.lower()
    if "ebitda" not in text_lower:
        return False
    for m in re.finditer(r"ebitda.*?\$?\s*(\d+(?:\.\d+)?)\s*(?:million|mn|m\b)", text_lower):
        try:
            if float(m.group(1)) < 20:
                return True
        except ValueError:
            pass
    return False


# ---------------------------------------------------------------------------
# SignalEngine
# ---------------------------------------------------------------------------

class SignalEngine:
    """Three-node pipeline: originate → qualify → route."""

    def __init__(self) -> None:
        self._cache: dict[str, tuple[Any, float]] = {}
        self._session: httpx.Client | None = None

    # ------------------------------------------------------------------
    # Internal utilities
    # ------------------------------------------------------------------

    def _http(self) -> httpx.Client:
        if not self._session:
            self._session = httpx.Client(
                timeout=15.0,
                headers=_EDGAR_HEADERS,
            )
        return self._session

    def _cached(self, key: str, fn: Callable, ttl: float = 900) -> Any:
        """Generic TTL cache wrapper (default 15 min)."""
        if key in self._cache:
            data, exp = self._cache[key]
            if time.time() < exp:
                return data
        data = fn()
        self._cache[key] = (data, time.time() + ttl)
        return data

    def _edgar_search(self, params: dict) -> list[dict]:
        """
        Hit EDGAR full-text search. Returns the raw hits list or [].
        Caches for 30 minutes per unique param set.
        """
        cache_key = "edgar:" + str(sorted(params.items()))

        def _fetch() -> list[dict]:
            try:
                resp = self._http().get(
                    "https://efts.sec.gov/LATEST/search-index",
                    params=params,
                )
                resp.raise_for_status()
                body = resp.json()
                return body.get("hits", {}).get("hits", [])
            except Exception:
                return []

        return self._cached(cache_key, _fetch, ttl=1800)  # 30 min

    @staticmethod
    def _parse_edgar_hit(hit: dict) -> dict:
        """Extract common fields from a single EDGAR hit."""
        src = hit.get("_source", {})
        entity = (
            src.get("entity_name")
            or (src.get("display_names") or [""])[0]
            or src.get("file_num", "Unknown Entity")
        )
        filing_date = src.get("file_date") or src.get("period_of_report", "")
        form_type = src.get("form_type", "")
        # Try to build a snippet from highlights, fall back to biz_location
        highlight = hit.get("highlight", {})
        raw_snippet = highlight.get("file_description_string") or [
            src.get("biz_location", "")
        ]
        if isinstance(raw_snippet, list):
            raw_snippet = " … ".join(raw_snippet[:2])
        snippet = str(raw_snippet)[:200]

        # Direct EDGAR filing URL
        accession = src.get("file_num") or src.get("adsh", "")
        cik = src.get("file_num", "")
        edgar_url = (
            f"https://www.sec.gov/cgi-bin/browse-edgar"
            f"?action=getcompany&company={entity}&type={form_type}&dateb=&owner=include&count=40"
        )
        if accession:
            edgar_url = f"https://www.sec.gov/Archives/edgar/data/{accession}"

        state = _extract_state(
            src.get("biz_location", "") + " " + snippet
        )

        return {
            "entity": str(entity).strip(),
            "filing_date": str(filing_date),
            "form_type": str(form_type),
            "state": state,
            "edgar_url": edgar_url,
            "snippet": snippet,
        }

    # ==================================================================
    # NODE 1 — ORIGINATION
    # ==================================================================

    def scan_edgar_ma_targets(self, naics_codes: list[str] = None) -> list[dict]:
        """
        Scan EDGAR for M&A trigger events and size-qualifying companies.
        Returns list of raw signal dicts (raw_score=0.0).
        """
        results: list[dict] = []

        # --- Query 1: merger / acquisition agreements ---
        hits_ma = self._edgar_search({
            "q": '"merger agreement" OR "acquisition agreement"',
            "forms": "8-K,SC 13D",
            "dateRange": "custom",
            "startdt": "2025-01-01",
            "enddt": "2026-12-31",
        })

        for hit in hits_ma[:25]:
            base = self._parse_edgar_hit(hit)
            src = hit.get("_source", {})
            form = base["form_type"]

            # Determine trigger event
            snippet_lower = base["snippet"].lower()
            if "merger" in snippet_lower:
                trigger = "merger_agreement"
            elif "schedule 13d" in snippet_lower or form == "SC 13D":
                trigger = "schedule_13d"
            else:
                trigger = "acquisition_target"

            # NAICS hint — pull from description if present
            naics_hint = src.get("sic", "") or src.get("naics", "") or ""

            # Optional NAICS filter
            if naics_codes and naics_hint and not any(
                naics_hint.startswith(nc) for nc in naics_codes
            ):
                continue

            ticker = src.get("ticker") or src.get("file_num", "")

            results.append({
                "signal_type": "ma_target",
                "entity": base["entity"],
                "ticker": str(ticker),
                "filing_date": base["filing_date"],
                "form_type": base["form_type"],
                "naics_hint": str(naics_hint),
                "state": base["state"],
                "trigger_event": trigger,
                "edgar_url": base["edgar_url"],
                "snippet": base["snippet"],
                "raw_score": 0.0,
            })

        # --- Query 2: annual revenue size indicators ---
        hits_rev = self._edgar_search({
            "q": (
                '"annual revenue" "30 million" OR "50 million" OR '
                '"75 million" OR "100 million"'
            ),
            "forms": "10-K",
            "dateRange": "custom",
            "startdt": "2025-01-01",
            "enddt": "2026-12-31",
        })

        for hit in hits_rev[:15]:
            base = self._parse_edgar_hit(hit)
            src = hit.get("_source", {})
            naics_hint = src.get("sic", "") or src.get("naics", "") or ""

            if naics_codes and naics_hint and not any(
                naics_hint.startswith(nc) for nc in naics_codes
            ):
                continue

            results.append({
                "signal_type": "ma_target",
                "entity": base["entity"],
                "ticker": str(src.get("ticker", "")),
                "filing_date": base["filing_date"],
                "form_type": base["form_type"],
                "naics_hint": str(naics_hint),
                "state": base["state"],
                "trigger_event": "acquisition_target",
                "edgar_url": base["edgar_url"],
                "snippet": base["snippet"],
                "raw_score": 0.0,
            })

        return results

    def scan_edgar_cre_events(self) -> list[dict]:
        """
        Scan EDGAR for real estate bond issuances and property events.
        Returns list of raw signal dicts (raw_score=0.0).
        """
        hits = self._edgar_search({
            "q": '"ground lease" OR "land acquisition" OR "construction financing"',
            "forms": "S-11,1-A,424B3",
            "dateRange": "custom",
            "startdt": "2024-01-01",
            "enddt": "2026-12-31",
        })

        results: list[dict] = []
        for hit in hits[:30]:
            base = self._parse_edgar_hit(hit)
            snippet_lower = base["snippet"].lower()

            if "ground lease" in snippet_lower:
                trigger = "ground_lease"
            elif "land acquisition" in snippet_lower or "land purchase" in snippet_lower:
                trigger = "land_purchase"
            else:
                trigger = "bond_issuance"

            results.append({
                "signal_type": "cre_bond_issuance",
                "entity": base["entity"],
                "filing_date": base["filing_date"],
                "form_type": base["form_type"],
                "state": base["state"],
                "trigger_event": trigger,
                "edgar_url": base["edgar_url"],
                "snippet": base["snippet"],
                "raw_score": 0.0,
            })

        return results

    def scan_construction_permits(self, states: list[str] = None) -> list[dict]:
        """
        Pull state-level residential permit counts from Census Bureau BPS.
        Returns list of raw signal dicts (raw_score=0.0).
        Falls back to [] on any error — Census API is finicky.
        """
        cache_key = "census:bps:" + str(sorted(states or []))

        def _fetch() -> list[dict]:
            try:
                resp = self._http().get(
                    "https://api.census.gov/data/timeseries/eits/bps",
                    params={
                        "get": "cell_value,error_data,time_slot_id",
                        "for": "state:*",
                        "time": "2025-12,2026-01,2026-02,2026-03,2026-04,2026-05",
                        "category_code": "RES",
                    },
                    headers={"User-Agent": "NEST-Advisors/1.0 sean.gilmore@ardanedgecapital.com"},
                    timeout=15,
                )
                resp.raise_for_status()
                rows = resp.json()
            except Exception:
                return []

            # First row is headers
            if not rows or len(rows) < 2:
                return []

            headers = rows[0]
            try:
                cv_idx = headers.index("cell_value")
                time_idx = headers.index("time")
                state_idx = headers.index("state")
            except (ValueError, IndexError):
                return []

            signals: list[dict] = []
            for row in rows[1:]:
                try:
                    state_code = str(row[state_idx])
                    period = str(row[time_idx])
                    count_raw = row[cv_idx]
                    permit_count = int(float(count_raw)) if count_raw not in (None, "", "N") else 0
                except (IndexError, ValueError, TypeError):
                    continue

                if states and state_code not in states:
                    continue

                signals.append({
                    "signal_type": "permit_surge",
                    "state": state_code,
                    "period": period,
                    "permit_count": permit_count,
                    "trigger_event": "permit_surge",
                    "raw_score": 0.0,
                })

            return signals

        return self._cached(cache_key, _fetch, ttl=1800)

    def scan_sector_comparables(self, sector: str, state: str = "",
                                min_amount: int = 0, max_amount: int = 0) -> list[dict]:
        """
        Ported from EagleEyeScanner.search_edgar_comparables() — sector-
        keyword EDGAR full-text search for comparable filings, now flowing
        through the same qualification/routing pipeline as every other
        signal instead of returning an unscored raw list.
        Returns list of raw signal dicts (raw_score=0.0).
        """
        search_term = _SECTOR_COMPARABLE_TERMS.get(sector, f'"{sector}"')
        hits = self._edgar_search({
            "q": search_term,
            "forms": "8-K,S-11,424B5",
            "dateRange": "custom",
            "startdt": "2023-01-01",
            "enddt": "2026-12-31",
        })

        results: list[dict] = []
        for hit in hits[:10]:
            base = self._parse_edgar_hit(hit)
            if state and base["state"] and base["state"] != state:
                continue
            results.append({
                "signal_type": "sector_comparable",
                "entity": base["entity"],
                "filing_date": base["filing_date"],
                "form_type": base["form_type"],
                "state": base["state"],
                "sector": sector,
                "trigger_event": "comparable_filing",
                "edgar_url": base["edgar_url"],
                "snippet": base["snippet"],
                "raw_score": 0.0,
            })

        return results

    def get_fred_market_context(self) -> dict:
        """
        Ported from EagleEyeScanner.get_fred_market_context() — live rate
        environment context from FRED (10yr treasury, 30yr mortgage, CRE
        delinquency rate). Cached 15 minutes. Returns {} without FRED_API_KEY
        or on any fetch error — same fail-open behavior as the original.
        """
        cache_key = "fred:market_context"
        cached = self._cache.get(cache_key)
        if cached and time.time() < cached[1]:
            return cached[0]

        api_key = os.environ.get("FRED_API_KEY", "")
        if not api_key:
            return {}

        def _fetch_series(series_id: str) -> float:
            resp = self._http().get(
                "https://api.stlouisfed.org/fred/series/observations",
                params={
                    "series_id": series_id, "api_key": api_key,
                    "sort_order": "desc", "limit": "1", "file_type": "json",
                },
                timeout=10,
            )
            resp.raise_for_status()
            obs = resp.json().get("observations", [])
            if not obs or obs[0].get("value", ".") == ".":
                raise ValueError(f"No usable observation for {series_id}")
            return float(obs[0]["value"])

        try:
            data = {
                "ten_yr_treasury": _fetch_series("DGS10"),
                "mortgage_30yr": _fetch_series("MORTGAGE30US"),
                "cre_delinquency": _fetch_series("DRCRLACBS"),
                "fetched_at": _utcnow(),
            }
        except Exception:
            return {}

        self._cache[cache_key] = (data, time.time() + 900)
        return data

    def scan_maturity_wall(self, market: str = None) -> dict:
        """
        Ported from EagleEyeScanner.scan_maturity_wall() — real reference
        figures on the construction/bridge loan maturity wall. Aggregate
        market context, not a per-entity signal, so it doesn't flow through
        qualify_signals()/route_signal() the way entity-level signals do.
        """
        wall = dict(_MATURITY_WALL_CONTEXT, distressed_signals=[], perm_ready_signals=[])
        market_key = (market or "").strip().lower()
        market_data = _MATURITY_WALL_MARKET_DATA.get(market_key) or (
            _MATURITY_WALL_MARKET_DATA.get("austin") if market_key in ("austin tx", "texas") else None
        )
        if market_data:
            wall.update(market_data)
        return wall

    # ==================================================================
    # NODE 2 — QUALIFICATION ENGINE
    # ==================================================================

    def qualify_signals(self, signals: list[dict]) -> list[dict]:
        """
        Score each signal and attach: nest_score, grade, qualified, desk,
        id, scored_at.
        """
        now = _utcnow()
        for signal in signals:
            stype = signal.get("signal_type", "")
            score = 0.0

            if stype == "ma_target":
                score = self._score_ma(signal)
                # Threshold lowered: EDGAR filings are real events.
                # Any filing that scores >= 0.3 (recent + source credit) qualifies.
                grade = "HOT" if score >= 0.7 else "WARM" if score >= 0.3 else "COLD"
                desk = "ma"

            elif stype == "cre_bond_issuance":
                score = self._score_cre(signal)
                # Threshold lowered: CRE bond filings are inherently noteworthy.
                grade = "HOT" if score >= 0.6 else "WARM" if score >= 0.3 else "COLD"
                desk = "cre"

            elif stype == "permit_surge":
                score = 0.5
                grade = "WARM"
                desk = "bond_desk"

            elif stype == "sector_comparable":
                score = self._score_sector_comparable(signal)
                grade = "HOT" if score >= 0.6 else "WARM" if score >= 0.3 else "COLD"
                desk = "cre"

            else:
                score = 0.0
                grade = "COLD"
                desk = "ma"

            signal["nest_score"] = round(min(score, 1.0), 4)
            signal["grade"] = grade
            signal["qualified"] = grade != "COLD"
            signal["desk"] = desk
            signal["id"] = str(uuid.uuid4())
            signal["scored_at"] = now

        return signals

    def _score_ma(self, signal: dict) -> float:
        score = 0.0
        text = (signal.get("snippet") or "") + " " + (signal.get("entity") or "")
        text_lower = text.lower()

        # Revenue $30M-$150M
        if _revenue_in_range(text):
            score += 0.4
        else:
            score += 0.2  # unknown → partial credit

        # EBITDA sub-$20M
        if _ebitda_sub_20m(text):
            score += 0.2

        # NAICS match
        naics_hint = signal.get("naics_hint", "")
        if any(naics_hint.startswith(n) for n in _TARGET_NAICS):
            score += 0.2

        # Recent filing (within 6 months = ~180 days)
        days = _days_since(signal.get("filing_date", ""))
        if 0 <= days <= 180:
            score += 0.1

        # Schedule 13D / activist interest
        if signal.get("trigger_event") == "schedule_13d" or "schedule 13d" in text_lower:
            score += 0.1

        return score

    def _score_cre(self, signal: dict) -> float:
        score = 0.0
        snippet = (signal.get("snippet") or "").lower()

        # S-11 form (REIT security)
        if signal.get("form_type", "") == "S-11":
            score += 0.3

        # Ground lease or land acquisition keyword
        trigger = signal.get("trigger_event", "")
        if trigger in ("ground_lease", "land_purchase") or (
            "ground lease" in snippet or "land acquisition" in snippet
        ):
            score += 0.3

        # Hot-state filter
        if signal.get("state", "") in _HOT_STATES:
            score += 0.2

        # Filing within 12 months = ~365 days
        days = _days_since(signal.get("filing_date", ""))
        if 0 <= days <= 365:
            score += 0.2

        return score

    def _score_sector_comparable(self, signal: dict) -> float:
        """Score a sector-comparable EDGAR filing (from scan_sector_comparables()).
        Real signal, same qualification treatment as ma_target/cre_bond_issuance —
        this data used to come back unscored from EagleEyeScanner."""
        score = 0.0

        # Larger/more formal disclosure forms carry more weight
        form = signal.get("form_type", "")
        if form == "S-11":  # REIT registration — real capital-raise intent
            score += 0.3
        elif form == "424B5":  # prospectus supplement — active offering
            score += 0.25
        elif form == "8-K":  # material event — could be anything, lower weight
            score += 0.15

        # Sector explicitly matched (not a generic fallback query)
        if signal.get("sector") in _SECTOR_COMPARABLE_TERMS:
            score += 0.2

        # Hot-state filter, same real markets as CRE scoring
        if signal.get("state", "") in _HOT_STATES:
            score += 0.2

        # Recent filing (within 12 months)
        days = _days_since(signal.get("filing_date", ""))
        if 0 <= days <= 365:
            score += 0.2

        return score

    # ==================================================================
    # NODE 3 — ACTION ROUTER
    # ==================================================================

    def route_signal(self, signal: dict) -> dict:
        """
        Attach routing metadata (action block) to a qualified signal.
        Mutates and returns the signal dict.
        """
        desk = signal.get("desk", "ma")
        grade = signal.get("grade", "COLD")

        agent_map = {
            "ma": "merlin",
            "bond_desk": "sterling",
            "cre": "eagleeye",
        }
        template_map = {
            "ma": "ma_intro",
            "bond_desk": "permit_follow",
            "cre": "cre_intro",
        }

        signal["action"] = {
            "desk": desk,
            "agent": agent_map.get(desk, "eagleeye"),
            "next_step": "Schedule intro call" if grade == "HOT" else "Add to watch list",
            "outreach_template": template_map.get(desk, "ma_intro"),
            "routed_at": _utcnow(),
        }
        return signal

    # ==================================================================
    # MAIN PIPELINE
    # ==================================================================

    def run_signal_pipeline(self, max_signals: int = 50, sectors: list[str] = None) -> dict:
        """
        Run full three-node pipeline.
        Returns a summary dict plus the list of qualified + routed signals.

        sectors: optional list of REVENUE_SECTOR_REGISTRY-style sector keys
        (e.g. ["senior_living", "healthcare"]) to also pull EagleEyeScanner-
        merged sector-comparable signals for, on top of the standard
        MA/CRE/permit scan. Backward compatible — omitted or empty means
        the original three sources only.
        """
        # ---- Node 1: Origination ----
        ma_signals = self.scan_edgar_ma_targets()
        cre_signals = self.scan_edgar_cre_events()
        permit_signals = self.scan_construction_permits()
        comparable_signals: list[dict] = []
        for sector in (sectors or []):
            comparable_signals.extend(self.scan_sector_comparables(sector))
        all_signals = (ma_signals + cre_signals + permit_signals + comparable_signals)[:max_signals]

        # ---- Node 2: Qualification ----
        qualified_all = self.qualify_signals(all_signals)

        # ---- Node 3: Action routing (only qualified) ----
        routed = [
            self.route_signal(s)
            for s in qualified_all
            if s.get("qualified")
        ]

        # Desk counts
        by_desk: dict[str, int] = {"ma": 0, "cre": 0, "bond_desk": 0}
        for s in routed:
            desk = s.get("desk", "")
            if desk in by_desk:
                by_desk[desk] += 1

        return {
            "run_at": _utcnow(),
            "total_scanned": len(all_signals),
            "qualified": len(routed),
            "hot": sum(1 for s in routed if s.get("grade") == "HOT"),
            "warm": sum(1 for s in routed if s.get("grade") == "WARM"),
            "by_desk": by_desk,
            "signals": routed,
        }
