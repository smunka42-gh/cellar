"""The companies Cellar covers, and how they are classified.

Deliberately self-contained: the constituent list and every sector label
come from one public source, fetched at run time. Nothing is inherited
from an earlier project, and no scan file has to exist first.
"""
from __future__ import annotations

import io

import pandas as pd
import requests

# The S&P Composite 1500 is the large-, mid- and small-cap indices
# combined. S&P publishes them as three separate constituent lists, so
# three pages are read and concatenated. Their tables share a column
# layout, and the GICS sector labels are identical across all three,
# which is what lets one parser and one track rule serve all of them.
WIKI_PAGES = (
    "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
    "https://en.wikipedia.org/wiki/List_of_S%26P_400_companies",
    "https://en.wikipedia.org/wiki/List_of_S%26P_600_companies",
)

# Wikipedia asks that automated readers identify themselves and blocks
# some default library agents outright. Unlike the SEC's, this is a
# courtesy rather than a hard requirement, so a project string is enough
# and no contact address is embedded here.
WIKI_USER_AGENT = "cellar/0.1 (stock screener; contact via repository)"

# ONE RULE for dual-class companies: keep the ticker the SEC's own
# company_tickers.json names first for that filer, and drop the rest.
#
# The alternative was a hand-checked list, which is how this started —
# five entries, each argued individually, on the reasoning that the right
# line is not guessable from the letter (Alphabet's plain ticker is the
# non-voting retail line; for Fox and News Corp the "A" line is the
# widely traded one). That reasoning was sound and it does not scale: it
# needs a human decision every time the index changes, and by the time
# the universe reached 1,500 it had produced two rules that contradicted
# each other on Alphabet.
#
# A published field decided by someone else beats a judgement of ours,
# even a well-argued one. The cost of the switch is that Alphabet is now
# GOOGL rather than GOOG — the two track each other within a fraction of
# a percent, so no gate or price reading moves.
#
# Companies the SEC file does not carry at all (CWEN-A) need no entry:
# they never match a filer and drop out here on their own.
SEC_TICKERS = "https://www.sec.gov/files/company_tickers.json"
SEC_USER_AGENT_FALLBACK = "cellar (stock screener)"


def _canonical_tickers() -> dict[int, str]:
    """CIK -> the ticker the SEC lists first for that filer."""
    import os
    ua = os.environ.get("SEC_USER_AGENT", SEC_USER_AGENT_FALLBACK)
    raw = requests.get(SEC_TICKERS, headers={"User-Agent": ua}, timeout=30)
    raw.raise_for_status()
    first: dict[int, str] = {}
    for row in raw.json().values():
        first.setdefault(int(row["cik_str"]), row["ticker"].upper())
    return first


# Each page carries several tables — constituents, historical changes,
# and navigation boxes. The constituent table is the one that has BOTH a
# Symbol and a GICS Sector column AND a plausible row count. Picking "the
# largest table" instead once selected a 619-row table of index additions
# and removals in place of the 400 actual members.
_MIN_ROWS, _MAX_ROWS = 300, 700


def _constituents(url: str) -> list[dict]:
    """Parse one index page into [{ticker, name, sector}, ...].

    The page is fetched with requests rather than handed to pandas as a
    URL. pandas would download it through urllib, which on macOS relies
    on a system certificate store that a python.org install does not
    populate — so the fetch fails with CERTIFICATE_VERIFY_FAILED on a
    machine where everything else works. requests carries its own CA
    bundle, and this is also the only way to set a User-Agent.

    Each page carries several tables — constituents, historical changes,
    navigation boxes. The constituent one has BOTH a Symbol and a GICS
    Sector column AND a plausible row count. Picking "the largest table"
    instead once selected a 619-row table of index additions and
    removals in place of the 400 actual members.
    """
    html = requests.get(url, headers={"User-Agent": WIKI_USER_AGENT},
                        timeout=30)
    html.raise_for_status()
    for table in pd.read_html(io.StringIO(html.text)):
        cols = [str(c) for c in table.columns]
        if ("Symbol" in cols and "GICS Sector" in cols
                and _MIN_ROWS <= len(table) <= _MAX_ROWS):
            break
    else:
        raise RuntimeError(f"no constituent table found at {url}")
    # the same table also carries GICS Sub-Industry — the finest peer level
    sub_col = next((c for c in cols if "sub-industry" in c.lower() or "sub industry" in c.lower()), None)
    return [{"ticker": str(r["Symbol"]).strip().replace(".", "-"),
             "name": str(r["Security"]).strip(),
             "sector": str(r["GICS Sector"]).strip(),
             "sub_industry": (str(r[sub_col]).strip() if sub_col else "")}
            for _, r in table.iterrows()]


def constituents() -> list[dict]:
    """Return [{ticker, name, sector}, ...] for the S&P Composite 1500."""
    canonical = _canonical_tickers()
    by_cik = {t: c for c, t in canonical.items()}     # ticker -> cik
    seen_cik, seen_ticker, rows = set(), set(), []
    for url in WIKI_PAGES:
        for r in _constituents(url):
            t = r["ticker"]
            if t in seen_ticker:          # promoted between indices
                continue
            cik = by_cik.get(t)
            if cik is None:               # not the SEC's canonical line
                continue                  # for this filer, or unknown
            if cik in seen_cik:
                continue
            seen_cik.add(cik); seen_ticker.add(t)
            rows.append(r)
    if len(rows) < 1200:
        raise RuntimeError(f"only {len(rows)} constituents parsed; expected ~1500")
    return sorted(rows, key=lambda x: x["ticker"])


if __name__ == "__main__":
    import collections
    rows = constituents()
    print(f"{len(rows)} companies after de-duplication")
    by_sector = collections.Counter(r["sector"] for r in rows)
    for s, n in by_sector.most_common():
        print(f"   {s:24s} {n:3d}")
