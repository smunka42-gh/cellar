"""Daily incremental price + market-cap refresh (for the live site).

`pull.py` does the one-time bulk history pull and *skips* anything already
cached — correct for the first build, wrong for a daily site whose whole premise
is "today's price". This appends only the latest closes onto the cached series,
in BATCHED yfinance downloads (a handful of calls for the whole universe, far
more reliable at scale than 1,394 individual requests), and rescales each market
cap by its close ratio (shares are ~constant day-to-day, so cap ∝ price).

Splits are the one correctness trap: a split inside the window would put today's
close on a different basis than the cached historical high — a fake dip, the
exact silent-wrong answer the tool must avoid. So any ticker that shows a split
in the window is re-pulled in full (period=max), which re-adjusts its history.

Reads/writes only the local cache. Safe to re-run (idempotent: it appends only
dates newer than the last cached one).

Usage:
  refresh_prices.py              # whole universe
  refresh_prices.py MSFT NKE ... # just these (for testing)
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
PDIR = DATA / "prices"
CHUNK = 120           # tickers per batched download
WINDOW = "1mo"        # covers multi-day gaps, weekends, holidays


def last_row(csv: Path):
    """(last_date_str, last_close_float) from a prices CSV, or (None, None)."""
    try:
        line = csv.read_text().strip().splitlines()[-1]
        d, c = line.split(",")
        return d, float(c)
    except Exception:
        return None, None


def repull_full(t: str) -> bool:
    """Re-pull a ticker's whole adjusted history (used after a split)."""
    try:
        h = yf.Ticker(t).history(period="max", auto_adjust=True)["Close"].dropna()
        if h.empty:
            return False
        h.index = h.index.tz_localize(None)
        h.rename("close").to_csv(PDIR / f"{t}.csv")
        return True
    except Exception:
        return False


def main():
    rows = json.loads((DATA / "universe.json").read_text())
    args = [a.upper() for a in sys.argv[1:]]
    tickers = args or [r["ticker"] for r in rows]

    cap_file = DATA / "market_cap.json"
    caps = json.loads(cap_file.read_text()) if cap_file.exists() and cap_file.stat().st_size else {}

    appended = scaled = 0
    split_tickers, missing = [], 0
    t0 = time.time()
    for i in range(0, len(tickers), CHUNK):
        chunk = tickers[i:i + CHUNK]
        try:
            df = yf.download(chunk, period=WINDOW, auto_adjust=True, actions=True,
                             group_by="ticker", progress=False, threads=True)
        except Exception as e:
            print(f"  chunk {i} download error: {type(e).__name__}"); continue
        for t in chunk:
            try:
                sub = df[t] if len(chunk) > 1 else df
            except Exception:
                continue
            if sub is None or "Close" not in sub or sub["Close"].dropna().empty:
                continue
            # split in the window → re-pull full history (re-adjusts the past)
            if "Stock Splits" in sub and (sub["Stock Splits"].fillna(0) != 0).any():
                split_tickers.append(t); continue
            csv = PDIR / f"{t}.csv"
            if not csv.exists():
                missing += 1; continue
            ld, lc = last_row(csv)
            closes = sub["Close"].dropna()
            new = closes[closes.index > pd.Timestamp(ld)] if ld else closes
            if len(new):
                with csv.open("a") as f:
                    for d, v in new.items():
                        f.write(f"{d.date()},{float(v)}\n")
                appended += 1
                nc = float(new.iloc[-1])
                if caps.get(t) and lc:                       # cap ∝ price (shares ~constant)
                    caps[t] = caps[t] * (nc / lc); scaled += 1
        time.sleep(0.5)                                       # gentle between batches
        if (i // CHUNK) % 3 == 0:
            print(f"  {min(i+CHUNK,len(tickers))}/{len(tickers)}  appended={appended}  ({time.time()-t0:.0f}s)")

    for t in split_tickers:                                   # rare: full re-pull
        repull_full(t)

    cap_file.write_text(json.dumps(caps))
    print(f"PRICES REFRESHED  appended={appended} | split-repulled={len(split_tickers)} | "
          f"caps scaled={scaled} | no-cache={missing} | {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
