"""Pull recent SEC filings per company into data/filings.json (Tenet 1: pull
once, cache). The authoritative "what has this company officially disclosed"
feed — from EDGAR, the same source every Cellar number traces to. No LLM, no key,
no relevance guessing: a filing is definitionally about the company.

"Recent" = the most recent periodic report (10-K or 10-Q, the last full financial
snapshot) plus every material event (8-K) and proxy (DEF 14A) filed on or since
it — "what's happened since we last saw the numbers." Material forms only: the
insider-trade (Form 3/4/5), ownership (SC 13*), and registration (S-*, 424B)
churn is excluded — a big bank files thousands of those a quarter.

Usage:
  pull_filings.py              # full universe (fast; SEC allows ~10 req/s)
  pull_filings.py NKE INTC ... # just these (merges into existing filings.json)
"""
from __future__ import annotations

import json
import ssl
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

import certifi

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
FILINGS = DATA / "filings.json"
CTX = ssl.create_default_context(cafile=certifi.where())

PERIODIC = {"10-K", "10-Q", "10-K/A", "10-Q/A"}
EVENTS = {"8-K", "8-K/A", "DEF 14A"}
MATERIAL = PERIODIC | EVENTS
CAP = 8               # most rows to keep
UA = "cellar-screener research tool"   # SEC asks for a descriptive UA; no personal info (public repo)

# 8-K item codes → plain language (see docs/data-hazards.md for why these matter)
ITEM = {
    "1.01": "Entered a material agreement", "1.02": "Ended a material agreement",
    "1.03": "Bankruptcy or receivership",
    "2.01": "Completed an acquisition/disposal", "2.02": "Quarterly earnings released",
    "2.03": "Took on new debt/obligation", "2.04": "Debt obligation triggered",
    "2.05": "Restructuring / exit costs", "2.06": "Material asset impairment",
    "3.01": "Delisting notice", "3.02": "Unregistered share sale", "3.03": "Shareholder-rights change",
    "4.01": "Changed auditor", "4.02": "Restatement — prior financials not reliable",
    "5.01": "Change in control", "5.02": "Leadership change (director/officer)",
    "5.03": "Charter/bylaw amendment", "5.07": "Shareholder vote results", "5.08": "Shareholder nominations",
    "7.01": "Reg FD disclosure", "8.01": "Other material event",
}
FORM_LABEL = {"10-K": "Annual report (10-K)", "10-Q": "Quarterly report (10-Q)",
              "DEF 14A": "Proxy statement"}


def label(form: str, items: str) -> str:
    """Human label for a filing row."""
    if form in FORM_LABEL:
        return FORM_LABEL[form]
    if form.endswith("/A"):
        base = FORM_LABEL.get(form[:-2], form[:-2])
        if form[:-2] == "8-K":
            base = _eight_k(items)
        return base + " (amended)"
    if form == "8-K":
        return _eight_k(items)
    return form


def _eight_k(items: str) -> str:
    codes = [c.strip() for c in (items or "").split(",") if c.strip() and c.strip() != "9.01"]
    labels = [ITEM.get(c, f"Item {c}") for c in codes]
    return " · ".join(dict.fromkeys(labels)) if labels else "Material event"


def edgar_url(cik: int, accession: str, doc: str) -> str:
    acc = accession.replace("-", "")
    if doc:
        return f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/{doc}"
    return f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=&dateb=&owner=include&count=40"


def recent_filings(cik: int) -> list[dict]:
    url = f"https://data.sec.gov/submissions/CIK{cik:010d}.json"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    d = json.loads(urllib.request.urlopen(req, timeout=25, context=CTX).read())
    rec = d["filings"]["recent"]
    forms, dates, items = rec["form"], rec["filingDate"], rec["items"]
    accs, docs = rec["accessionNumber"], rec["primaryDocument"]

    rows = [{"form": f, "d": dt, "items": it, "acc": a, "doc": doc}
            for f, dt, it, a, doc in zip(forms, dates, items, accs, docs)
            if f in MATERIAL]
    if not rows:
        return []
    periodic = [r["d"] for r in rows if r["form"] in PERIODIC]
    anchor = max(periodic) if periodic else None
    keep = [r for r in rows if (anchor is None or r["d"] >= anchor)]
    keep.sort(key=lambda r: r["d"], reverse=True)
    out = []
    for r in keep[:CAP]:
        out.append({"d": r["d"], "form": r["form"], "label": label(r["form"], r["items"]),
                    "u": edgar_url(cik, r["acc"], r["doc"])})
    return out


def main():
    rows = json.loads((DATA / "universe.json").read_text())
    cik_by_t = {r["ticker"]: int(r["cik"]) for r in rows}
    args = [a.upper() for a in sys.argv[1:]]
    tickers = args or [r["ticker"] for r in rows]
    store = json.loads(FILINGS.read_text()) if (args and FILINGS.exists()) else {}

    t0, kept, empty, errs = time.time(), 0, 0, 0
    for i, tk in enumerate(tickers, 1):
        try:
            store[tk] = recent_filings(cik_by_t[tk])
            kept += bool(store[tk]); empty += not store[tk]
        except Exception:
            errs += 1
            store.setdefault(tk, [])
        time.sleep(0.12)   # polite: SEC fair-access is ~10 req/s
        if i % 200 == 0:
            print(f"  {i}/{len(tickers)}  ({time.time()-t0:.0f}s)")

    FILINGS.write_text(json.dumps(store))
    print(f"wrote {FILINGS} | tickers {len(tickers)} | with-filings {kept} | "
          f"none {empty} | errors {errs} | {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
