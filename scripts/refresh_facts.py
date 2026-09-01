"""Daily fundamentals refresh: re-pull SEC companyfacts only for companies that
filed something in the last few days — so M4-M7 and M6 reflect fresh earnings
without re-downloading the whole 4.4 GB facts cache.

Reads data/filings.json (written by pull_filings.py — run it first) for each
company's newest filing date, and overwrites the companyfacts for those whose
newest filing is within the window. SEC processes XBRL a few days after a filing,
so the window is generous. Small daily set; leaves the rest of the cache untouched.

Usage (SEC contact address from the environment, never hard-coded):
  SEC_USER_AGENT="cellar <you@example.com>" python scripts/refresh_facts.py
"""
from __future__ import annotations

import json
import os
import time
from datetime import date, timedelta
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
UA = os.environ.get("SEC_USER_AGENT", "cellar (research)")
DAYS = 7          # re-pull facts for anything filed within this many days


def main():
    uni = {r["ticker"]: int(r["cik"]) for r in json.loads((DATA / "universe.json").read_text())}
    fj = DATA / "filings.json"
    if not fj.exists():
        print("no filings.json — run pull_filings.py first; skipping facts refresh")
        return
    filings = json.loads(fj.read_text())
    cutoff = (date.today() - timedelta(days=DAYS)).isoformat()
    recent = [t for t, items in filings.items()
              if items and items[0].get("d", "") >= cutoff and t in uni]

    fdir = DATA / "facts"; fdir.mkdir(parents=True, exist_ok=True)
    done = fail = 0
    for t in recent:
        cik = uni[t]
        url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
        try:
            r = requests.get(url, headers={"User-Agent": UA}, timeout=30)
            if r.status_code == 200:
                (fdir / f"CIK{cik:010d}.json").write_bytes(r.content); done += 1
            else:
                fail += 1
        except Exception:
            fail += 1
        time.sleep(0.13)
    print(f"facts refreshed for {done}/{len(recent)} recent filers (last {DAYS}d, {fail} failed)")


if __name__ == "__main__":
    main()
