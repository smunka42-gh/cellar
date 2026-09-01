"""Compute M1-M3 for the whole SEC-filing universe, from the local cache.

Writes data/results_dip.json and prints calibration distributions so the
M2/M3 knobs (spec §12) are set by looking at real data, not guessed. No
network — this is the fast half of Tenet 1.

The universe is the S&P 1500 minus REITs minus non-SEC-filers. The last cut
is applied MECHANICALLY here: a company is in only if its EDGAR companyfacts
was retrievable (data/facts/CIK##########.json exists). No hand-kept list.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from cellar import dip, value, quality, floor, mispricing  # noqa: E402

DATA = ROOT / "data"


def sec_filers() -> list[dict]:
    """Universe rows whose financials the SEC actually carries."""
    rows = json.loads((DATA / "universe.json").read_text())
    kept = []
    for r in rows:
        facts = DATA / "facts" / f"CIK{int(r['cik']):010d}.json"
        if facts.exists() and facts.stat().st_size > 0:
            kept.append(r)
    return rows, kept


def main():
    allrows, rows = sec_filers()
    print(f"universe: {len(allrows)} (S&P1500 - REITs) -> {len(rows)} SEC filers "
          f"(dropped {len(allrows) - len(rows)} non-filers)")

    mc_file = DATA / "market_cap.json"
    mcaps = json.loads(mc_file.read_text()) if mc_file.exists() and mc_file.stat().st_size else {}
    print(f"market caps loaded for {sum(1 for v in mcaps.values() if v)} companies")

    results, fails = [], []
    t0 = time.time()
    for i, r in enumerate(rows, 1):
        try:
            m = dip.all_measures(r["ticker"])
            if m is None:
                fails.append((r["ticker"], "too little data"))
                continue
            m["name"] = r["name"]; m["sector"] = r["sector"]
            m["mcap"] = mcaps.get(r["ticker"])
            m["m6"] = value.m6(r["ticker"], r["cik"])   # cheap on earnings
            m["m7"] = floor.m7(r["cik"], r["sector"])    # absolute solvency floor
            m["m5"] = mispricing.m5(r["cik"], r["sector"])  # mispricing test
            results.append(m)
        except Exception as e:
            fails.append((r["ticker"], f"{type(e).__name__}: {e}"))
        if i % 200 == 0:
            print(f"  {i}/{len(rows)} computed ({time.time()-t0:.0f}s)")
    # ---- M4 quality (cross-sectional: percentiles need every company's peers) ----
    tq = time.time()
    m4 = quality.all_quality(rows)
    for m in results:
        m["m4"] = m4.get(m["ticker"])
    print(f"\nM4 quality computed for {len(m4)} in {time.time()-tq:.0f}s")

    (DATA / "results_dip.json").write_text(json.dumps(results))
    print(f"\ncomputed {len(results)} in {time.time()-t0:.0f}s  | failures {len(fails)}")
    for t, why in fails[:10]:
        print(f"    fail {t}: {why}")

    # ---- M6 availability (surfaces reorg-filer / dual-class / thin-history gaps) ----
    from collections import Counter
    m6ok = sum(1 for x in results if x.get("m6", {}).get("available"))
    reasons = Counter(x["m6"].get("reason") for x in results if not x.get("m6", {}).get("available"))
    print(f"\nM6 (cheap on earnings): available {m6ok}/{len(results)}  | NA reasons: {dict(reasons)}")
    thin = [x["ticker"] for x in results if x.get("m6", {}).get("reason") == "thin_history"]
    print(f"  thin/NA sample: {thin[:25]}")

    # ---- calibration distributions ----
    def q(xs, ps=(10, 25, 50, 75, 90)):
        xs = np.array([x for x in xs if x is not None])
        return {p: round(float(np.percentile(xs, p)), 2) for p in ps} if len(xs) else {}

    thin = sum(1 for x in results if x["thin_history"])
    r2s = [x["m3"]["r2"] for x in results]
    trend = sum(1 for x in results if x["m3"]["mode"] == "trend")
    has_reliable = [x for x in results if x["m2"]["reliable"]]
    depths = [x["m2"]["reliable"]["depth"] for x in has_reliable]
    dd_now = [abs(x["m1"]["drawdown"]) for x in results]

    print("\n=== CALIBRATION ===")
    print(f"thin history (<{dip.MIN_HISTORY_YEARS}y): {thin} of {len(results)}")
    print(f"M3 fit R^2 percentiles: {q(r2s)}")
    print(f"M3 mode: trend {trend} ({trend/len(results)*100:.0f}%) | "
          f"range {len(results)-trend} (at R^2 cutoff {dip.M3_R2_CUTOFF})")
    print(f"M2 has a reliable depth: {len(has_reliable)} of {len(results)} "
          f"(bar {dip.M2_ANN_BAR*100:.0f}%/yr, min {dip.M2_MIN_OCCURRENCES} occ)")
    print(f"M2 reliable-depth percentiles: {q(depths)}")
    print(f"today's drawdown percentiles: {q(dd_now)}")

    # ---- sanity rows ----
    print("\n=== SANITY (known names) ===")
    idx = {x["ticker"]: x for x in results}
    for t in ("WMT", "NFLX", "ORCL", "AMZN", "MSFT", "COST", "KHC"):
        x = idx.get(t)
        if not x:
            print(f"  {t}: (not in results)"); continue
        m1, m2, m3 = x["m1"], x["m2"], x["m3"]
        rel = m2["reliable"]
        reltxt = (f"reliable to {rel['depth']*100:.0f}% ({rel['occurrences']}x, "
                  f"{rel['median_recovery_days']/30.4:.0f}mo)") if rel else "no reliable depth"
        if m3["mode"] == "trend":
            m3txt = f"trend usual ${m3['usual_price']:.0f} ({m3['vs_usual']*100:+.0f}%, z{m3['z']:+.1f}, R^2 {m3['r2']:.2f})"
        else:
            m3txt = f"range room+10%={m3['room_10']*100:.0f}% (R^2 {m3['r2']:.2f}, low fit)"
        print(f"  {t}: down {m1['drawdown']*100:.0f}% ({m1['days_since_high']}d) | {reltxt} | {m3txt}")


if __name__ == "__main__":
    main()
