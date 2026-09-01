# Cellar — specification

Buy the dip — but only in **high-quality companies that reliably recover**,
and tell the buyer, in plain language, *why* and *how confident to be*.

A cellar is where you keep things worth keeping and wait. Cellar watches a
fixed universe of strong US companies and, every day, finds the ones whose
price has fallen to a level history says they climb back from.

This document is the shipped statement of the design. Working notes,
rejected options and reasoning live in the private build log, never here.
**Methods** below are settled; **numbers** marked `[calibrate]` are set from
the one-time data pull, by looking at real data rather than guessing.

---

## 1 · What Cellar is

**The promise is timeliness.** An email goes out *only* on a day with a real
opportunity, so the arrival of an email *is* the signal — nobody has to
check the site. The site is the always-current reference; the email (and
later, text) is the trigger. Cellar exists because the motivating case — a
big drop in a great company — was found four days late.

**It recommends, openly.** The same list goes to everyone, the criteria are
stated in full and applied mechanically. A footer states this is general
information, identical for every subscriber, and not tailored advice.

---

## 2 · The four questions

Everything Cellar computes answers four plain questions about every company,
every day:

| Question | Means | Measurements |
|---|---|---|
| **Fell?** | Has the price dropped, and freshly? | M1 |
| **Comes back?** | Does it reliably recover — and how deep can you safely buy? | M2 |
| **Cheap?** | Is today a genuine discount, on its own price *and* on earnings? | M3 · M6 |
| **Good business?** | Strong, still-sound, not broken? | M4 · M5 · M7 |

A fifth, cross-cutting lens sits over all four: **how does this compare to
its sector peers?** (the sector overlay).

**The buy case, and the gate.** **M7 (the hoarding floor) is the top-level
gate** — *is this worth owning at all?* If it fails, the dip, the recovery
record and the cheapness are moot. Once it clears, a name is a buy when it
*fell* (M1), *reliably comes back* from a dip this deep (M2), is *cheap*
(M3/M6), and is *high relative quality* (M4) — with M5 (the mispricing test)
telling the buyer whether the fall was backed by real deterioration. Every
row carries a deterministic **verdict**, led by the hoarding gate.

**Site vs. email.**
- The **site** shows every company with all four answers and **tier filters**
  (not raw sliders — a first-time user can't anchor a slider), and a
  **Buy list ⇄ All** toggle (the buy preset, or the whole universe).
- The **email** is exactly the **site's default filter view** — the buy
  preset. One definition serves both, so the email criteria and the site
  filters can never drift apart. Email fires only when that view is
  non-empty.

---

## 3 · Universe

S&P Composite 1500, then two published-fact exclusions:
- drop the GICS sector `Real Estate` (REITs are judged on funds from
  operations, not the ratios everything else uses); and
- drop any company that does **not file financial statements with the
  SEC** — a small number of banks report to their bank regulator (FDIC)
  instead, so EDGAR carries no financials for them and Cellar could never
  complete their case. This is decided *mechanically* (the company's EDGAR
  `companyfacts` is empty / it files no 10-K), never by a hand-kept list.

One ticker per filer — whichever the SEC's `company_tickers.json` lists
first for that CIK. Result: **1,394 companies** (1,500 − ~104 REITs − 2
FDIC-only banks, as of the current constituent lists).

Carried over unchanged: constituent loading (with a guard against parsing a
page's *changes* table instead of its *constituents*) and a split-repair
step for splits a price feed leaves unapplied.

---

## 4 · The measurements

Prices are split/dividend-adjusted daily closes. Fundamentals are
as-filed from SEC EDGAR `companyfacts`. All history is **full filing /
listing history**, as far back as the source allows.

### 4.1 · M1 — The dip *(Fell?)*

The trigger. Measured from the **highest close in a trailing window
(~3 years)** — deliberately *not* the all-time high, so a peak years stale
can't dress a long decline up as a "dip":
- **how far below** that recent high the price is today (the drawdown), and
- **how many days since** that high — a *fresh* drop versus a *slow slide*.

Freshness matters: a stock that dropped this week is the "I'd have missed
it" case; one that has slid for a year is a different situation. Sector
overlay: the same drop shown against the sector's own drop, to separate a
company-specific fall from a sector-wide one.
`[calibrate: high window (~3y), freshness window]`

### 4.2 · M2 — Reliable recovery *(Comes back?)* — the resilience reading

The measurement that decides how deep you can safely accumulate. From the
full price history, every **drawdown episode** is identified (record high →
trough → reclaim of that high), with its depth and its recovery time.

A depth is **reliably recoverable** when it passes a twofold test:
1. **it always eventually recovers** to the prior high, and
2. the **typical recovery is fast enough that the gain, annualized, clears
   ~10%/year** — where the recover-to-high gain is `1/(1 − depth) − 1`.

Because a deep recovery is a large gain, **depth earns patience
automatically**: a 15% dip must recover within ~1.7 years to clear the bar;
a 39% dip may take up to ~5 years. The **deepest depth that passes**, on at
least `[calibrate: min occurrences]` occurrences, is the stock's *reliable
depth*. The reading reports that depth, how many times it happened, and the
typical recovery time.

The **current, open drawdown is excluded** — it is the case under
evaluation, not evidence, so a company is never penalised for the dip you
are looking at.

*Illustrative (from a snapshot):* Walmart reliably recovers from dips as
deep as ~36% (bounced back many times, typically within a year or two);
Netflix as deep as ~55%. The deeper that reliable floor, the more you can
accumulate cheaply and still win. `[calibrate: annualized bar, min occurrences]`

### 4.3 · M3 — Cheap vs. its own price history *(Cheap?, part 1)*

Every steady stock has a **"usual price"** — where its own growth would put
it today. Fit a straight line to `log(price)` over a fixed window; that line
is the usual price, and today's distance below it, measured in the stock's
own typical wobble, is a **standard-deviation reading** (−2 = unusually
cheap for this stock). This is drift-corrected: a compounder near its highs
sits *on* its line (not "cheap"), and only reads cheap when it falls below
its own growth path.

**A fit-quality gate decides the readout.** The trend "usual price" leads
only where the fit is good **and the trend isn't declining** — a falling
trend line predicts more falling, so "below/above trend" would say nothing
about cheap vs. expensive (this is what made crashed names misread as
"above usual"). Where the fit is poor *or the trend slopes down*, a
**range reading** takes over — *"what fraction of the last 3 years
did it trade at least 10% (and 20%) above today?"* A lot → real room to
recover into levels it recently held; little → today is near the top of its
range. The range reading needs no trend, so it covers exactly the cyclical
and flat stocks the trend reading cannot. The dividing line is *measured
fit*, not a hand-drawn "growth vs. cyclical" label.

*Illustrative:* Walmart's usual price ≈ $108 (so at ~$105 it is at its usual
price — recoverable, but not a discount); Netflix's ≈ $91 (so at ~$81 it is
a modest discount). `[calibrate: window length, fit cutoff]`

### 4.4 · M4 — Quality *(Good business?, part 1)*

The foundation, and the real buy gate. Nine vetted fundamental ratios across
five quality dimensions — **returns on capital** (ROE, ROA), **margin** (net
margin), **cash** (free-cash-flow margin, cash conversion), **efficiency**
(asset turnover), and **balance sheet** (debt/equity, interest coverage,
current ratio). Each ratio, each year, becomes a **percentile against sector
peers**; the year's scores are averaged within each dimension and then across
the five dimensions with **equal weight** — so the three balance-sheet ratios
can't outvote profitability. That yearly composite is summarised per company
as a **level** (its median year — typical standing) and a **consistency** (its
worst year — a track record, not one good year).

**A bounded window, not all of history.** Level and consistency use the last
**~ten fiscal years**. The per-year percentile already neutralises macro
cycles (a sector-wide margin squeeze doesn't change a company's *rank*), but an
unbounded window skews three other ways: the business a decade-plus ago may be
a different company (level should reflect what it *is*); a stale one-off stumble
can define the floor; and — the sharp one — "worst year ever" punishes
long-tenured companies for merely having lived more years in which to have a
bad one. A fixed decade judges every company on the same span, still spans a
full cycle (2015–2025 includes the COVID shock), and reflects the business now.

**Peers, coverage, and the honest gaps.** Peers are the **finest GICS level
with enough members**: each company is ranked in its **GICS sub-industry**
wherever that group has at least a handful of members in a given ratio-year,
falling back to its **sector** otherwise — about 89% of companies rank at the
sub-industry level. This is what lets a bank be judged against banks
(JPMorgan against *diversified banks*, not against payment networks and
exchanges). The ratio set was vetted on the real pull: the XBRL fallback chains
are **verified complete** (every alias that would raise coverage was examined
and rejected as a *different* concept — e.g. `InterestPaidNet` is cash-flow
interest, not P&L interest expense; `RepaymentsOfLongTermDebt` is a cash-flow
line, not the balance), gross margin was dropped (48% coverage, no fallback),
and operating margin was pruned as redundant with net margin (ρ = 0.93).
Coverage is strong — the median company computes all nine ratios across all ten
years. A company is scored only on the ratios it reports, **never a defaulted
blank**; where a ratio or year is missing, the panel shows it (ratios /
dimensions / years covered) rather than hiding it, and companies too thin to
rank are flagged *limited data*. `[calibrate: tier cutoffs]`

### 4.5 · M5 — The mispricing test *(Fell?, part 2 / Good business?, part 2)*

Was the fall backed by new fundamental evidence, or did the price drop while
the business **held up**? A dip with no deterioration behind it is the clean
**mispricing** — the ideal thing to hoard; a dip backed by genuinely declining
fundamentals is **earned**. And because M7 judges the whole decade, M5 adds
what the decade can't see: *is this sound business rolling over right now?*

Read from **quarterly** (10-Q) figures, year-over-year to kill seasonality —
the timely signal the annual 10-K can't give (the latest filing is a median of
~a month old). A reframe the data forced: since almost every company files
freshly, "no recent filing" is rare, so the axis is not *whether* there's a
filing but whether the latest fundamentals **declined or held up**:

- **Declining** — latest-quarter revenue down > 3%, *or* net income down > 25%
  (a real top-line decline or a sharp profit fall).
- **Held up** — otherwise: revenue flat/up and profit not sharply down.

**Financials fall back to annual** year-over-year, since their quarterly tagging
is unreliable (a bank's quarterly figures come and go under shifting concepts).
Recent listings with no year-ago comparable read *no timely read*. Everything
carries an **"as of [quarter-end]"** stamp. It shows on the **Fell? card** (the
dip's cause) and as a clause in the verdict — a *declining* read **tempers**
even a cheap, resilient, floor-clearing name; a *held-up* read **strengthens**
the buy case. It does not hard-gate the buy list (M7 is the hard gate); it is an
early warning. Calibrated + validated on a fell-on-bad-news vs. fell-on-nothing
basket (Nike/Lululemon/Intel → declining; Costco/Google/recovered-Target →
held up). ~24% of the universe reads declining. `[calibrate: the thresholds]`

### 4.6 · M6 — Cheap on earnings *(Cheap?, part 2)*

Today's **earnings yield** — annual earnings ÷ today's price — ranked against
the company's **own** yield history, both long and recent (5-year). A high
rank means today's price buys more earnings than it usually has: cheap on
earnings. It is the earnings-side companion to M3's price-side reading; §5
sets out how the two combine.

**Why yield, not the P/E ratio.** A P/E explodes toward infinity as earnings
approach zero and turns meaningless when they go negative, so a P/E history
is full of holes and spikes. Its reciprocal, the yield, stays finite: a loss
is simply a negative yield that ranks cleanly at the bottom. The series has
no gaps to paper over. **And current earnings, not a multi-year average** —
ranking today's yield against the stock's own past yields is self-consistent
(each past point used its own then-current earnings), so a company that grew
its profits is not penalised the way a lagging average would penalise it.

**Getting the earnings right was most of the work.** Earnings are annual
(whole-year 10-K figures), split-adjusted by **filing date** to line up with
the split-adjusted prices — a 10-K filed after a split already reports
post-split per-share numbers, so adjusting by the reporting period would
double-count. Three subtleties, each a silent-wrong-number trap if missed:
the fiscal year is read from the reporting period's **end date**, not the
filing's own year tag (one 10-K carries three comparative years under that
one tag); the diluted-EPS **concept is chosen per company by whichever is
freshest**, because filers migrate between concepts mid-history and reading
only the first leaves the series years stale; and where a filer reports no
per-share figure at all, earnings are **derived from net income ÷ diluted
shares** — the definition the company itself uses — guarded by a share-count
scale check, a valuation-sanity gate, and a staleness cutoff, so a name we
cannot read cleanly (dual-class, partnership, reorganised filer) shows an
honest blank rather than a wrong number. Coverage: **1,354 of 1,394**; the
blanks are recent IPOs, dual-class/partnership structures, and a few filers
whose recent earnings are not in the data.
`[calibrate: earnings-cheap percentile cut, derived-value sanity band]`

### 4.7 · M7 — The hoarding floor *(Good business?, part 3 — the gate)*

**The top-level gate of the whole tool.** M7 asks the one deliberately
**absolute** question: *is this business worth hoarding at all?* If it fails,
every other reading — the dip, the recovery record, the cheapness, the
relative quality — is moot; a fallen, cheap, resilient stock that fails M7 is
just a cheap way to own a bad business. Relative quality (M4) has one blind
spot it cannot fix: it can rate a company "high" for being the best of a weak
peer group (the best airline is still an airline). M7 is the backstop, and the
email/buy gate.

**Three gates, each a soundness indicator — all pass or the floor fails:**
1. **Consistently profitable** — net income positive in ≥80% of the last decade.
2. **Generates operating cash** — operating cash flow positive in ≥80% of years.
3. **Debt serviceable** — comfortably covers its interest.

**Near-universal, with targeted exceptions where a metric is a category error
for a business model** (adjusting the metric to fit a model is legitimate;
lowering the bar for a weak sector is not):
- The **cash gate is skipped for Financials** — a bank's or insurer's operating
  cash flow is lending/trading/float (balance-sheet activity, not cash
  generation), so it false-fails sound banks (JPMorgan, Goldman) even
  cumulatively.
- **Solvency is measured as interest coverage** (operating income ÷ interest),
  because it is **immune to buybacks**. Book equity is unusable: years of
  buybacks drive equity — and even retained earnings — negative at sound cash
  machines (AutoZone, Starbucks, Altria, Domino's), indistinguishable from
  loss-driven distress. For **Financials**, where interest *is* the business
  (coverage ≈ 2 is normal), solvency is a capital-adequacy floor (equity /
  assets) instead. A company with no interest burden at all is solvent by
  definition.

Thresholds are fixed — calibrated once on the whole universe and validated on
an edge basket (Costco/NVIDIA/JPMorgan/Amazon clear; American Airlines,
Boeing, Carnival, Ford fail) — and a near-miss is recorded, never a reason to
move a bar. **71% of the universe clears.** Data (net income, operating cash,
operating income, interest, equity, assets) is the same coverage-verified
cache as M4 — no new pull. `[calibrate: the three thresholds]`

---

## 5 · How "Cheap?" reconciles M3 and M6 — **critical**

M3 (cheap vs. its own **price** history) and M6 (cheap vs. **earnings**)
answer different questions and **coexist — they are never merged into one
"cheap" number.** M3 knows only price; M6 knows profits. Their **agreement
or disagreement is the signal:**

| | **Cheap on earnings** (high yield vs. own history) | **Not cheap on earnings** |
|---|---|---|
| **Price below its usual** (M3 cheap) | cheap both ways — **strongest** | price fell but earnings fell *more* → **value-trap risk** |
| **Price at/above usual** (M3 not cheap) | **"growing into its price"** — flat price, rising profits: a discount M3 alone would miss | **fully priced** |

The bottom-left cell is why M6 exists: a compounder can look "not a
discount" on price yet *be* a discount on earnings because the business grew
more profitable. Neither reading overwrites the other — the **Cheap?** box
holds both, side by side.

---

## 6 · The sector lens

Every reading is also shown **relative to peers**, because a number means
little in isolation: a 15% drop while the sector fell 3% is company-specific;
the same drop in a −20% sector is macro. The sector overlay applies to the
dip (M1), quality (M4, already peer-relative), the recovery record (M2, vs.
peer recovery), and valuation (M6, vs. peer earnings yield). It is a comparison lens,
not a separate measurement.

---

## 7 · Row output and the detailed panel

**Collapsed row** — scannable: the four plain-language answers plus their
tiers, market cap, and links (Yahoo, Google Finance). Below-floor names carry
a "below floor" flag.

**Expanded panel** — opens with a **colour-coded verdict readout**: the
deterministic call ("A dip worth hoarding" / "Not worth hoarding" / …) led by
the hoarding gate, then a woven, evidence-highlighted narrative — every clause
pinned to a computed value. Below it, the chart and a **card per reading**:
**Worth hoarding?** (M7, the gate, led first with a clears/below accent),
Fell?, Comes back?, Cheap? (price × earnings side by side), and Good business?
(M4 relative quality). Each opens the **real workings** — the multi-year
values, how the number was derived, plain English — and **every headline
number cites its working**. Nothing shown is un-auditable.

---

## 8 · Site

- **Header** — `Daily Analysis: S&P 1500*` · asterisk: excludes REITs.
- **Filters** — **tiers** for each question: Fell (Big/Some/Minimal);
  Comes-back (Strong/Past/None); Cheap (Both/Growing-in/Trap-risk/Full — the
  M3×M6 cells of §5); Good business (High/Solid/Mixed/Weak — M4 quality); a
  **Hoarding floor** filter (Clears/Below — M7); and a **Size** tier
  (Mega ≥ $200B / Large / Mid / Small < $2B).
- **Sort** — order the list (biggest dip, deepest reliable recovery, cheapest,
  best business, market cap); column headers also sort.
- **Buy list ⇄ All toggle.** The default is the **buy preset** (worth
  hoarding + fell + reliably recovers + cheap + high quality). Switching to
  **All**, or touching any filter or search, queries the whole ~1,394; the
  toggle back to **Buy list** restores the preset and clears filters.

---

## 9 · Email

Sent only on days the **default view** is non-empty — buy-tier only, so an
email always means an opportunity. It *is* the default view, so its criteria
cannot drift from the site. Per name: the four answers, the tiers, the two
sentences (why it fell / why we'd still buy), and a link to its row. Footer:
the criteria in full and the general-information disclaimer.

---

## 10 · Data — pull once, compute from the cache

Per Tenet 1, raw data is pulled **once** into a local cache; every
measurement recomputes from the cache in seconds, never a fresh pull.

| Source | What | Span | Refresh |
|---|---|---|---|
| yfinance | daily close (adjusted) + split events | full history | daily |
| yfinance | market cap | current | daily |
| SEC EDGAR `companyfacts` | **every** XBRL fact + its filing date, one call per company | full history | weekly |
| index lists + `company_tickers.json` | ticker, name, GICS hierarchy, CIK | current | weekly |

`companyfacts` returns *all* of a filer's tags in a single call, so caching
it future-proofs M4–M7: new metrics read a different field from the same
cache — no re-pull. The pull is implemented in `scripts/pull.py` (resumable,
rate-limited); the cache lives under `data/` (gitignored).

---

## 11 · Data-quality guards and pitfalls

Handled explicitly; a missing value is NA — never a proxy or a silent
default. The full catalogue of corporate events that can corrupt the numbers —
splits, buybacks, dilution, CIK reorgs, spin-offs, mergers, tag migrations,
part-year filings, and more — with the measurements each threatens and how
Cellar handles it, is in [`docs/data-hazards.md`](data-hazards.md). A summary
of the load-bearing few:

- **Unapplied splits** — a raw feed can leave a split unadjusted, faking a
  ~50% one-day fall; corrected (adjusted closes; split-repair on raw).
- **A quarter posing as a fiscal year** — annual duration facts must span
  350–380 days.
- **Dropped `frame`-labelled EDGAR entries** — for the newest year these are
  often the only entry; keep them.
- **Filer-id (CIK) changes** — a reorganisation can move a company's whole
  history to a new id; track former ids.
- **Tag availability ≠ quality** — fallback chains plus an explicit "not
  assessable"; prefer asset-denominated and operating-income ratios (higher
  coverage, fewer accounting artefacts than net income and equity).
- **Corporate discontinuities** — a spinoff or re-listing truncates price
  history (a stock can be decades old but list only recently); too-short a
  history cannot establish a reliable depth or a trend, and is flagged
  low-confidence rather than scored on noise.
- **Survivorship** — the universe is today's constituents, so recovery
  records are optimistic (companies that dipped and died left the index);
  M2 is read as "conditional on still being here."
- **Fiscal-year misalignment, restatements, non-USD units** — aligned by
  period-end, point-in-time where it matters, units checked.

---

## 12 · To calibrate from the pull

Set by looking at real data across all 1,396, not guessed:

- **M1** — the trailing high window (~3y) and the freshness window.
- **M2** — the annualized-return bar (~10%), the minimum occurrences, the
  recovery definition.
- **M3** — the trend window (~7 years candidate) and the fit-quality cutoff
  that switches to the range reading.
- **M4** — the ratio set (coverage ≥95%, redundancy pruned) and the peer
  min-members threshold.
- Tier boundaries and the email gate.

---

## Credits

Index constituents from S&P Dow Jones Indices via public listings.
Financial and filing data from the US Securities and Exchange Commission's
EDGAR system. GICS is a joint product of S&P Dow Jones Indices and MSCI.
Price and market-cap data via the yfinance library.
