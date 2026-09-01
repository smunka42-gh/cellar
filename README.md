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

- **Price engine (Fell? / Comes back? / Cheap?)** — built and validated on
  full price history for all ~1,394 companies. Computed from a local cache
  in seconds.
- **Good business? (quality, fundamentals, solvency floor)** — designed, not
  yet built. This is the next piece.
- **Site and email** — a working interface mock exists; the live daily site
  and the email are not yet built.

## How it runs

Everything follows one rule: **pull raw data once, compute from the cache.**

```bash
# 1. pull the raw data once (prices + SEC filings + market cap) into data/
SEC_USER_AGENT="cellar <you@example.com>" python scripts/pull.py all

# 2. compute the price-engine scores for the whole universe (seconds)
python scripts/run_dip.py            # -> data/results_dip.json
```

`SEC_USER_AGENT` is read from the environment (SEC requires a contact
address on every request); it is never hard-coded.

## Layout

```
cellar/      library — pure functions (universe, dip measures, split repair)
scripts/     pull.py (fetch + cache), run_dip.py (compute the price engine)
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
