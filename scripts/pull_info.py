"""Pull company profile + analyst consensus per company into data/info.json.

One yfinance `.info` call carries both: the business summary (for the profile at
the top of the detail panel) and the aggregate analyst rating (for the Analysts
column and its contrarian framing). Cached like every other pull; refreshed on
the daily job. Graceful per-ticker failure — a missing rating or summary just
shows as unavailable, never a fabricated value.

Analyst rating scale (yfinance recommendationMean): 1 = Strong Buy … 5 = Strong
Sell. Shown as context beside Cellar's own verdict, never a gate.

Usage:
  pull_info.py              # whole universe (~8 min)
  pull_info.py ADBE NKE ... # just these (merges into existing info.json)
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import yfinance as yf

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
INFO = DATA / "info.json"
SUMMARY_CAP = 900


def _key(rm):
    """Derive a rating label from the mean (yfinance's own recommendationKey is
    unreliable — often 'none' even when a breakdown exists)."""
    if rm is None:
        return ""
    return ("strong_buy" if rm < 1.5 else "buy" if rm < 2.5 else
            "hold" if rm < 3.5 else "sell" if rm < 4.5 else "strong_sell")


def one(tk: str) -> dict:
    t = yf.Ticker(tk)
    i = t.info or {}
    rm = rn = None
    # Primary: the analyst breakdown (strongBuy/buy/hold/sell/strongSell counts) —
    # far more complete than .info's recommendationMean (which is None even for
    # heavily-covered names like JPM/BAC). Compute the 1-5 mean from it.
    try:
        rs = t.recommendations
        if rs is not None and len(rs):
            row = rs.iloc[0]
            sb, b, h, s, ss = (int(row.get(k, 0) or 0) for k in
                               ("strongBuy", "buy", "hold", "sell", "strongSell"))
            tot = sb + b + h + s + ss
            if tot:
                rm = round((1*sb + 2*b + 3*h + 4*s + 5*ss) / tot, 2)
                rn = tot
    except Exception:
        pass
    if rm is None:                                   # fallback: .info's own field
        m = i.get("recommendationMean")
        if m:
            rm = round(float(m), 2)
            rn = i.get("numberOfAnalystOpinions")
    return {
        "s": (i.get("longBusinessSummary") or "").strip()[:SUMMARY_CAP],
        "ind": (i.get("industry") or "").strip(),
        "rm": rm,
        "rk": _key(rm),
        "rn": rn,
    }


def main():
    rows = json.loads((DATA / "universe.json").read_text())
    args = [a.upper() for a in sys.argv[1:]]
    tickers = args or [r["ticker"] for r in rows]
    store = json.loads(INFO.read_text()) if (args and INFO.exists()) else {}

    t0, ok_r, ok_s, errs = time.time(), 0, 0, 0
    for n, tk in enumerate(tickers, 1):
        try:
            d = one(tk)
            store[tk] = d
            ok_r += d["rm"] is not None
            ok_s += bool(d["s"])
        except Exception:
            errs += 1
            store.setdefault(tk, {"s": "", "ind": "", "rm": None, "rk": "", "rn": None})
        time.sleep(0.15)
        if n % 200 == 0:
            INFO.write_text(json.dumps(store))       # checkpoint
            print(f"  {n}/{len(tickers)}  ratings={ok_r} summaries={ok_s}  ({time.time()-t0:.0f}s)")

    INFO.write_text(json.dumps(store))
    print(f"wrote {INFO} | tickers {len(tickers)} | with-rating {ok_r} | "
          f"with-summary {ok_s} | errors {errs} | {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
