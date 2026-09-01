"""M7 — the absolute solvency floor  (Good business?, part 3 — the HOARDING gate).

M7 is the top-level gate of the whole tool: *is this business worth hoarding at
all?* If it fails, every other reading — the dip, the recovery record, the
cheapness, the relative quality — is moot; a fallen, cheap, resilient stock
that fails M7 is just a cheap way to own a bad business. It is the one
deliberately ABSOLUTE measure (M4 handles all sector-relative performance), and
the email/buy gate. Three gates, each a soundness indicator:

  1. consistently profitable   — net income positive in ≥80% of the last decade
  2. generates operating cash   — operating cash flow positive in ≥80% of years
  3. debt serviceable           — can comfortably cover its interest

Clears the floor only if every applicable gate passes.

Near-universal, with targeted exceptions where a metric is a category error for
a sector's business model (allowed; adjusting the metric to fit a model is not
the same as lowering the bar for a weak sector):

  - Cash gate — skipped for **Financials**: a bank's/insurer's operating cash
    flow is lending/trading/float, i.e. balance-sheet activity, not cash
    generation; it false-fails sound banks (JPMorgan, Goldman) even cumulatively.
  - Solvency gate — measured as **interest coverage** (operating income ÷
    interest) for everyone, because it is immune to buybacks. Book equity is
    NOT usable: years of buybacks drive equity — and even retained earnings —
    negative at sound cash machines (AutoZone, Starbucks, Domino's, Altria),
    indistinguishable from loss-driven distress. For **Financials**, where
    interest is the business (coverage ≈ 2 is normal, not distress), solvency is
    instead a capital-adequacy floor (equity / assets). A company with no
    interest burden at all is solvent by definition.

Thresholds are fixed — calibrated once on the whole universe and validated on
an edge basket (sound names clear; balance-sheet blow-ups fail); a near-miss is
recorded, never a reason to move a bar. Reads only the local cache.
See docs/cellar-spec.md §4.7.
"""
from __future__ import annotations

import numpy as np

from cellar import facts
from cellar.quality import NI, OI, INT, OCF, EQ, WINDOW   # reuse the coverage-verified chains

MIN_YEARS = 5           # fewer than this → the floor can't be assessed
PROFIT_FRAC = 0.80      # net income positive in at least this share of years    [calibrated]
CASH_FRAC = 0.80        # operating cash positive in at least this share of years [calibrated]
COVERAGE_MIN = 2.0      # non-financials: median interest coverage at least this  [calibrated]
EQUITY_FLOOR = 0.05     # financials: equity / assets (capital adequacy) at least [calibrated]

FINANCIALS = "Financials"   # cash gate skipped; solvency by capital, not coverage


def m7(cik, sector: str) -> dict:
    """Solvency-floor reading for one company, or an unavailable marker."""
    g = facts.load_facts(cik)
    if not g:
        return {"available": False, "reason": "no_data"}
    ni = facts.annual_concept(g, NI)
    oi = facts.annual_concept(g, OI)
    ie = facts.annual_concept(g, INT)
    ocf = facts.annual_concept(g, OCF)
    eq = facts.annual_concept(g, EQ, instant=True)
    ast = facts.annual_concept(g, ["Assets"], instant=True)
    is_fin = sector == FINANCIALS

    ni_years = [y for y in ni if y in WINDOW]
    if len(ni_years) < MIN_YEARS:
        return {"available": False, "reason": "limited_data", "n_years": len(ni_years)}

    # Gate 1 — consistently profitable
    profit_frac = sum(1 for y in ni_years if ni[y] > 0) / len(ni_years)
    profit_ok = profit_frac >= PROFIT_FRAC

    # Gate 2 — generates operating cash (skipped for financials)
    ocf_years = [y for y in ocf if y in WINDOW]
    if not is_fin and ocf_years:
        cash_frac = sum(1 for y in ocf_years if ocf[y] > 0) / len(ocf_years)
        cash_ok = cash_frac >= CASH_FRAC
    else:
        cash_frac, cash_ok = None, True                 # n/a → cannot block

    # Gate 3 — debt serviceable. Coverage (buyback-immune) for most; capital
    # adequacy for financials; a company with no interest burden is solvent.
    eq_years = sorted(y for y in eq if y in WINDOW and y in ast and ast[y])
    equity_assets = (eq[eq_years[-1]] / ast[eq_years[-1]]) if eq_years else None
    cov = [oi[y] / ie[y] for y in oi if y in WINDOW and y in ie and ie[y] > 0]
    coverage = float(np.median(cov)) if cov else None
    if is_fin:
        solvent_ok = equity_assets is not None and equity_assets >= EQUITY_FLOOR
        solvency_basis = "capital"
    elif coverage is None:
        solvent_ok, solvency_basis = True, "no-debt"    # no interest burden = solvent
    else:
        solvent_ok, solvency_basis = coverage >= COVERAGE_MIN, "coverage"

    return {
        "available": True,
        "clears": profit_ok and cash_ok and solvent_ok,
        "profit_frac": round(profit_frac, 2), "profit_ok": profit_ok,
        "cash_frac": (round(cash_frac, 2) if cash_frac is not None else None), "cash_ok": cash_ok,
        "coverage": (round(coverage, 1) if coverage is not None else None),
        "equity_assets": (round(equity_assets, 3) if equity_assets is not None else None),
        "solvency_basis": solvency_basis, "solvent_ok": solvent_ok,
        "n_years": len(ni_years),
    }
