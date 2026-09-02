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


def one(tk: str) -> dict:
    i = yf.Ticker(tk).info or {}
    rm = i.get("recommendationMean")
    return {
        "s": (i.get("longBusinessSummary") or "").strip()[:SUMMARY_CAP],
        "ind": (i.get("industry") or "").strip(),
        "rm": round(float(rm), 2) if rm else None,
        "rk": (i.get("recommendationKey") or "").strip(),
        "rn": i.get("numberOfAnalystOpinions") or None,
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
