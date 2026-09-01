"""M4 — Good business? (quality).

The foundation of the buy decision. A vetted set of fundamental ratios, each
turned into a percentile against sector peers, per year over the decade window,
then summarised per company as:

  - level        the median year's composite — its typical standing
  - consistency  the worst year's composite — a track record, not one good year

Ratios are grouped into five quality dimensions and combined with EQUAL WEIGHT
per dimension (so the three balance-sheet ratios don't outvote profitability).
A company is scored only on the ratios it actually reports; a missing ratio is
never defaulted, only omitted, and the coverage rides along so the gap is
visible on the site. Reads only the local cache — no network.

The ratio set, the fallback chains, and the ~decade window were all vetted on
the real pull (see the build log): chains are complete (every alias that would
add coverage was checked and rejected as a different concept), and coverage is
strong — the median company computes all nine ratios across all ten years.

See docs/cellar-spec.md §4.4.
"""
from __future__ import annotations

import numpy as np

from cellar import facts

WINDOW = list(range(2016, 2026))   # last ten fiscal years — a full cycle, comparable across firms
MIN_PEERS = 5                      # a peer cell (sub-industry, else sector) needs this many members to rank
MIN_YEARS = 3                      # fewer composite years than this → "limited data", no tier

# ── Fallback chains (verified complete on the pull) ────────────────────────────
NI  = ["NetIncomeLoss", "ProfitLoss", "NetIncomeLossAvailableToCommonStockholdersBasic"]
OI  = ["OperatingIncomeLoss",
       "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
       "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments",
       "IncomeLossFromContinuingOperationsBeforeIncomeTaxesDomesticAndForeign",
       "IncomeLossFromContinuingOperationsBeforeIncomeTaxesDomestic"]
REV = ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues",
       "RevenueFromContractWithCustomerIncludingAssessedTax", "SalesRevenueNet"]
OCF = ["NetCashProvidedByUsedInOperatingActivities", "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"]
CAPX = ["PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsToAcquireProductiveAssets", "PaymentsForCapitalImprovements"]
INT = ["InterestExpense", "InterestExpenseDebt", "InterestExpenseNonoperating", "InterestAndDebtExpense"]
EQ  = ["StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"]
LTD = ["LongTermDebtNoncurrent", "LongTermDebt", "LongTermDebtAndCapitalLeaseObligations"]

# ── The nine ratios, grouped into five equally-weighted quality dimensions ─────
DIMENSIONS = {
    "Returns":       ["ROE", "ROA"],
    "Margin":        ["Net margin"],
    "Cash":          ["FCF margin", "Cash conversion"],
    "Efficiency":    ["Asset turnover"],
    "Balance sheet": ["Debt/equity", "Interest coverage", "Current ratio"],
}
RATIOS = [r for rs in DIMENSIONS.values() for r in rs]
LOWER_BETTER = {"Debt/equity"}     # less leverage ranks higher; everything else higher = better


def _ratios(gaap: dict | None) -> dict[int, dict[str, float]] | dict:
    """{ratio: {year: value}} for one company across the window."""
    if not gaap:
        return {r: {} for r in RATIOS}
    ac = facts.annual_concept
    ni  = ac(gaap, NI);  rev = ac(gaap, REV); oi  = ac(gaap, OI)
    ocf = ac(gaap, OCF); cpx = ac(gaap, CAPX); ie = ac(gaap, INT)
    eq  = ac(gaap, EQ, True);  ast = ac(gaap, ["Assets"], True)
    ca  = ac(gaap, ["AssetsCurrent"], True); cl = ac(gaap, ["LiabilitiesCurrent"], True)
    ltd = ac(gaap, LTD, True)

    def div(a, b):   # ratio for the years both sides exist, in-window, denom non-zero
        return {y: a[y] / b[y] for y in a if y in WINDOW and y in b and b[y]}

    fcf = {y: ocf[y] - cpx[y] for y in ocf if y in cpx}   # free cash flow numerator
    return {
        "ROE": div(ni, eq),  "ROA": div(ni, ast),  "Net margin": div(ni, rev),
        "FCF margin": div(fcf, rev),  "Cash conversion": div(ocf, ni),
        "Asset turnover": div(rev, ast),  "Debt/equity": div(ltd, eq),
        "Interest coverage": div(oi, ie),  "Current ratio": div(ca, cl),
    }


def _tier(level: float, consistency: float) -> str:
    """Row-pill tier from the level (typical) and consistency (worst-year floor).

    Cutoffs calibrated on the real distribution: averaging five dimension
    percentiles compresses the composite toward the middle, so these sit lower
    than raw-percentile intuition would suggest (High ≈ top 12%). The
    consistency gate keeps a good *level* with an ugly worst year (3M, Intel)
    out of High — a track record, not one good year. `[calibrate]`
    """
    if level >= 65 and consistency >= 40:
        return "High"      # top-tier typically AND no severe down year
    if level >= 54:
        return "Solid"     # clearly above-average
    if level >= 42:
        return "Mixed"
    return "Weak"


def all_quality(rows: list[dict]) -> dict[str, dict]:
    """Compute M4 for the whole universe at once — percentiles are cross-sectional,
    so every company's reading needs its peers. `rows`: [{ticker, cik, sector}, …].
    Returns {ticker: m4_dict}."""
    # Pass 1 — extract each company's ratio series from the cache.
    series = {r["ticker"]: _ratios(facts.load_facts(r["cik"])) for r in rows}
    sector = {r["ticker"]: r["sector"] for r in rows}
    subind = {r["ticker"]: (r.get("sub_industry") or r["sector"]) for r in rows}
    grp_n: dict[tuple, int] = {}
    for r in rows:
        grp_n[("sec", r["sector"])] = grp_n.get(("sec", r["sector"]), 0) + 1
        grp_n[("sub", subind[r["ticker"]])] = grp_n.get(("sub", subind[r["ticker"]]), 0) + 1

    # Pass 2 — pool peer values for every (ratio, year) cell at BOTH peer levels:
    # the fine GICS sub-industry and the coarse sector fallback.
    pool_sub: dict[tuple, list] = {}
    pool_sec: dict[tuple, list] = {}
    for t, rs in series.items():
        for rt, ys in rs.items():
            for y, v in ys.items():
                pool_sub.setdefault((rt, y, subind[t]), []).append(v)
                pool_sec.setdefault((rt, y, sector[t]), []).append(v)

    # Pass 3 — per company: percentile each ratio-year, build the yearly composite,
    # then level (median year) and consistency (worst year).
    out: dict[str, dict] = {}
    for r in rows:
        t, sec, sub, rs = r["ticker"], r["sector"], subind[r["ticker"]], series[r["ticker"]]
        pct: dict[str, dict[int, float]] = {}     # ratio -> {year: percentile 0-100}
        used = {"sub": 0, "sec": 0}               # which peer level each cell ranked at
        for rt, ys in rs.items():
            lower_better = rt in LOWER_BETTER
            pr = {}
            for y, v in ys.items():
                # finest peer group with enough members that year, else the sector
                pool = pool_sub.get((rt, y, sub), [])
                lvl = "sub"
                if len(pool) < MIN_PEERS:
                    pool, lvl = pool_sec.get((rt, y, sec), []), "sec"
                    if len(pool) < MIN_PEERS:
                        continue
                rank = (sum(1 for x in pool if x >= v) if lower_better
                        else sum(1 for x in pool if x <= v))
                pr[y] = rank / len(pool) * 100.0
                used[lvl] += 1
            if pr:
                pct[rt] = pr
        # label the peer group by the level that carried most of the ranking
        peer_level = "sub" if used["sub"] >= used["sec"] else "sec"
        peer_group = sub if peer_level == "sub" else sec
        peer_size = grp_n[(peer_level, peer_group)]

        # yearly composite = mean within each available dimension, then mean across dimensions
        yearly = {}
        for y in WINDOW:
            dim_scores = []
            for dim, rlist in DIMENSIONS.items():
                vals = [pct[rt][y] for rt in rlist if rt in pct and y in pct[rt]]
                if vals:
                    dim_scores.append(float(np.mean(vals)))
            if dim_scores:
                yearly[y] = float(np.mean(dim_scores))

        n_years = len(yearly)
        n_dims = len({dim for dim in DIMENSIONS if any(rt in pct for rt in DIMENSIONS[dim])})
        if n_years < MIN_YEARS:
            out[t] = {"available": False, "reason": "limited_data",
                      "n_ratios": len(pct), "n_dims": n_dims, "n_years": n_years,
                      "peer_group": peer_group, "peer_n": peer_size}
            continue

        comp = list(yearly.values())
        level = float(np.median(comp))
        consistency = float(np.min(comp))
        # per-ratio standing (median year percentile) for the detail box
        ratio_level = {rt: round(float(np.median(list(pr.values())))) for rt, pr in pct.items()}
        out[t] = {
            "available": True,
            "level": round(level),
            "consistency": round(consistency),
            "tier": _tier(level, consistency),
            "ratio_level": ratio_level,
            "n_ratios": len(pct), "n_dims": n_dims, "n_years": n_years,
            "peer_group": peer_group, "peer_n": peer_size, "peer_level": peer_level,
        }
    return out
