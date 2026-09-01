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

from cellar import facts
from cellar.quality import NI, REV

REV_DROP = -0.03    # revenue YoY below this = a real top-line decline    [calibrated]
NI_DROP_Q = -0.25   # quarterly net income YoY below this = declining      [calibrated]
NI_DROP_A = -0.20   # annual net income YoY below this = declining         [calibrated]
MIN_QUARTERS = 5    # fewer clean quarters than this → fall back to annual
FINANCIALS = "Financials"


def _r(x):
    return None if x is None else round(x, 3)


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
    return {"available": True, "basis": "annual", "status": "declining" if declining else "held_up",
            "as_of": str(latest), "rev_yoy": _r(rev_yoy), "ni_yoy": _r(ni_yoy)}


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
    return {
        "available": True, "basis": "quarterly",
        "status": "declining" if declining else "held_up",
        "as_of": latest.isoformat(),
        "rev_yoy": _r(rev_yoy), "ni_yoy": _r(ni_yoy),
    }
