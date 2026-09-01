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

**The buy case.** A name is a buy when it *fell* (M1), it *reliably comes
back* from a dip this deep (M2), and the *business is sound* (M4/M5/M7) —
with *cheap* (M3/M6) telling the buyer how good the entry price is. Quality
is the foundation: Cellar only deals in strong businesses.

**Site vs. email.**
- The **site** shows every company with all four answers and **tier filters**
  (not raw sliders — a first-time user can't anchor a slider). A
  **"reset to default"** button restores the buy preset.
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

### 4.4 · M4 — Quality *(Good business?, part 1)* — **proposed**

The foundation. A vetted set of fundamental ratios, each turned into a
**percentile against peers**, per year, over the full 10-K history;
summarised as a **level** (median year) and a **consistency** (worst year —
a long track record, not one good year). Peers = the **finest GICS level
that still has enough members**, falling back up the hierarchy
(sub-industry → industry → group → sector). The ratio set is vetted on the
pull for coverage (≥95% after fallback chaining) and for redundancy (metrics
that move in lockstep are pruned). `[design + calibrate on the pull]`

### 4.5 · M5 — Fundamentals status *(Good business?, part 2 — the mispricing test)* — **proposed**

Whether the fall was backed by evidence. Financials only change when a
filing lands, so this is answered around a 10-Q/10-K:
- dip **shortly after** a filing → compare the new filing to the prior
  period → fundamentals **declined** or **held up**;
- dip with **no recent filing** → financials are stale, nothing in the
  business changed → **"no new evidence"**, shown with an "as of [date]"
  stamp — the clean-mispricing tell, not a demotion.

Uses the filing dates carried in `companyfacts`. `[design]`

### 4.6 · M6 — Cheap on earnings *(Cheap?, part 2)* — **proposed**

Today's price/earnings ratio ranked against the company's **own** P/E
history, both recent and long. TTM earnings, with Q4 derived as annual minus
Q1–Q3. This is the earnings-side companion to M3's price-side reading; §5
sets out how the two combine. `[design]`

### 4.7 · M7 — The absolute floor *(Good business?, part 3 — the email gate)* — **proposed**

The one deliberately **absolute** check amid relative scoring: is the
company genuinely **profitable, cash-generative, and not over-levered**, on
hard numbers, not versus peers. Relative quality has one blind spot it
cannot fix — it can rate a company "high" merely for being the best of a
weak peer group (the best airline is still an airline). The floor is the
backstop that keeps "high quality" true in absolute terms, and it is part of
the **email/default gate**. `[design]`

---

## 5 · How "Cheap?" reconciles M3 and M6 — **critical**

M3 (cheap vs. its own **price** history) and M6 (cheap vs. **earnings**)
answer different questions and **coexist — they are never merged into one
"cheap" number.** M3 knows only price; M6 knows profits. Their **agreement
or disagreement is the signal:**

| | **Cheap on earnings** (low P/E vs. own history) | **Not cheap on earnings** |
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
peer recovery), and valuation (M6, vs. peer P/E). It is a comparison lens,
not a separate measurement.

---

## 7 · Row output and the detailed panel

**Collapsed row** — scannable: the four plain-language answers plus their
tiers, market cap, and links (Yahoo, Google Finance).

**Expanded panel** — full transparency. A **collapsible box per
measurement** (M1–M7), each opening to the **real workings**: the multi-year
actual values, how the number was derived, and a plain-English explanation.
**Every headline number cites its working** — clickable through to the
episodes behind "recovered 14 times," the fit behind "usual price $108," and
so on. Nothing shown is un-auditable.

---

## 8 · Site

- **Header** — `Daily Analysis: S&P 1500*` · asterisk: excludes REITs.
- **Filters** — **tiers** for each question (e.g. Fell: Big/Some/Any;
  Comes-back: Strong/Some/Any; Cheap: Cheap/Fair/Any; Business: High/Med/Low),
  a **Size** tier filter (Mega ≥ $200B / Large / Mid / Small < $2B), and a
  category filter for fundamentals status. A power-user slider may hide
  behind an "advanced" toggle.
- **Sort** — a control to order the list (biggest dip, deepest reliable
  recovery, cheapest, ticker); column headers also sort.
- **Default view** = the buy preset (fell + reliably recovers + business
  sound). A **reset button** restores it.

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
default.

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
