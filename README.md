# Cellar

Buy the dip — but only in high-quality companies that reliably climb back.

**Live:** https://smunka42-gh.github.io/cellar/

Cellar watches a fixed universe of US companies (the S&P Composite 1500,
minus REITs and non-SEC-filers — ~1,394 names) and, every day, finds the
ones whose share price has fallen to a level history says they recover from.
Each is answered in plain questions:

- **Fell?** — has the price dropped, and freshly, versus its recent high?
- **Comes back?** — does it reliably recover, and how deep can you safely buy?
- **Cheap?** — is today a genuine discount, on its own price and on earnings?
- **Good business?** — is it strong, still-sound, and not broken?
- **Worth hoarding?** — the absolute gate beneath it all: is it worth owning at all?

The full design is in [`docs/cellar-spec.md`](docs/cellar-spec.md); the
principles are in [`docs/TENETS.md`](docs/TENETS.md); the corporate events that
can corrupt the numbers, and how each is handled, are catalogued in
[`docs/data-hazards.md`](docs/data-hazards.md).

## Status — all seven measures built and validated

Computed for every company from the local cache in ~2 minutes:

- **Fell? / Comes back? / Cheap?** — the price engine (M1–M3, M6), on full
  split-adjusted price history and the company's own earnings-yield history.
- **Good business?** — the **hoarding floor** (M7, the absolute
  profitable / cash-generative / solvent gate — *is it worth owning at all?*)
  and **relative quality** (M4, nine fundamental ratios ranked against GICS
  sub-industry peers over the last decade).
- **Mispriced?** — the **mispricing test** (M5: did fundamentals actually
  decline around the dip, or did the price fall while the business held up?),
  with a **low-confidence flag** when the latest earnings move is unusually
  large for the company (a likely one-off item).

Each row opens a deterministic **verdict**, led by the hoarding gate and woven
from every answer — every clause pinned to a computed number — plus six cards
(Worth hoarding? · Good business? · Comes back? · Cheap? · Fell? · Mispriced?)
and a **Recent SEC filings** card (the company's own material filings since its
last report, from EDGAR, with a link to full coverage on Yahoo Finance).

A labelled **eval harness** ([`scripts/eval.py`](scripts/eval.py)) checks every
measure against independent per-company judgment across all sectors and the
known data hazards.

### The Buy list

The default view is a high-conviction shortlist — a company is in only if **all
five** hold: it **clears the hoarding floor** (M7), **fell big** (M1), **reliably
recovers** from depths this deep (M2 Strong), is **cheap on both price and
earnings** (M3 × M6), and is a **high-quality** business (M4 High). Switch to
**All** to filter and search the whole universe.

## How it runs

Everything follows one rule: **pull raw data once, compute from the cache.**

```bash
# 1. pull the raw data (prices + SEC facts + market cap) into data/
SEC_USER_AGENT="cellar <you@example.com>" python scripts/pull.py all

# 2. pull recent SEC filings (the "Recent SEC filings" card)
python scripts/pull_filings.py

# 3. compute all measures (M1-M7 + quality) for the whole universe (~2 min)
python scripts/run_dip.py            # -> data/results_dip.json

# 4. build the site from those results
python scripts/build_mock.py         # -> data/mock.html

# (optional) run the eval harness
python scripts/eval.py
```

`SEC_USER_AGENT` is read from the environment (SEC requests a contact address);
it is never hard-coded.

The live site is deployed to GitHub Pages from the built `data/mock.html`.

## Layout

```
cellar/      library — pure functions (universe, dip measures M1-M3, facts +
             fundamentals M4/M6/M7, mispricing M5, split repair)
scripts/     pull.py + pull_filings.py (fetch + cache), run_dip.py (compute
             M1-M7), build_mock.py (build the site), eval.py (golden-set eval)
site/        the interface (mock template)
docs/        cellar-spec.md (design), TENETS.md (principles), data-hazards.md
tests/       validation
data/        local raw cache + computed results (gitignored, reproducible)
```

## Carried over

Two modules came from earlier work because they were already paid for:

- `cellar/universe.py` — S&P 1500 constituent loading, one ticker per filer
  via the SEC's canonical list.
- `cellar/splits.py` — repairs splits a price feed leaves unapplied.

## Credits

Index constituents from S&P Dow Jones Indices via public listings. Financial
and filing data from the US Securities and Exchange Commission's EDGAR
system. GICS is a joint product of S&P Dow Jones Indices and MSCI. Price and
market-cap data via the yfinance library.
