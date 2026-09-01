"""M5 — the mispricing test  (Good business?, part 2).

Was the fall backed by new fundamental evidence, or did the price drop while
the business held up? A dip with no deterioration behind it is the clean
mispricing — the ideal thing to hoard. A dip backed by genuinely declining
fundamentals is *earned* — the cheapness may be deserved. And because M7 (the
hoarding floor) judges the whole decade, M5 adds what the decade can't see:
is this sound business rolling over *right now*?

Reads recent **quarterly** filings (10-Q), year-over-year to kill seasonality —
the timely signal the annual 10-K can't give. Since filings are fresh (a median
of ~a month old), the axis is not "is there a filing" but **held up vs.
declining**. Financials, whose quarterly tagging is unreliable (a bank's
quarterly figures come and go under shifting concepts), fall back to **annual**
year-over-year. Reads only the local cache. See docs/cellar-spec.md §4.5.
"""
from __future__ import annotations

import statistics

from cellar import facts
from cellar.quality import NI, REV

REV_DROP = -0.03    # revenue YoY below this = a real top-line decline    [calibrated]
NI_DROP_Q = -0.25   # quarterly net income YoY below this = declining      [calibrated]
NI_DROP_A = -0.20   # annual net income YoY below this = declining         [calibrated]
MIN_QUARTERS = 5    # fewer clean quarters than this → fall back to annual
FINANCIALS = "Financials"

# One-off / low-confidence flag: the latest earnings YoY move is *unusually large
# for this company* — beyond OUTLIER_PCTILE of its own |YoY| history AND at least
# OUTLIER_FLOOR in magnitude. An outsized single-quarter swing is often a
# non-recurring item (a charge, writedown, tax) rather than a trend, so the M5
# read is surfaced as low-confidence. Never changes the status or the buy list —
# it only adds a caveat. Validated: flags INTC (-278% vs ±41% usual), TGT (+101%
# vs ±19%); leaves ordinary declines (NKE -35%, LULU -38%) and naturally-volatile
# names (CRM, NVDA) unflagged. See docs/data-hazards.md (H · non-recurring items).
OUTLIER_PCTILE = 0.85
OUTLIER_FLOOR = 0.40
OUTLIER_MIN_HIST = 5   # need this many prior moves to say what's "usual"


def _r(x):
    return None if x is None else round(x, 3)


def _all_yoy(series):
    """Every YoY move keyed by end — the distribution that says what a *normal*
    move is for this company. Handles both quarterly (date-keyed, ~365d apart)
    and annual (year-int-keyed) series. Values may be (filed, val) or val."""
    ends = sorted(series)
    getv = lambda v: v[1] if isinstance(v, tuple) else v
    is_year = bool(ends) and isinstance(ends[0], int)
    out = {}
    for e in ends:
        if is_year:
            p = e - 1 if (e - 1) in series else None
        else:
            prior = [q for q in ends if abs((e - q).days - 365) <= 45]
            p = min(prior, key=lambda x: abs((e - x).days - 365)) if prior else None
        if p is None:
            continue
        pv, ev = getv(series[p]), getv(series[e])
        if pv:
            out[e] = (ev - pv) / abs(pv)
    return out


def _outlier(all_moves, latest_end):
    """Is the latest YoY move unusually large vs this company's own history?
    Returns (flag, typical_abs) where typical_abs is the median |prior move|,
    for explaining the flag on the card. Conservative when history is thin."""
    if latest_end not in all_moves:
        return False, None
    lv = abs(all_moves[latest_end])
    hist = [abs(all_moves[e]) for e in all_moves if e != latest_end]
    if len(hist) < OUTLIER_MIN_HIST:
        return False, None
    p = sorted(hist)[int(OUTLIER_PCTILE * len(hist))]
    return (lv > p and lv > OUTLIER_FLOOR), round(statistics.median(hist), 3)


def _yoy(series, end, back=365, tol=45):
    """value at `end` ÷ value ~`back` days earlier − 1, or None. `series` maps
    end-date → (filed, val) or end-date → val."""
    if end not in series:
        return None
    prior = [e for e in series if abs((end - e).days - back) <= tol]
    if not prior:
        return None
    p = min(prior, key=lambda e: abs((end - e).days - back))
    getv = lambda v: v[1] if isinstance(v, tuple) else v
    pv, ev = getv(series[p]), getv(series[end])
    return None if not pv else (ev - pv) / abs(pv)


def _annual_fallback(g, reason):
    """Annual (10-K) YoY — for financials and for names with too little quarterly."""
    arev = facts.annual_concept(g, REV)
    ani = facts.annual_concept(g, NI)
    yrs = sorted(ani)
    if len(yrs) < 2:
        return {"available": False, "reason": reason or "thin_history"}
    latest, prior = yrs[-1], yrs[-1] - 1
    rev_yoy = (arev[latest] / arev[prior] - 1) if (latest in arev and prior in arev and arev[prior]) else None
    ni_yoy = (ani[latest] / ani[prior] - 1) if (prior in ani and ani[prior]) else None
    if rev_yoy is None and ni_yoy is None:
        return {"available": False, "reason": "no_yoy"}
    declining = (rev_yoy is not None and rev_yoy < REV_DROP) or (ni_yoy is not None and ni_yoy < NI_DROP_A)
    outlier, ni_typical = _outlier(_all_yoy(ani), latest)
    return {"available": True, "basis": "annual", "status": "declining" if declining else "held_up",
            "as_of": str(latest), "rev_yoy": _r(rev_yoy), "ni_yoy": _r(ni_yoy),
            "outlier": outlier, "ni_typical": ni_typical}


def m5(cik, sector: str) -> dict:
    """Mispricing reading for one company, or an unavailable marker."""
    g = facts.load_facts(cik)
    if not g:
        return {"available": False, "reason": "no_data"}

    # Financials: quarterly tagging is unreliable → annual basis.
    if sector == FINANCIALS:
        return _annual_fallback(g, None)

    qni = facts.quarterly_concept(g, NI)
    qrev = facts.quarterly_concept(g, REV)
    ni_ends = sorted(qni)
    if len(ni_ends) < MIN_QUARTERS:
        return _annual_fallback(g, "thin_quarterly")

    latest = ni_ends[-1]
    rev_yoy = _yoy(qrev, latest)
    ni_yoy = _yoy(qni, latest)
    if rev_yoy is None and ni_yoy is None:
        return _annual_fallback(g, "no_yoy")

    # declining = a real top-line decline, or a sharp latest-quarter profit fall
    declining = (rev_yoy is not None and rev_yoy < REV_DROP) or (ni_yoy is not None and ni_yoy < NI_DROP_Q)
    outlier, ni_typical = _outlier(_all_yoy(qni), latest)   # one-off / low-confidence flag
    return {
        "available": True, "basis": "quarterly",
        "status": "declining" if declining else "held_up",
        "as_of": latest.isoformat(),
        "rev_yoy": _r(rev_yoy), "ni_yoy": _r(ni_yoy),
        "outlier": outlier, "ni_typical": ni_typical,
    }
