"""Golden-set eval for M1-M7.

A curated, sector-spread, edge-case-covering set of companies, each with the
reading a human would independently expect — NOT copied from the current output,
so a passing check means the measure agrees with judgment, and a failing one is
a finding to investigate (the measure may be wrong, or the label may be).

Runs against the computed results (data/results_dip.json) and reports, per
measure, agree/total plus every disagreement with the actual value. Exits
non-zero if anything disagrees, so it can gate a build.

Each case carries only the assertions we're confident about, and an optional
`edge` tag naming the hazard it exercises (see docs/data-hazards.md).

Expected keys:
  m1_fell        Big | Some | Minimal        (drawdown tier from the recent high)
  m2_reliable    True | False                 (a reliable recovery depth exists)
  m4_tier        High | Solid | Mixed | Weak  (relative quality)
  m4_available   True | False
  m5             held_up | declining          (mispricing test)
  m6_available   True | False
  m6_dir         cheap | mid | expensive      (earnings-yield percentile vs own history)
  m7_clears      True | False                 (clears the hoarding floor)
  m7_available   True | False
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "data" / "results_dip.json"

# ── The golden set ────────────────────────────────────────────────────────────
GOLDEN = [
    # --- elite compounders: high quality, sound, healthy ---
    {"t": "MSFT", "expect": {"m4_tier": "High", "m7_clears": True, "m5": "held_up"}, "why": "elite software compounder"},
    {"t": "NVDA", "expect": {"m4_tier": "High", "m7_clears": True, "m1_fell": "Minimal"}, "why": "near highs, fortress fundamentals"},
    {"t": "COST", "expect": {"m4_tier": "High", "m7_clears": True, "m5": "held_up"}, "why": "consistent staples retailer"},
    {"t": "GOOGL", "expect": {"m7_clears": True, "m5": "held_up"}, "why": "dominant, cash-rich", "edge": "dual-class (voting)"},
    {"t": "V", "expect": {"m4_tier": "High", "m7_clears": True}, "why": "asset-light payment network", "edge": "dual-class → M6 per-class"},
    {"t": "MA", "expect": {"m4_tier": "High", "m7_clears": True}, "why": "asset-light payment network"},
    {"t": "UNH", "expect": {"m7_clears": True}, "why": "large, profitable insurer"},
    # LLY: elite returns (ROE 92nd pctile) but Solid not High — the consistency floor
    # catches a real balance-sheet soft spot (Debt/equity 17th, Current ratio 13th vs
    # pharma peers). Reputation says High; the evidence says Solid. (eval finding)
    {"t": "LLY", "expect": {"m4_tier": "Solid", "m7_clears": True}, "why": "high-return pharma, stretched balance sheet"},
    {"t": "ADBE", "expect": {"m4_tier": "High", "m7_clears": True}, "why": "high-margin software"},
    {"t": "SHW", "expect": {"m4_tier": "High", "m7_clears": True}, "why": "durable, high-return coatings franchise (Materials)"},

    # --- banks: financials handling (M7 capital basis, M5 annual) ---
    {"t": "JPM", "expect": {"m7_clears": True, "m4_tier": "High"}, "why": "best-run megabank", "edge": "financials: capital basis, GICS sub-industry"},
    {"t": "GS", "expect": {"m7_clears": True}, "why": "profitable, adequately capitalised", "edge": "financials: OCF meaningless"},
    {"t": "BLK", "expect": {"m7_available": False}, "why": "2024 holdco reorg → new CIK", "edge": "former-CIK, thin fundamentals"},

    # --- buyback machines: negative book equity but sound (M7 must clear on coverage) ---
    {"t": "AZO", "expect": {"m7_clears": True}, "why": "cash machine, negative equity from buybacks", "edge": "buyback → negative equity"},
    {"t": "MO", "expect": {"m7_clears": True}, "why": "high-coverage cash cow, negative equity", "edge": "buyback → negative equity"},
    {"t": "MCD", "expect": {"m7_clears": True}, "why": "franchise cash flows, negative equity", "edge": "buyback → negative equity"},
    {"t": "HD", "expect": {"m7_clears": True, "m4_tier": "High"}, "why": "high-return retailer"},

    # --- distress / cyclical wrecks: below the floor ---
    {"t": "AAL", "expect": {"m7_clears": False, "m5": "declining", "m2_reliable": False}, "why": "airline, negative equity, never reliably recovers", "edge": "negative equity (losses)"},
    {"t": "BA", "expect": {"m7_clears": False}, "why": "crisis, chronic losses", "edge": "profit + solvency fail"},
    {"t": "CCL", "expect": {"m7_clears": False}, "why": "COVID-wrecked cruise line"},
    {"t": "F", "expect": {"m4_tier": "Weak"}, "why": "low-return cyclical automaker"},

    # --- mispricing test (M5): fell on real deterioration ---
    # NKE: the value trap — cheap on its own earnings and down big, but declining.
    # Same cheap+fell signal as PYPL below, opposite verdict (M5 is the discriminator).
    {"t": "NKE", "expect": {"m5": "declining", "m1_fell": "Big", "m6_dir": "cheap"}, "why": "cheap and fallen, but earnings still sliding"},
    # INTC: the M5/M7 split in one name. M7 (long-run floor) CLEARS — profitable 80% of
    # the decade, coverage 22.7x — because the floor asks "durable business over a long
    # window", which Intel was. The current collapse (NI YoY -278%) is M5's job, and M5
    # correctly reads `declining`. M7 is not a recency gate; M5 is. (eval finding)
    {"t": "INTC", "expect": {"m5": "declining", "m7_clears": True}, "why": "long-run sound (floor), collapsing now (M5)", "edge": "M5/M7 division of labor"},
    {"t": "LULU", "expect": {"m5": "declining"}, "why": "sharp margin/earnings drop"},

    # --- mispricing test: fell/dipped but fundamentals fine (the good case) ---
    {"t": "CRM", "expect": {"m5": "held_up", "m7_clears": True}, "why": "growing while price lagged"},
    {"t": "META", "expect": {"m5": "held_up", "m7_clears": True}, "why": "revenue + profit strong"},

    # --- valuation (M6): richly valued on own history ---
    {"t": "AAPL", "expect": {"m6_available": True, "m6_dir": "expensive", "m7_clears": True}, "why": "richest end of its own P/E history"},

    # --- utilities: cash gate must use operating cash, not FCF ---
    {"t": "NEE", "expect": {"m7_clears": True}, "why": "sound regulated utility, capex-heavy", "edge": "utility: negative FCF but OCF+"},
    {"t": "DUK", "expect": {"m7_clears": True}, "why": "regulated utility", "edge": "utility"},

    # --- reorgs / spin-offs / new: honest can't-assess ---
    {"t": "XOM", "expect": {"m4_available": False, "m7_available": False}, "why": "reorg: history under former CIK", "edge": "former-CIK reorg"},
    {"t": "KVUE", "expect": {"m7_available": False}, "why": "2023 spin-off, thin history", "edge": "spin-off"},
    {"t": "GEV", "expect": {"m7_available": False}, "why": "2024 spin-off", "edge": "spin-off"},

    # --- dip tiers (M1) ---
    {"t": "WMT", "expect": {"m2_reliable": True}, "why": "blue chip, reliably recovers"},
    # PYPL: the textbook opportunity — fell big, recovers reliably, fundamentals held
    # up, cheap on its own earnings (P/E ~10 vs a history near 40x). Contrast with NKE.
    {"t": "PYPL", "expect": {"m5": "held_up", "m1_fell": "Big", "m6_dir": "cheap"}, "why": "fell big, sound, cheap on own history", "edge": "deep multi-year faller"},
]

DIR = {"cheap": (67, 101), "mid": (34, 67), "expensive": (0, 34)}


def fell_tier(m1):
    dd = abs(m1["drawdown"])
    return "Big" if dd >= 0.20 else "Some" if dd >= 0.08 else "Minimal"


def actual(rec, key):
    m1, m2, m4, m5, m6, m7 = (rec.get(k) or {} for k in ("m1", "m2", "m4", "m5", "m6", "m7"))
    if key == "m1_fell":      return fell_tier(rec["m1"])
    if key == "m2_reliable":  return m2.get("reliable") is not None
    if key == "m4_tier":      return m4.get("tier") if m4.get("available") else None
    if key == "m4_available": return bool(m4.get("available"))
    if key == "m5":           return m5.get("status") if m5.get("available") else None
    if key == "m6_available": return bool(m6.get("available"))
    if key == "m6_dir":
        if not m6.get("available"): return None
        p = m6.get("cheap_pctile_full")
        return next((d for d, (lo, hi) in DIR.items() if lo <= p < hi), None)
    if key == "m7_clears":    return m7.get("clears") if m7.get("available") else None
    if key == "m7_available": return bool(m7.get("available"))
    return "?"


def main():
    if not RESULTS.exists():
        sys.exit("run scripts/run_dip.py first (data/results_dip.json missing)")
    recs = {r["ticker"]: r for r in json.loads(RESULTS.read_text())}

    from collections import defaultdict
    tally = defaultdict(lambda: [0, 0])   # measure-key -> [agree, total]
    misses = []
    missing_tickers = []
    for case in GOLDEN:
        rec = recs.get(case["t"])
        if not rec:
            missing_tickers.append(case["t"]); continue
        for key, exp in case["expect"].items():
            got = actual(rec, key)
            tally[key][1] += 1
            if got == exp:
                tally[key][0] += 1
            else:
                misses.append((case["t"], key, exp, got, case.get("edge", "")))

    # ---- coverage: sectors and edge-case hazards the set exercises ----
    sectors = defaultdict(list)
    for case in GOLDEN:
        rec = recs.get(case["t"])
        sectors[rec["sector"] if rec else "?"].append(case["t"])
    edges = [(c["t"], c["edge"]) for c in GOLDEN if c.get("edge")]
    print(f"Golden-set eval — {len(GOLDEN)} companies, "
          f"{sum(t[1] for t in tally.values())} assertions")
    print(f"\nsector coverage ({len(sectors)} sectors):")
    for sec in sorted(sectors):
        print(f"  {sec:24} {' '.join(sectors[sec])}")
    print(f"\nedge-case coverage ({len(edges)} hazards, see docs/data-hazards.md):")
    for t, e in edges:
        print(f"  {t:6} {e}")
    print()
    print(f"{'assertion':14}{'agree':>10}")
    for key in sorted(tally):
        a, n = tally[key]
        print(f"  {key:14}{a:>4}/{n:<4}{'  ✓' if a == n else '  ✗'}")
    agree = sum(t[0] for t in tally.values()); total = sum(t[1] for t in tally.values())
    print(f"\n  TOTAL       {agree}/{total}  ({agree/total*100:.0f}%)")

    if misses:
        print("\nDisagreements (investigate — measure wrong, or label wrong):")
        for t, key, exp, got, edge in misses:
            print(f"  {t:6} {key:14} expected {str(exp):10} got {str(got):10}{'  ['+edge+']' if edge else ''}")
    if missing_tickers:
        print(f"\nnot in universe/results: {missing_tickers}")

    sys.exit(1 if misses else 0)


if __name__ == "__main__":
    main()
