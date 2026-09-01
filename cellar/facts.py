"""Read the cached SEC companyfacts and pull point-in-time fundamental series.

Shared by every fundamentals-based measure (M6 now; M4/M5/M7 next). Reads
only from the local cache (data/facts/, data/splits/) — no network.

A subtlety this module gets right: per-share figures (EPS) must be
split-adjusted to line up with the split-adjusted prices, and the right
reference is the *filing date*, not the reporting period. A 10-K filed
*after* a split already reports post-split per-share figures, so adjusting
by the period end would double-count the split.
"""
from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
FACTS = ROOT / "data" / "facts"
SPLITS = ROOT / "data" / "splits"


def _date(s: str) -> _dt.date:
    return _dt.date.fromisoformat(s[:10])


def load_facts(cik) -> dict | None:
    """The us-gaap fact block for one filer, or None if not cached."""
    p = FACTS / f"CIK{int(cik):010d}.json"
    if not p.exists() or p.stat().st_size == 0:
        return None
    try:
        return json.loads(p.read_text()).get("facts", {}).get("us-gaap", {})
    except Exception:
        return None


def load_splits(ticker: str) -> list[tuple[_dt.date, float]]:
    """(date, factor) split events for a ticker, or [] if none."""
    p = SPLITS / f"{ticker}.csv"
    if not p.exists():
        return []
    df = pd.read_csv(p)
    col = [c for c in df.columns if c != "Date"][0]
    return [(_date(str(r["Date"])), float(r[col])) for _, r in df.iterrows()]


# The diluted-EPS concepts a filer might use. A company often migrates between
# them mid-history (Halliburton reported EarningsPerShareDiluted through 2019,
# then switched to the continuing-operations variant): we pick whichever gives
# the freshest coverage, not the first one listed, so the series never goes stale.
EPS_TAGS = [
    "EarningsPerShareDiluted",
    "IncomeLossFromContinuingOperationsPerDilutedShare",
    "EarningsPerShareBasicAndDiluted",
]

# When a company tags no annual diluted EPS at all, derive it the way the
# company itself defines it: net income ÷ diluted share count, from the same
# 10-K. This recovers filers like Hershey and Brady that report only the two
# ingredients. It deliberately does NOT try to rescue dual-class or partnership
# filers (Visa, Berkshire, KKR): their shares are tagged per-class or not at
# all, so a blended figure would be wrong — better an honest blank.
NI_TAG = "NetIncomeLoss"
DILUTED_SHARE_TAGS = [
    "WeightedAverageNumberOfDilutedSharesOutstanding",
    "WeightedAverageNumberOfShareOutstandingBasicAndDiluted",
]

_MIN_YEARS = 3   # below this a direct series is too thin to prefer over the fallback


def _annual_10k(node: dict | None) -> dict[int, tuple[_dt.date, float]]:
    """{fiscal_year: (filed_date, value)} for whole-year (350–380 day) 10-K
    facts, keyed on the reporting period's *end-date* year and keeping the
    earliest-filed report of each year.

    End-date keying matters: a single 10-K carries the current year plus two
    prior years as comparatives, and companyfacts stamps all three with the
    filing's own `fy`. Keying on `fy` would collapse those three into one and
    keep an arbitrary value; keying on the end date recovers every year, once
    each, in its original (earliest-filed, pre-restatement) form.
    """
    out: dict[int, tuple[_dt.date, float]] = {}
    if not node:
        return out
    rows = []
    for arr in node.get("units", {}).values():
        for e in arr:
            if not e.get("form", "").startswith("10-K"):
                continue
            try:
                end = _date(e["end"])
                span = (end - _date(e["start"])).days
            except Exception:
                continue
            if not (350 <= span <= 380):                       # whole year only
                continue
            if e.get("val") is None or e.get("filed") is None:
                continue
            rows.append((_date(e["filed"]), end.year, float(e["val"])))
    for filed, yr, val in sorted(rows):
        out.setdefault(yr, (filed, val))                       # original filing per year
    return out


def _rescale_shares(sh: dict[int, tuple[_dt.date, float]]) -> dict[int, tuple[_dt.date, float]]:
    """Snap share counts that a filing tagged in thousands up to actual units.

    Companyfacts sometimes labels a weighted-average share count "shares" while
    the value is really in thousands (Hershey's 2010–2011: 230,313 beside a
    2012 value of 228,337,000). The only realistic error is a factor of 1,000,
    so any year two orders of magnitude below the median is scaled up until it
    rejoins the pack.
    """
    if not sh:
        return sh
    vals = sorted(v for _, v in sh.values())
    med = vals[len(vals) // 2] or 1.0
    out = {}
    for yr, (f, v) in sh.items():
        while v and v < med / 100:
            v *= 1000
        out[yr] = (f, v)
    return out


def annual_eps(gaap: dict | None, splits: list, return_source: bool = False):
    """Annual diluted EPS, point-in-time, split-adjusted to today's share basis.

    Returns [(filed_date, fiscal_year, eps_adjusted), ...] sorted by year — one
    value per year, each divided by the splits that happened *after its filing
    date* so it lines up with the split-adjusted prices. Prefers the company's
    reported diluted EPS; where that tag is empty (or thinner than three years)
    it derives EPS from net income ÷ diluted shares out of the same filings.

    With return_source=True, also returns "reported" or "derived" so the caller
    can apply a sanity gate to figures it computed itself (the derived path can
    be fooled by up-C / non-controlling-interest structures, where total net
    income over only the public share class overstates EPS).
    """
    source = "reported"
    result = [] if not gaap else None
    if gaap is not None:
        # Among the diluted-EPS concepts this filer uses, take the one with the
        # freshest coverage (latest reporting year, then most years) and use it
        # alone — mixing concepts would put a discontinuity at the switch year.
        cands = [s for s in (_annual_10k(gaap[t]) for t in EPS_TAGS if t in gaap) if s]
        direct = max(cands, key=lambda s: (max(s), len(s))) if cands else {}
        series = direct
        if len(direct) < _MIN_YEARS:
            ni = _annual_10k(gaap.get(NI_TAG))
            sh = _rescale_shares(
                next((_annual_10k(gaap[t]) for t in DILUTED_SHARE_TAGS if t in gaap), {})
            )
            derived = {
                yr: (ni[yr][0], ni[yr][1] / sh[yr][1])
                for yr in ni if yr in sh and sh[yr][1]
            }
            if len(derived) > len(direct):
                series, source = derived, "derived"
        result = []
        for yr, (filed, val) in sorted(series.items()):
            cum = float(np.prod([sf for sd, sf in splits if sd > filed]) or 1.0)
            result.append((filed, yr, val / cum))
    return (result, source) if return_source else result
