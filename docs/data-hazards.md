# Data hazards — the corporate events that break the numbers

Every measurement in Cellar is a computation over raw SEC filings and price
history, and a handful of ordinary corporate events can quietly corrupt those
inputs — producing a number that looks fine and is wrong. That silent-wrong
answer is the failure mode the whole tool most has to avoid.

This is the catalogue of those events: what each one does, which measurements
(M1–M7) it threatens, how it shows up, and how Cellar handles it today —
**guarded** (a mechanism neutralises it), **surfaced** (we can't fix it, so we
show it honestly as *can't assess* / *limited data* rather than guess), or
**open** (a known residual, tracked for the rigor phase). It doubles as the
seed list for the edge-case evals: every row is a case the golden set must
cover.

Measurement key: **M1** dip · **M2** reliable recovery · **M3** cheap-vs-price ·
**M4** quality vs peers · **M5** mispricing test · **M6** cheap-on-earnings ·
**M7** the hoarding floor.

---

## A · Per-share distortions

A per-share figure (EPS) and a total figure (net income, shares) diverge
whenever the share count changes. Prices are split-adjusted by the feed; the
filings are not — so the two must be reconciled by hand.

| Event | What it does | At risk | Handling |
|---|---|---|---|
| **Stock split / reverse split** | Multiplies shares, divides per-share figures; the price feed is already adjusted, the 10-K is not | M6 | **Guarded** — EPS is split-adjusted by *filing date* (a 10-K filed after a split already reports post-split, so adjusting by period-end would double-count). Validated to the cent on Walmart 3:1 and Apple 7:1×4:1. |
| **Buybacks** | Shrink share count and **drive book equity — and even retained earnings — negative** at cash machines (AutoZone, Starbucks, Domino's, Altria) | M7, M4, M6 | **Guarded** — M7 solvency uses **interest coverage, not book equity** (buyback-immune); retained-earnings sign was tested and rejected (buybacks flip it too). M4/M6 read the effect (higher ROE, higher EPS) as real, which it is. |
| **Dilution / secondary issuance** | Grows the share count; per-share figures fall even at flat totals | M6 | **Guarded** — M6 uses the diluted-share count as filed each period; the yield ranks against the company's own history on the same basis. |
| **Dual-class shares** | EPS and share counts are reported per class, often behind an XBRL dimension `companyfacts` omits (Visa, Berkshire, Constellation) | M6 | **Surfaced / partially guarded** — falls back to net income ÷ diluted shares where the direct tag is empty; where even that is per-class-dimensioned, reads *no earnings reading*. |
| **Up-C / partnership structures** | Total net income over the public share class alone inflates EPS (Shift4); per-unit not per-share (KKR, Ares) | M6 | **Guarded** — a valuation-sanity band rejects the implausible P/E; reads *no earnings reading* rather than a wrong number. |

## B · Identity and continuity breaks

The company you see today may not be the SEC registrant that filed its history.

| Event | What it does | At risk | Handling |
|---|---|---|---|
| **Holding-company reorg / new CIK** | A 2024–25 wave (Exxon, BlackRock, Ferguson, Six Flags, Pinnacle, Viper, Uniti) created a **new SEC filer**; the long history sits under the old CIK, the new one carries only recent comparatives | M4, M5, M6, M7 | **Surfaced → open.** Reads *can't assess / limited data* today (honest). The verified former-CIK merge is a tracked rigor-phase task — done per name against EDGAR, never a fragile auto-match. |
| **Spin-off** | A new entity with little or no filing history (Kenvue, GE Vernova, Solventum, Veralto) | M2–M7 | **Surfaced** — *limited data* until it has filed enough; nothing to merge (it is genuinely new). |
| **Merger / acquisition** | A combined entity with two predecessors and a discontinuous history (Paramount Skydance, Smurfit Westrock); prior-period comparatives may be one predecessor only | M2, M3, M5 | **Surfaced → open.** Long price history can be inherited/synthetic; fundamentals read *can't assess* where the new CIK is thin. Comparability of pre-merger history is a known residual. |
| **Name change** | Same CIK, new name/ticker | — | **Guarded** — keyed on CIK, not name; `companyfacts` carries `formerNames`. |

## C · Period and timing issues

| Event | What it does | At risk | Handling |
|---|---|---|---|
| **Part-year / transition filing (10-KT)** | A stub fiscal period (e.g. 152 days) tagged as a year | M4, M6, M7 | **Guarded** — annual extraction keeps only 350–380-day periods; quarterly keeps 80–100. |
| **Quarter mistagged `fp=FY`** | A 10-K carries its quarters too; a quarter can masquerade as the year | M4, M6, M7 | **Guarded** — the day-span filter (not the `fp` label) decides what is a year. |
| **Fiscal-year-end change** | A transition period; YoY comparability breaks around it | M5 | **Partially guarded** — YoY matches on ~365-day spacing (±45d); a shifted year with no clean comparable reads *no timely read*. **Open**: a company mid-shift can miss a period. |
| **52/53-week fiscal calendar** | Years run 364/371 days, quarters 91/98 | M4–M7 | **Guarded** — the 350–380 / 80–100 windows admit them. |
| **Restatement** | Prior periods refiled with new numbers | M4, M6 | **Guarded (point-in-time)** — the **earliest-filed** figure per fiscal year is kept (as originally reported), so a later restatement doesn't rewrite history. |
| **Fiscal year not yet filed** | The latest 10-K lands 2–12 months after year-end; a stale latest figure | M6 | **Guarded** — a staleness cutoff (latest filing > ~600 days before the latest price) marks the earnings read stale rather than ranking a years-old number. |

## D · Tag and concept issues

| Event | What it does | At risk | Handling |
|---|---|---|---|
| **Concept migration** | A company switches XBRL tags mid-history — diluted EPS → continuing-ops EPS (Halliburton), or revenue → ASC-606 revenue | M4, M5, M6 | **Guarded** — fallback chains merge across a concept's aliases; M6 picks the *freshest* diluted-EPS concept per company so the series never goes stale. |
| **Wrong-concept name collisions** | A same-keyword tag is a *different* concept — `InterestPaidNet` (cash, not P&L), `RepaymentsOfLongTermDebt` (a cash-flow line, not the balance), `…CurrentAndNoncurrent` combos | M7, M4 | **Guarded** — chains were verified by hand; every alias that would raise coverage was examined and rejected if it was a different concept. |
| **Unit-scale inconsistency** | A share count tagged in thousands beside one in units (Hershey 2010–11: 230,313 vs 228,337,000) | M6 | **Guarded** — the derived-EPS path snaps sub-median-by-100× share counts up by 1,000. |
| **Missing tag entirely** | Gross profit not tagged (service/tech firms); a ratio's ingredient absent | M4 | **Surfaced** — the company is scored only on the ratios it reports; the panel shows *X of 9 ratios · Y of 10 years*. Gross margin was dropped (48% coverage). |

## E · Sign and denominator issues

| Event | What it does | At risk | Handling |
|---|---|---|---|
| **Negative earnings** | A P/E explodes toward ∞ near zero and is meaningless when negative | M6 | **Guarded** — M6 ranks the **earnings yield** (earnings ÷ price), which stays finite; a loss is a clean negative at the bottom of the history. |
| **Negative equity** | Book equity < 0 (from losses *or* from buybacks) breaks equity-based ratios and can't tell distress from financial engineering | M7 | **Guarded** — solvency is interest coverage, not equity (see A · buybacks). Financials use a capital-adequacy floor where equity *is* meaningful. |
| **Near-zero / negative denominator** | Tiny equity → huge ROE; a one-off tiny base spikes a ratio | M4 | **Guarded** — M4 is **rank-based** (percentile vs peers), so an outlier ratio ranks at an extreme without distorting the scale; no winsorising needed. |

## F · Sector-structural differences

Not events, but standing category differences that break a universal metric —
handled by adjusting *what is measured* per sector, never by lowering the bar.

| Structure | What breaks | At risk | Handling |
|---|---|---|---|
| **Banks / capital-markets** | Operating cash flow is lending/trading/float (not cash generation); interest is the *business*, so coverage ≈ 2 is normal; assets are the business, so ROA misreads | M4, M5, M7 | **Guarded** — M4 ranks within sub-industry (banks vs banks); M7 skips the cash gate for financials and uses capital adequacy not coverage; M5 falls back to annual YoY. |
| **Utilities** | Perpetual capex funded by debt → negative free cash flow though operating-cash-positive | M7 | **Guarded** — M7's cash gate uses operating cash, not free cash; coverage ≥ 2× admits stably-levered utilities. |
| **REITs** | Excluded from the universe by design | — | **N/A** — not in scope. |

## G · Data-source issues

| Event | What it does | At risk | Handling |
|---|---|---|---|
| **Real but wild price moves** | A 10:1 split (Netflix), a 2000% run (SanDisk) look like bad data but aren't | M1, M3 | **Guarded (lesson learned)** — we do not "repair" a move just because it's large; split-adjusted closes are trusted. |
| **Split not applied by the feed** | A raw feed leaves a split unadjusted | M1, M2, M3 | **Guarded** — `splits.py` repairs unapplied splits. |
| **Missing market-cap field** | The provider key is an attribute, not a dict key | display | **Guarded** — read via the attribute; missing → shown as —. |

## H · Non-recurring items

| Event | What it does | At risk | Handling |
|---|---|---|---|
| **One-time charge / impairment / tax item** | A single quarter's net income drops sharply on a non-operating item, with the business fine | M5 | **Open / mitigated** — M5 can read a one-off quarter as *declining*; it only **tempers** the verdict (never gates the buy list), and the panel shows the actual revenue/earnings YoY so the cause is visible. A revenue+earnings (not earnings-only) rule limits false positives; further smoothing is a rigor-phase candidate. |
| **Sector-wide shock year** | An exogenous event (a demand collapse) knocks a whole sector into loss for one year | M4, M7 | **Open** — not yet excused mechanically in Cellar (Vantage excluded such years from its profit gate; whether to port that is a rigor-phase decision). |

---

## Open residuals (tracked for the rigor phase)

1. **Former-CIK merge** — recover the ~10 reorged names (Exxon, BlackRock, …), verified per name against EDGAR.
2. **Merger-history comparability** — pre-merger comparatives for combined entities (Paramount Skydance, Smurfit Westrock).
3. **Fiscal-year-shift gaps in M5** — a company mid-shift can miss a comparable period.
4. **One-off-item smoothing in M5** — reduce false *declining* reads from non-recurring charges.
5. **Sector-wide shock years** — decide whether to excuse them mechanically (M4/M7).

Each is currently **surfaced honestly** (the affected company reads *can't assess*
or its number is shown with its working), so no open residual is a silent wrong
answer — only a visible gap.

## Credits

Data hazards catalogued from direct testing against SEC EDGAR `companyfacts`
across the S&P Composite 1500. The sector-metric principle (adjust the metric to
fit a business model, never the bar to fit a sector) and the sector-shock-year
idea are drawn from prior fundamental-screening work on the same data source.
