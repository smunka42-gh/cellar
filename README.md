# Cellar

Buy the dip — but only in high-quality companies that reliably climb back.

Cellar watches a fixed universe of US companies (the S&P Composite 1500,
minus REITs and non-SEC-filers — ~1,394 names) and, every day, finds the
ones whose share price has fallen to a level history says they recover from.
Each is answered in four plain questions:

- **Fell?** — has the price dropped, and freshly, versus its recent high?
- **Comes back?** — does it reliably recover, and how deep can you safely buy?
- **Cheap?** — is today a genuine discount, on its own price and on earnings?
- **Good business?** — is it strong, still-sound, and not broken?

The full design is in [`docs/cellar-spec.md`](docs/cellar-spec.md); the
principles are in [`docs/TENETS.md`](docs/TENETS.md).

## Status

- **The four questions — built and validated** on all ~1,394 companies,
  computed from the local cache in ~2 minutes:
  - **Fell? / Comes back? / Cheap?** (M1–M3, M6) — the price engine, on full
    price history.
  - **Good business?** — the **hoarding floor** (M7, the absolute
    profitable/cash-generative/solvent gate — *is it worth owning at all?*)
    and **relative quality** (M4, nine fundamental ratios ranked against GICS
    sub-industry peers over the last decade).
  - The remaining piece is the **mispricing test** (M5 — did fundamentals
    actually decline around the dip?), in progress.
- Each row carries a deterministic **verdict**, led by the hoarding gate and
  woven from the four answers — every clause pinned to a computed number.
- **Site and email** — a working interface mock exists; the live daily site
  and the email are deferred until the measures are complete and evaluated.

## How it runs

Everything follows one rule: **pull raw data once, compute from the cache.**

```bash
# 1. pull the raw data once (prices + SEC filings + market cap) into data/
SEC_USER_AGENT="cellar <you@example.com>" python scripts/pull.py all

# 2. compute all measures (M1-M7 + quality) for the whole universe (~2 min)
python scripts/run_dip.py            # -> data/results_dip.json

# 3. build the interface mock from those results
python scripts/build_mock.py         # -> data/mock.html
```

`SEC_USER_AGENT` is read from the environment (SEC requires a contact
address on every request); it is never hard-coded.

## Layout

```
cellar/      library — pure functions (universe, dip measures M1-M3, facts +
             fundamentals M4/M6/M7, split repair)
scripts/     pull.py (fetch + cache), run_dip.py (compute M1-M7), build_mock.py
site/        the interface (mock template)
docs/        cellar-spec.md (design), TENETS.md (principles)
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
