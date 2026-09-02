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

    # Merge cached SEC filings into each record, if pulled. Kept separate from the
    # measure pipeline so filings can refresh without recomputing.
    filings_file = DATA / "filings.json"
    filings = json.loads(filings_file.read_text()) if filings_file.exists() and filings_file.stat().st_size else {}
    for r in results:
        r["filings"] = filings.get(r["ticker"], [])
    print(f"filings attached for {sum(1 for r in results if r['filings'])} companies")

    # Company profile + analyst consensus (one .info pull, cached in info.json).
    info_file = DATA / "info.json"
    info = json.loads(info_file.read_text()) if info_file.exists() and info_file.stat().st_size else {}
    for r in results:
        r["info"] = info.get(r["ticker"], {})
    print(f"info attached for {sum(1 for r in results if r['info'])} companies")

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
