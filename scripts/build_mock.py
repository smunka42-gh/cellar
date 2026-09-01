"""Build the interface mock: inject the computed results into the template.

Reads data/results_dip.json (the fast half of Tenet 1 — everything already
computed from the cache) and site/mock.template.html, and writes the
self-contained data/mock.html. No network, no recomputation.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def main() -> None:
    results = json.loads((DATA / "results_dip.json").read_text())
    template = (ROOT / "site" / "mock.template.html").read_text()

    # Merge cached news (publisher headlines) into each record, if pulled. Kept
    # separate from the measure pipeline so news can refresh without recomputing.
    news_file = DATA / "news.json"
    news = json.loads(news_file.read_text()) if news_file.exists() and news_file.stat().st_size else {}
    for r in results:
        r["news"] = news.get(r["ticker"], [])
    print(f"news attached for {sum(1 for r in results if r['news'])} companies")

    # Escape "<" so a company name can never close the <script> block early;
    # "<" is still valid JSON, so JSON.parse reads it back unchanged.
    payload = json.dumps(results).replace("<", "\\u003c")
    asof = dt.date.today().strftime("%d %b %Y")

    html = template.replace("__DATA__", payload).replace("__ASOF__", asof)
    out = DATA / "mock.html"
    out.write_text(html)
    print(f"wrote {out}  ({out.stat().st_size / 1e6:.1f} MB, "
          f"{len(results)} companies, as of {asof})")


if __name__ == "__main__":
    main()
