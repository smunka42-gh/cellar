"""Pull recent news headlines per company into data/news.json (Tenet 1: pull
once, cache). No LLM, no API key — the summaries are the publisher's own, via
yfinance (which we already use for prices). Cellar never authors or interprets
these; they are shown on the Mispriced? card as *recent coverage* beside the M5
filing signal, never as the stated cause of a fall.

Relevance filter (loose feeds tag tangential mentions — a Thiel bio names
PayPal, a market-wide video names every chip stock): keep only STORY items with
a non-empty publisher summary that actually name the company (ticker or a stem of
its name). Everything is a *published* field — no hand-curated lists.

Usage:
  pull_news.py              # full universe (slow; ~1 call/company)
  pull_news.py NKE INTC ... # just these tickers (merges into existing news.json)
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

import yfinance as yf

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
NEWS = DATA / "news.json"
PER_COMPANY = 3          # headlines kept per company
SUMMARY_CAP = 320        # chars stored per summary


def name_stem(name: str) -> str:
    """A matchable root of a company name: 'NIKE, Inc.' -> 'nike', 'Lilly (Eli)' -> 'lilly'."""
    head = re.split(r"[,(]", name)[0].strip().lower()
    return head.split()[0] if head.split() else ""


def clean(items, ticker: str, stem: str):
    out = []
    for it in items or []:
        c = it.get("content") or {}
        if c.get("contentType") != "STORY":
            continue
        summ = (c.get("summary") or "").strip()
        if not summ:
            continue
        title = (c.get("title") or "").strip()
        blob = f"{title} {summ}".lower()
        if ticker.lower() not in blob and (not stem or stem not in blob):
            continue
        url = (c.get("canonicalUrl") or {}).get("url") or (c.get("clickThroughUrl") or {}).get("url")
        if not url:
            continue
        out.append({
            "d": (c.get("pubDate") or "")[:10],
            "t": title,
            "s": summ[:SUMMARY_CAP],
            "u": url,
            "pub": ((c.get("provider") or {}).get("displayName") or "").strip(),
        })
        if len(out) >= PER_COMPANY:
            break
    return out


def main():
    rows = json.loads((DATA / "universe.json").read_text())
    name_by_t = {r["ticker"]: r["name"] for r in rows}
    args = [a.upper() for a in sys.argv[1:]]
    tickers = args or [r["ticker"] for r in rows]

    store = json.loads(NEWS.read_text()) if (args and NEWS.exists()) else {}

    t0, kept, empty, errs = time.time(), 0, 0, 0
    for i, tk in enumerate(tickers, 1):
        try:
            items = clean(yf.Ticker(tk).news, tk, name_stem(name_by_t.get(tk, "")))
            store[tk] = items
            if items:
                kept += 1
            else:
                empty += 1
        except Exception:
            errs += 1
            store.setdefault(tk, [])
        if i % 100 == 0:
            print(f"  {i}/{len(tickers)}  ({time.time()-t0:.0f}s)")

    NEWS.write_text(json.dumps(store))
    print(f"wrote {NEWS}  | tickers {len(tickers)} | with-news {kept} | "
          f"none {empty} | errors {errs} | {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
