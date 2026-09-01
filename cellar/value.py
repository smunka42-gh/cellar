"""M6 — Cheap on earnings.

Today's earnings yield (earnings ÷ price), ranked against the stock's *own*
history, both recent and long. Cheap = a high yield percentile — today's
price buys more earnings than it usually does.

Why yield, not P/E: yield never explodes near zero earnings and a loss
becomes a clean negative that ranks at the bottom, so the series has no holes
or spikes. Why *current* (not a multi-year average): ranking today's yield
against the stock's own historical yields is self-consistent — each past
point used its own then-current earnings — so a growing company is not
penalised the way a lagging multi-year average would penalise it.

Companion to M3 (the price-side of "Cheap?"); see docs/cellar-spec.md §5 for
how the two combine. Reads only from the local cache — no network.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from cellar import facts

ROOT = Path(__file__).resolve().parent.parent
PRICES = ROOT / "data" / "prices"

MIN_EPS_YEARS = 3       # below this, no meaningful own-history to rank against
RECENT_YEARS = 5        # the "recent" window for the second reading
STALE_DAYS = 600        # a company files a 10-K yearly; a gap this long means we
                        # are missing its recent earnings — the reading is stale
# Sanity band for a *derived* current P/E (earnings we computed ourselves, not
# the company's reported EPS). A figure outside this is almost always a broken
# share basis or an up-C structure — we'd rather show nothing than a wrong P/E.
DERIVED_PE_BAND = (2.0, 300.0)


def m6(ticker: str, cik) -> dict:
    """Earnings-yield reading for one company, or an unavailable marker with a
    reason (thin history, no earnings series, etc.)."""
    eps, source = facts.annual_eps(
        facts.load_facts(cik), facts.load_splits(ticker), return_source=True
    )
    if len(eps) < MIN_EPS_YEARS:
        return {"available": False, "reason": "thin_history", "n_eps": len(eps)}

    df = pd.read_csv(PRICES / f"{ticker}.csv", parse_dates=["Date"])
    dates = df["Date"].dt.date.to_numpy()
    closes = df["close"].to_numpy()
    filed = [e[0] for e in eps]
    vals = [e[2] for e in eps]

    # Staleness: if the newest earnings we have predate the newest price by more
    # than a filing cycle, "current" EPS would really be years old — withhold.
    if (dates[-1] - filed[-1]).days > STALE_DAYS:
        return {"available": False, "reason": "stale_earnings", "n_eps": len(eps)}

    # Build the daily earnings-yield series, point-in-time: at each date use the
    # most recent annual EPS *known by then* (filed on or before that date).
    ys = []
    for dt_, c in zip(dates, closes):
        k = sum(1 for f in filed if f <= dt_)
        if k >= 1:
            ys.append(vals[k - 1] / c)
    if len(ys) < 252:
        return {"available": False, "reason": "series_short", "n_eps": len(eps)}

    y = np.array(ys)
    recent = y[-252 * RECENT_YEARS:] if len(y) > 252 * RECENT_YEARS else y
    cur_eps = vals[-1]
    price = float(closes[-1])
    # Guard figures we derived ourselves: a nonsensical valuation means the
    # share basis is broken (up-C float, wrong scale) — withhold rather than mislead.
    if source == "derived" and cur_eps > 0:
        pe = price / cur_eps
        if not (DERIVED_PE_BAND[0] <= pe <= DERIVED_PE_BAND[1]):
            return {"available": False, "reason": "derived_implausible", "n_eps": len(eps)}
    return {
        "available": True,
        "eps": round(cur_eps, 2),
        "pe": round(price / cur_eps, 1) if cur_eps > 0 else None,
        # percentile of today's yield within its own history: high = cheap
        "cheap_pctile_full": round(float((y < y[-1]).mean() * 100)),
        "cheap_pctile_recent": round(float((recent < recent[-1]).mean() * 100)),
        "negative_earnings": cur_eps <= 0,
        "n_eps": len(eps),
    }
