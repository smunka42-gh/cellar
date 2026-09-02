"""CI-safe daily refresh of the price-based measures (M1-M3) + market cap.

Why this exists: SEC (data.sec.gov and www.sec.gov) blocks GitHub Actions'
datacenter IPs, so the SEC-derived measures — M4 quality, M5 mispricing, M6
cheap-on-earnings, M7 the hoarding floor — and the SEC filings CANNOT be pulled
in CI. They change slowly (quarterly filings), so they ship as a committed
snapshot (data/results_dip.json + data/filings.json), refreshed locally where SEC
is reachable. Prices, though, DO work in CI (yfinance), and they're the daily-
critical input (today's price = the dip). So the daily job recomputes only the
price-based measures from fresh prices and merges them onto the snapshot.

Loads the committed results_dip.json, recomputes M1/M2/M3 (dip.all_measures — no
SEC) from the freshly-pulled prices, updates market cap, and writes it back. The
fundamentals (m4/m5/m6/m7) and name/sector are preserved untouched; profiles and
filings are merged separately at build time.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from cellar import dip  # noqa: E402

DATA = ROOT / "data"


def main():
    results = json.loads((DATA / "results_dip.json").read_text())
    mc_file = DATA / "market_cap.json"
    mcaps = json.loads(mc_file.read_text()) if mc_file.exists() and mc_file.stat().st_size else {}

    updated = missing = 0
    for m in results:
        t = m["ticker"]
        try:
            fresh = dip.all_measures(t)          # M1-M3 + chart, from prices only
        except Exception:
            fresh = None
        if fresh:
            m.update(fresh)                      # refresh m1/m2/m3/chart/history; keep m4-m7/name/sector
            updated += 1
        else:
            missing += 1
        if mcaps.get(t) is not None:
            m["mcap"] = mcaps[t]

    (DATA / "results_dip.json").write_text(json.dumps(results))
    print(f"refreshed price measures for {updated}/{len(results)} (no fresh prices: {missing})")


if __name__ == "__main__":
    main()
