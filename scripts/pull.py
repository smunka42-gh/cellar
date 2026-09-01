"""One-time (and repeatable) raw-data pull for Cellar.

Cellar's Tenet 1: pull raw data ONCE into a local cache, then compute every
score from that cache in seconds — never a fresh network pull per scoring
iteration. This module IS that pull. It is deliberately dumb: it fetches and
caches raw data and makes NO judgements about it. Every score and every
data-quality check lives elsewhere and reads only from data/.

Two free sources, no API key:
  - yfinance   : full daily price history (split/dividend-adjusted) + the
                 raw split events, one call per ticker.
  - SEC EDGAR  : `companyfacts` — EVERY XBRL fact a filer has ever reported,
                 each with its filing date and form — in ONE call per
                 company. Because it returns *all* tags, caching it now
                 future-proofs every fundamentals measure we design later:
                 we never re-pull to add a metric, we just read a different
                 field from the cached file.

Cache layout under data/ (gitignored — raw, large, reproducible):
  data/universe.json          [{ticker, cik, name, sector}, ...]  (REITs excluded)
  data/prices/<TICKER>.csv     date, close        (fully adjusted)
  data/splits/<TICKER>.csv     date, split        (only if any splits)
  data/facts/CIK##########.json  raw EDGAR companyfacts response

Resumable by construction: a company whose file already exists (and is
non-empty) is skipped, so an interrupted run is resumed by re-running the
same command. Nothing is judged or transformed here — that is the point.

Usage (SEC requires a contact address in the User-Agent, read from the
environment so it is never hard-coded into tracked code):
  SEC_USER_AGENT="cellar <you@example.com>" python scripts/pull.py universe
  SEC_USER_AGENT="cellar <you@example.com>" python scripts/pull.py prices
  SEC_USER_AGENT="cellar <you@example.com>" python scripts/pull.py facts
  SEC_USER_AGENT="cellar <you@example.com>" python scripts/pull.py all
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import requests

# Repo layout: this file is at cellar/scripts/pull.py, so the package
# `cellar` (universe.py etc.) is one directory up. Add that to the path so
# the pull can reuse the canonical universe loader rather than reinventing
# the constituent list.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
DATA = ROOT / "data"

from cellar import universe  # noqa: E402  (after sys.path juggling)

# SEC asks automated clients to identify themselves with a contact address
# and rate-limits to 10 requests/second. We stay well under that.
SEC_UA = os.environ.get("SEC_USER_AGENT", "cellar (research)")
EDGAR_SLEEP = 0.13          # ~7.5 req/s, comfortably under SEC's limit
YF_SLEEP = 0.15             # gentle pacing for yfinance


def log(msg: str) -> None:
    """Timestamped progress line (this script runs in the background, so its
    stdout is the only window into how far along it is)."""
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# ---------------------------------------------------------------------------
# Universe: the ~1,396 companies Cellar covers (S&P 1500 minus REITs), each
# joined to the SEC filer id (CIK) that companyfacts is keyed on.
# ---------------------------------------------------------------------------
def build_universe() -> list[dict]:
    """Fetch the canonical constituent list and attach each filer's CIK.

    `universe.constituents()` already keeps only the SEC's canonical ticker
    per filer, so every row it returns matches a CIK in company_tickers.json.
    We invert that same mapping (ticker -> CIK) to attach the id, and drop
    Real Estate because Cellar excludes REITs (they are judged on funds from
    operations, not the ratios everything else uses)."""
    log("building universe from S&P 1500 constituent lists ...")
    cik_to_ticker = universe._canonical_tickers()          # {cik: TICKER}
    ticker_to_cik = {t: c for c, t in cik_to_ticker.items()}
    rows = []
    for r in universe.constituents():                      # [{ticker,name,sector}]
        if r["sector"] == "Real Estate":                   # REITs excluded
            continue
        cik = ticker_to_cik.get(r["ticker"])
        if cik is None:                                    # not a canonical filer line
            continue
        rows.append({**r, "cik": cik})
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "universe.json").write_text(json.dumps(rows, indent=1))
    log(f"universe: {len(rows)} companies -> data/universe.json")
    return rows


def load_universe() -> list[dict]:
    """Read the cached universe, building it first if it isn't there yet."""
    f = DATA / "universe.json"
    if f.exists() and f.stat().st_size > 0:
        return json.loads(f.read_text())
    return build_universe()


# ---------------------------------------------------------------------------
# Prices: full daily history per ticker, split/dividend-adjusted (the series
# every price-based measure uses), plus the raw split events for later
# data-quality checks.
# ---------------------------------------------------------------------------
def pull_prices(rows: list[dict]) -> None:
    import yfinance as yf

    pdir = DATA / "prices"; pdir.mkdir(parents=True, exist_ok=True)
    sdir = DATA / "splits"; sdir.mkdir(parents=True, exist_ok=True)
    done = skip = fail = 0
    for i, r in enumerate(rows, 1):
        t = r["ticker"]
        out = pdir / f"{t}.csv"
        if out.exists() and out.stat().st_size > 0:        # resumable: already have it
            skip += 1
            continue
        try:
            tk = yf.Ticker(t)
            h = tk.history(period="max", auto_adjust=True)  # adjusted close
            if h.empty:
                fail += 1
                log(f"  no price data for {t}")
            else:
                close = h["Close"].dropna()
                close.index = close.index.tz_localize(None)  # drop tz for clean dates
                close.rename("close").to_csv(out)
                sp = tk.splits                               # raw split events
                if sp is not None and len(sp):
                    sp.index = sp.index.tz_localize(None)
                    sp.rename("split").to_csv(sdir / f"{t}.csv")
                done += 1
        except Exception as e:                               # network/parse hiccups: log, move on
            fail += 1
            log(f"  price error {t}: {type(e).__name__} {e}")
        time.sleep(YF_SLEEP)
        if i % 50 == 0:
            log(f"prices {i}/{len(rows)}  new={done} cached={skip} fail={fail}")
    log(f"PRICES DONE  new={done} cached={skip} fail={fail}")


# ---------------------------------------------------------------------------
# Fundamentals: one companyfacts file per company — every tag, every filing
# date, full history — cached raw so no future measure needs a re-pull.
# ---------------------------------------------------------------------------
def pull_facts(rows: list[dict]) -> None:
    fdir = DATA / "facts"; fdir.mkdir(parents=True, exist_ok=True)
    done = skip = fail = 0
    for i, r in enumerate(rows, 1):
        cik = int(r["cik"])
        out = fdir / f"CIK{cik:010d}.json"
        if out.exists() and out.stat().st_size > 0:        # resumable
            skip += 1
            continue
        url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
        try:
            resp = requests.get(url, headers={"User-Agent": SEC_UA}, timeout=30)
            if resp.status_code == 200:
                out.write_bytes(resp.content)               # store raw, judge nothing
                done += 1
            elif resp.status_code == 404:                    # filer has no XBRL facts
                fail += 1
                log(f"  no facts for {r['ticker']} (CIK {cik})")
            else:
                fail += 1
                log(f"  facts HTTP {resp.status_code} for {r['ticker']}")
        except Exception as e:
            fail += 1
            log(f"  facts error {r['ticker']}: {type(e).__name__} {e}")
        time.sleep(EDGAR_SLEEP)
        if i % 50 == 0:
            log(f"facts {i}/{len(rows)}  new={done} cached={skip} fail={fail}")
    log(f"FACTS DONE  new={done} cached={skip} fail={fail}")


# ---------------------------------------------------------------------------
# Market cap: current only, one light quote per ticker. Cached to a single
# JSON (ticker -> cap in dollars); resumable via the already-present keys.
# ---------------------------------------------------------------------------
def pull_mcap(rows: list[dict]) -> None:
    import yfinance as yf

    out = DATA / "market_cap.json"
    have = json.loads(out.read_text()) if out.exists() and out.stat().st_size else {}
    done = skip = fail = 0
    for i, r in enumerate(rows, 1):
        t = r["ticker"]
        if t in have and have[t] is not None:          # resumable
            skip += 1
            continue
        try:
            mc = yf.Ticker(t).fast_info.market_cap      # snake_case attribute
            have[t] = float(mc) if mc else None
            done += 1 if mc else 0
            if not mc:
                fail += 1
        except Exception:
            have[t] = None
            fail += 1
        time.sleep(0.05)
        if i % 100 == 0:
            out.write_text(json.dumps(have))            # checkpoint
            log(f"mcap {i}/{len(rows)}  new={done} cached={skip} missing={fail}")
    out.write_text(json.dumps(have))
    log(f"MCAP DONE  new={done} cached={skip} missing={fail}")


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    rows = load_universe()
    log(f"universe loaded: {len(rows)} companies  (mode={mode}, UA set={'SEC_USER_AGENT' in os.environ})")
    if mode in ("universe",):
        return
    if mode in ("prices", "all"):
        pull_prices(rows)
    if mode in ("facts", "all"):
        pull_facts(rows)
    if mode in ("mcap", "all"):
        pull_mcap(rows)


if __name__ == "__main__":
    main()
