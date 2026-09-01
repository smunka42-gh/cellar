"""The price-side measurements — M1 (the dip), M2 (reliable recovery), and
M3 (cheap vs. its own price history).

Everything here reads ONLY from the local price cache (data/prices/<T>.csv)
— no network. This is the fast half of Cellar's Tenet 1: pull once, then
recompute every score from the cache in seconds. Definitions match the spec
(docs/cellar-spec.md §4.1–4.3).

Prices are already split/dividend adjusted (that is what the pull stored), so
the split-repair concern does not arise here.
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PRICES = ROOT / "data" / "prices"

# --- calibratable knobs (defaults; the runner reports distributions so we
# --- can set these deliberately from the data). See spec §12.
M1_HIGH_WINDOW_YEARS = 3     # today's dip is measured from the high in THIS
                             # trailing window, not the all-time high — a dip
                             # is a recent question, and a peak 5 years stale
                             # turns a long decline into a fake "dip".
M3_WINDOW_YEARS = 7          # length of the "usual price" trend window
M3_R2_CUTOFF = 0.60          # below this fit, use the range reading instead
M2_ANN_BAR = 0.10            # recover-to-high gain must annualize >= this
M2_MIN_OCCURRENCES = 5       # a depth needs this many past recoveries to trust
MIN_HISTORY_YEARS = 3        # below this, price measures are low-confidence


def load_prices(ticker: str) -> pd.Series:
    """Adjusted daily closes for one ticker, date-indexed."""
    df = pd.read_csv(PRICES / f"{ticker}.csv", parse_dates=["Date"], index_col="Date")
    return df["close"].dropna()


# ---------------------------------------------------------------------------
# Drawdown episodes: the shared engine behind M1 and M2.
# An episode runs from a record high, down to a trough, back up to reclaim
# that high. We keep, per CLOSED episode, the path of days spent below the
# high (enough to find when it first crossed any depth) and the reclaim date.
# The final, still-open drawdown (if any) is the CURRENT situation and is
# returned separately — never counted as evidence (spec §4.2).
# ---------------------------------------------------------------------------
def _episodes(dates: np.ndarray, closes: np.ndarray):
    episodes = []          # (peak_val, below_closes[], below_dates[], reclaim_date)
    peak = -1.0
    in_dip = False
    below_closes: list[float] = []
    below_dates: list = []
    for i in range(len(closes)):
        c = closes[i]
        if c >= peak:                      # a (new or matched) record high
            if in_dip:                     # ... which reclaims a prior high: episode closes
                episodes.append((peak, np.array(below_closes), below_dates, dates[i]))
            peak = c
            in_dip = False
            below_closes, below_dates = [], []
        else:                              # below the running high: inside a dip
            in_dip = True
            below_closes.append(c)
            below_dates.append(dates[i])
    open_dd = None
    if in_dip and below_closes:            # still under water at the end = today's dip
        open_dd = min(below_closes) / peak - 1.0
    return episodes, open_dd


def _recovery_days_at(peak, below_closes, below_dates, reclaim_date, depth):
    """Days from first crossing `depth` below the peak to reclaiming the high —
    i.e. the holding period if you had bought at that depth. None if this
    episode never reached that deep."""
    threshold = peak * (1.0 - depth)
    hit = np.where(below_closes <= threshold)[0]
    if len(hit) == 0:
        return None
    cross_date = below_dates[hit[0]]
    # dates here are numpy.datetime64; convert the delta to whole days.
    return int((reclaim_date - cross_date) / np.timedelta64(1, "D"))


def _annualized(depth: float, days: float) -> float:
    """Annualized return of recovering to the prior high from `depth`."""
    gain = 1.0 / (1.0 - depth)            # price multiple back to the high
    return gain ** (365.0 / max(days, 1)) - 1.0


def _recent_high(close: pd.Series, years=M1_HIGH_WINDOW_YEARS):
    """Highest close in the trailing `years`, and its date. The reference a
    dip is measured against — deliberately NOT the all-time high, so an
    ancient peak can't dress a multi-year decline up as a dip."""
    w = close[close.index >= close.index[-1] - pd.Timedelta(days=int(years * 365))]
    i = int(np.argmax(w.values))
    return float(w.values[i]), w.index[i]


# ---------------------------------------------------------------------------
# M1 — the dip (measured from the recent high, not the all-time high)
# ---------------------------------------------------------------------------
def m1(close: pd.Series) -> dict:
    hi, hi_dt = _recent_high(close)
    last = float(close.values[-1])
    return {
        "last": last,
        "high": hi,
        "high_date": hi_dt.date().isoformat(),
        "high_window_years": M1_HIGH_WINDOW_YEARS,
        "drawdown": last / hi - 1.0,                          # <= 0
        "days_since_high": (close.index[-1] - hi_dt).days,
    }


# ---------------------------------------------------------------------------
# M2 — reliable recovery: the deepest depth that (a) always recovers and
# (b) annualizes >= the bar, on enough occurrences.
# ---------------------------------------------------------------------------
def m2(close: pd.Series, ann_bar=M2_ANN_BAR, min_occ=M2_MIN_OCCURRENCES) -> dict:
    dates = close.index.to_numpy()
    episodes, open_dd = _episodes(dates, close.values)

    def profile(depth):
        days = [_recovery_days_at(pk, bc, bd, rd, depth) for (pk, bc, bd, rd) in episodes]
        days = [d for d in days if d is not None]
        return days

    reliable = None
    # scan deep -> shallow; first depth that clears both tests is the deepest one
    for d in np.round(np.arange(0.60, 0.099, -0.01), 2):
        days = profile(float(d))
        if len(days) >= min_occ:
            med = float(np.median(days))
            if _annualized(float(d), med) >= ann_bar:
                reliable = {
                    "depth": float(d),
                    "occurrences": len(days),
                    "median_recovery_days": med,
                    "annualized": _annualized(float(d), med),
                }
                break

    # at TODAY's depth: how often has it been this deep before, and how fast
    # back? "Today's depth" is where the price sits RIGHT NOW versus its
    # recent (trailing-window) high — the same number M1 reports — not the
    # trough of the current dip, which may be deeper if it has already bounced.
    hi, _ = _recent_high(close)
    cur = abs(float(close.values[-1]) / hi - 1.0)
    today = None
    if cur >= 0.05:                        # only meaningful once it has dipped
        days = profile(cur)
        today = {"depth": cur, "occurrences": len(days),
                 "median_recovery_days": float(np.median(days)) if days else None}
    return {"reliable": reliable, "today": today, "n_episodes": len(episodes)}


# ---------------------------------------------------------------------------
# M3 — cheap vs. its own price history: trend "usual price" where the price
# follows a steady path (good fit), range/room reading where it doesn't.
# ---------------------------------------------------------------------------
def m3(close: pd.Series, window_years=M3_WINDOW_YEARS, r2_cutoff=M3_R2_CUTOFF) -> dict:
    last_dt = close.index[-1]
    w = close[close.index >= last_dt - pd.Timedelta(days=int(window_years * 365))]
    today = float(w.iloc[-1])
    out = {"today": today}

    # trend reading: straight line through log(price)
    lv = np.log(w.values)
    x = np.arange(len(lv))
    b1, b0 = np.polyfit(x, lv, 1)
    fit = b0 + b1 * x
    resid = lv - fit
    sd = resid.std()
    r2 = 1.0 - (resid ** 2).sum() / ((lv - lv.mean()) ** 2).sum()
    out["r2"] = float(r2)
    out["usual_price"] = float(math.exp(fit[-1]))
    out["z"] = float(resid[-1] / sd) if sd else 0.0
    out["vs_usual"] = today / out["usual_price"] - 1.0
    out["slope_annual"] = float(math.exp(b1 * 252) - 1.0)   # trend's implied annual growth

    # range reading (always computed; it is what leads when the fit is poor):
    # how much of the last 3 years traded >= 10% / 20% above today.
    w3 = close[close.index >= last_dt - pd.Timedelta(days=3 * 365)]
    out["room_10"] = float((w3 >= today * 1.10).mean())
    out["room_20"] = float((w3 >= today * 1.20).mean())

    # Use the "usual price" trend ONLY when it fits well AND is not declining.
    # A falling trend line predicts more falling, so "below/above trend" says
    # nothing about cheap/expensive (this is what made crashed names read
    # "+77% vs usual"). Those fall to the range reading instead.
    out["mode"] = "trend" if (r2 >= r2_cutoff and b1 >= 0) else "range"
    return out


def _downsample(w: pd.Series, points: int) -> dict:
    idx = np.linspace(0, len(w) - 1, min(points, len(w))).astype(int)
    ser = w.iloc[idx]
    return {
        "from": ser.index[0].date().isoformat(),
        "to": ser.index[-1].date().isoformat(),
        "closes": [round(float(x), 2) for x in ser.values],
    }


def chart_windows(close: pd.Series) -> dict:
    """Downsampled price series per selectable timeline (1Y/3Y/5Y/MAX). Full
    daily history would bloat a self-contained page, so each window is thinned
    to ~100 points — dense enough for its span, small enough to embed."""
    out = {}
    for name, yrs, pts in (("1Y", 1, 90), ("3Y", 3, 90), ("5Y", 5, 90), ("MAX", None, 110)):
        w = close if yrs is None else close[close.index >= close.index[-1] - pd.Timedelta(days=int(yrs * 365))]
        if len(w) < 2:
            w = close
        out[name] = _downsample(w, pts)
    return out


def levels(close: pd.Series) -> dict:
    """Reference levels for the chart's optional Indicators overlay. These are
    context only — no Cellar score uses them (the 50/200-day averages were the
    old trend signal the proven-floor replaced)."""
    v = close.values
    w52 = close[close.index >= close.index[-1] - pd.Timedelta(days=365)]
    return {
        "sma50": round(float(v[-50:].mean()), 2) if len(v) >= 50 else None,
        "sma200": round(float(v[-200:].mean()), 2) if len(v) >= 200 else None,
        "w52_high": round(float(w52.max()), 2),
        "w52_low": round(float(w52.min()), 2),
        "w52_high_date": w52.idxmax().date().isoformat(),
        "w52_low_date": w52.idxmin().date().isoformat(),
    }


def all_measures(ticker: str) -> dict | None:
    """M1+M2+M3 for one ticker, or None if it has too little history to judge."""
    close = load_prices(ticker)
    if len(close) < 30:
        return None
    years = (close.index[-1] - close.index[0]).days / 365.25
    row = {"ticker": ticker, "history_years": round(years, 1),
           "thin_history": years < MIN_HISTORY_YEARS}
    row["m1"] = m1(close)
    row["m2"] = m2(close)
    row["m3"] = m3(close)
    row["chart"] = chart_windows(close)
    row["levels"] = levels(close)
    return row
