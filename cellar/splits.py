"""Price series helpers.

Split repair carried over from the previous project: `auto_adjust=True`
is supposed to make splits invisible and usually does, but a split from
the last few weeks can arrive unadjusted — and an unadjusted 2-for-1 is
a 50% "fall".
"""
from __future__ import annotations

import pandas as pd
import yfinance as yf

SPLIT_BREAK = 0.70          # a one-day ratio at or below this is suspicious
SPLIT_NEAR_DAYS = 45        # how far the recorded split may sit from the break
# Only RECENT history is scanned. Splits older than a year are adjusted
# correctly by the feed; the failure is specifically a recent one. This
# is not a nicety — fetch() returns five years, and over five years
# hundreds of companies have had a one-day fall past the threshold, each
# of which would cost a separate per-ticker request. Across 1,389
# companies that is ~25 candidates over one year against several hundred
# over five, and the extra ones cannot be the bug being fixed.
SPLIT_SCAN_BARS = 252       # one trading year


class PriceDataError(RuntimeError):
    """Raised when the fetched data is not fit to publish."""


def fetch(tickers: list[str], period: str = "5y") -> dict[str, pd.DataFrame]:
    """Download daily bars for many tickers in one request.

    `auto_adjust=True` is the load-bearing argument — see the module
    docstring. `period` defaults to FIVE years: the 3-year percentile
    needs 756 bars, and two years cannot supply them. The extra history
    costs nothing — it is the same single request.
    """
    raw = yf.download(tickers, period=period, interval="1d",
                      group_by="ticker", auto_adjust=True,
                      threads=True, progress=False)

    out: dict[str, pd.DataFrame] = {}
    for t in tickers:
        try:
            frame = raw[t][["Close", "Volume"]].dropna()
        except (KeyError, TypeError):
            continue                       # no data returned for this one
        if not frame.empty:
            out[t] = frame
    return out


def repair_splits(frames: dict[str, pd.DataFrame]) -> tuple[dict, list]:
    """Back-adjust history the feed left unadjusted for a split.

    Returns (repairs, rejected).

    **This acts only where a split is actually on record.** A large
    one-day fall with no recorded split is left alone and scored as the
    real fall it almost certainly is — flattening those would erase
    exactly the signal this page exists to find. Checked on the four
    candidates of 31 Aug 2026: the one with a recorded split (IESC) saw
    volume barely move and dollar volume FALL, the signature of a split;
    the three without (VRRM, PRIM, UTI) spiked volume 2.5-7x, which is
    people trading news. The split record and the volume agreed.

    Where a split IS on record, two outcomes:

    * ONE break. The feed did not apply a recent split. Divide
      everything before the break by the factor, then re-check — a
      repair that leaves a break behind is rejected rather than
      published on a number nothing verified.
    * MANY breaks. On 31 Aug 2026 MNST arrived with FOUR, its days
      alternating between the two bases — 99.94, 97.50, 47.72, 47.23,
      47.83, 93.56. That is a corrupt series, not an unapplied split,
      and dividing "everything before the last break" would halve the
      days that were already right. Rejected.
    """
    repairs, rejected = {}, []
    # Anything with a split-shaped break MUST end up in one of the three
    # buckets below. Falling through silently is the failure mode.
    for t, f in frames.items():
        close = f["Close"]
        recent = close.tail(SPLIT_SCAN_BARS + 1)
        breaks = (recent / recent.shift(1)).pipe(lambda r: r[r <= SPLIT_BREAK])
        if breaks.empty:
            continue
        try:
            splits = yf.Ticker(t).splits
        except Exception as exc:
            # NEVER swallow this. A failed lookup here is indistinguishable
            # from "no split on record", and treating it as the latter
            # publishes the false 50% fall this function exists to stop.
            # Yahoo rate-limits these calls, and on 31 Aug 2026 that
            # silently disarmed the whole check while the run reported
            # "no unadjusted splits found".
            rejected.append((t, f"split record unreadable ({type(exc).__name__})"))
            continue
        recorded = [(d.date(), float(v)) for d, v in splits.items()
                    if float(v) > 1.01
                    and any(abs((d.date() - w.date()).days) <= SPLIT_NEAR_DAYS
                            for w in breaks.index)]
        if not recorded:
            continue                       # a real fall, not our business
        if len(breaks) > 1:
            rejected.append((t, f"{len(breaks)} split-shaped breaks around a "
                                f"recorded split — series is on mixed bases"))
            continue
        when, drop = breaks.index[0], float(breaks.iloc[0])
        factor = max(v for _, v in recorded)
        f.loc[f.index < when, "Close"] = f.loc[f.index < when, "Close"] / factor
        again = f["Close"] / f["Close"].shift(1)
        if (again <= SPLIT_BREAK).any():
            rejected.append((t, f"still broken after dividing by {factor:g}"))
            continue
        repairs[t] = (f"divided pre-{when.date()} closes by {factor:g} "
                      f"(one-day {100*(drop-1):.1f}%)")
    return repairs, rejected


