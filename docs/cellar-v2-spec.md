# Cellar v2 — design spec (DRAFT for review)

> **Status.** v2 is in design. **v1 is live and paused** at
> https://smunka42-gh.github.io/cellar/ (self-refreshing daily) and is not being
> changed while we design v2. This document is a working draft — the sections
> below are meant to be argued with and revised together, not treated as settled.
> Where a choice is still open it is marked **[OPEN]**.

---

## 1 · The investor: the Hoarder

Cellar is built for one specific investor, and every measurement and every pixel
should serve how *they* decide. Naming the profile precisely is what keeps the
tool from drifting into a generic stock screener.

**The Hoarder is:**
- **A long-term owner, not a trader.** They *accumulate* great businesses and
  hold for years. They are not timing swings or chasing momentum.
- **Patient and infrequent.** They do not buy every day. **One well-evidenced buy
  a week — or a month — is plenty.** A short, high-conviction list beats a long
  hedged one. An empty list on a given day is a perfectly good answer.
- **Quality-first.** They only want to own durable, sound, high-quality
  businesses in the first place. Price is the *second* question, never the first.
- **Contrarian, but not reckless.** They are comfortable buying what is out of
  favour — *provided the business is intact.* Their nightmare is the **value
  trap** (cheap because it is genuinely deteriorating) and the **falling knife**
  (a prolonged structural decline they mistake for a dip).
- **Evidence-driven.** They distrust hype and narrative. Every claim must trace
  to a number or a filing they can check. "The market is down on it" is not a
  reason; *why* it is down, and whether that reason is real, is the whole game.
- **Risk-aware about the things screens miss.** Customer concentration, a
  controlled/opaque ownership structure, a structural threat to the moat — they
  want these surfaced even when the ratios look clean.

**What the Hoarder is NOT:** a day-trader, a momentum chaser, an index buyer, or
someone who wants 50 "buy" ideas. Volume is not the goal; *conviction* is.

---

## 2 · The Hoarder's decision journey (the spine of the product)

Everything downstream — measurements, pillars, the daily list, the email, the UI —
is derived from this sequence. There are several ways a hoarder can arrive at a
buy; the tool should support all of them, but they share one backbone:

1. **Build the watchlist (Quality).** First, permanently narrow the ~1,396 to the
   businesses worth owning *at all*: durably sound, high-quality, resilient. This
   list changes slowly (only as fundamentals change), and it is the universe the
   hoarder actually watches. *Question: is this a company I would ever want to
   hoard?*

2. **Watch for value (Valuation).** Monitor the watchlist for when a name becomes
   *cheap* — cheap versus its own price history (low in its multi-year range),
   cheap versus its earnings, and trading at a discount to where analysts think
   it should be. **A quality company at a cheap price is buyable even with no
   dramatic crash.** *Question: is it cheap right now?*

3. **Notice the catalyst (the Dip).** In practice, the moment that *prompts*
   action is usually a **dip** — a sudden fall that puts a quality company on
   sale. A **5%+ single-day drop** in a watchlist name is the "look today" signal.
   But a dip is not automatically an opportunity; it raises the decisive question:

4. **Was the dip justified? (Evidence).** Did the *business or its expectations*
   actually deteriorate — an earnings **miss** versus analyst consensus, or a
   **downward revision** of forward estimates/guidance? 
   - **Justified** → the cheapness is *earned*; likely a value trap or knife → **Avoid.**
   - **Unjustified** → the fall came with no deterioration → a **mispricing** →
     the strongest **Buy** signal, on top of an already-cheap quality name.

5. **Check for a prolonged decline (Staleness).** Is this a *fresh* dip or a
   multi-year grind? A deep dip that only appears in the 2–5-year view but not the
   1-year view means the high is old and unrecovered — the "reliably recovers"
   history may no longer apply. This makes the hoarder *uneasy* and should be
   surfaced loudly.

6. **Decide: Buy or Avoid — with the evidence.** Never a bare verdict; always the
   reasons on both sides.

**Ways a hoarder legitimately decides (all supported):**
- *"Only own great businesses"* → Quality gate.
- *"Buy quality cheap vs its own history"* → cheap-on-price percentile.
- *"Buy quality cheap on earnings"* → earnings yield vs own history.
- *"Buy when there's real upside to fair value"* → analyst-target discount.
- *"Act on a dip, but only if unjustified"* → the dip catalyst + Dip-Justified.
- *"Avoid deterioration, traps, knives, and opaque names"* → Dip-Justified =
  justified, the staleness flag, and (future) concentration/governance flags.

---

## 3 · How the journey maps to Cellar — three pillars + evidence

| Pillar | The hoarder's question | Signals |
|---|---|---|
| **Quality** (the watchlist) | *Worth owning at all?* | Hoarding floor + business quality vs peers + resilience/recovery |
| **Valuation** (is it cheap now) | *Cheap right now?* | Cheap on price (multi-window) · cheap on earnings · discount to analyst target |
| **Price & the dip** (the catalyst) | *Did it just fall, and was that justified?* | Single-day move · multi-window dip · **Dip Justified?** · prolonged-decline flag · chart |
| **News / filings** | *What's actually happening?* | Recent SEC filings + link to press coverage |

The **daily list** is the intersection: **on the Quality watchlist, and cheap now.**
A **dip** raises urgency and adds the Dip-Justified test. The **verdict** is a
**Buy / Avoid** with evidence.

---

## 4 · Pillar 1 — Quality (the watchlist gate)

A single binary the hoarder can toggle: **Company Quality: Yes / No.** *Yes* means
"worth hoarding at all." It merges three v1 measures; the detail still shows each
component so the Yes/No is auditable.

- **Sound enough to own (the hoarding floor)** — durably profitable, cash-
  generative, debt serviceable over the decade *(v1 M7, unchanged logic)*.
- **High quality vs peers** — top-tier on the fundamental ratios vs GICS
  sub-industry peers *(v1 M4)*. **[OPEN]** threshold for the watchlist: High only,
  or High + Solid? (v1 buy used High.)
- **Resilient / reliably recovers** — has a track record of climbing back from
  drawdowns *(v1 M2)*. Note: this is mechanically a price-history signal; it sits
  here as *resilience*. **[OPEN]** keep as a gate, or demote to a displayed
  resilience read rather than a hard requirement?

*Quality = Yes* → on the watchlist. The watchlist is the standing universe the
hoarder monitors; it changes only as fundamentals change.

---

## 5 · Pillar 2 — Valuation (is it cheap now?)

Three independent reads, each its own card; none invented, all vs a stated
reference.

1. **Cheap on price (multi-window percentile).** *Replaces v1's "% below the
   3-year high" machinery* with something more intuitive and robust: **the % of
   each lookback window the stock traded ABOVE today's price**, for **YTD, 1yr,
   2yr, 3yr, 5yr.** If it traded higher than today >~75% of a window, today is in
   the cheap end of that range. Showing all windows exposes the staleness nuance
   directly (e.g., ADBE: ~42% on 1yr but ~81% on 3yr → cheap only on the long
   view → an old, unrecovered high). No trend-fitting, no R² fragility.

2. **Cheap on earnings.** Earnings yield vs the company's own history *(v1 M6,
   unchanged)*. **[OPEN]** add cyclical-earnings normalisation (mid-cycle EPS) so
   a low P/E on peak earnings isn't mistaken for cheap.

3. **Discount to analyst target.** (mean analyst price target − today) / today,
   from aggregated analyst targets (yfinance `targetMeanPrice`, with the analyst
   count). **Displayed + used as a tie-breaker, NOT a hard gate** — targets lag
   price and are conservative on out-of-favour names (the exact names we want to
   be contrarian on), so gating on them would quietly re-impose consensus.

---

## 6 · Pillar 3 — Price & the dip (the catalyst and its justification)

1. **The catalyst — single-day move.** A **≥5% single-day drop** in a watchlist
   name is the "pay attention today" trigger (and the email trigger, §8).

2. **Multi-window dip (depth + staleness).** The drawdown from each window's high:
   **YTD, 1yr, 2yr, 3yr, 5yr.** A dip that appears only in the longer windows
   (deep 3–5yr dip, shallow YTD/1yr) means the high is **old and unrecovered** →
   a **prolonged-decline flag**, shown loudly. Fresh dips (visible in YTD/1yr) are
   the healthy hoarding moments.

3. **Dip Justified? — the real M5 (expectations-based).** The decisive test.
   Built entirely from analyst-expectations data (yfinance, no LLM, no paid feed):
   - **Beat/miss:** latest reported quarter's actual EPS vs the consensus estimate
     (surprise %). A miss is deterioration evidence.
   - **Estimate revisions:** the forward consensus EPS estimate *now vs 30/60/90
     days ago*. Estimates being **cut** is the live proxy for a guidance
     downgrade — and, crucially, it is **continuously fresh** (it does not wait
     for the next 10-Q), which solves v1's "stale between filings" gap.
   - **Verdict:** **Justified (Yes)** = the quarter missed *or* forward estimates
     are being cut → the fall is earned → **Avoid.** **Unjustified (No)** =
     met/beat *and* estimates stable/rising, yet the price fell → a **mispricing**
     → **Buy** signal.
   - **No analyst coverage → disqualifying,** not a neutral "no read." If the
     market doesn't watch it, it isn't a hoard. *(This replaces v1's YoY-actuals
     M5 entirely; TTM smoothing is dropped — it addressed noise, not the real
     driver, which is expectations.)*
   - Every verdict shows its **evidence**: "beat by X% / missed by X%," "forward
     EPS revised +/−X% over 90 days."

4. **The chart** — price history with the key levels.

---

## 7 · The daily list and the Buy / Avoid decision

- **Always-on (website):** the full analysis for the entire watchlist (and,
  toggleable, all 1,396) is available every day, whether or not anything dipped.
- **The buy candidates:** on the **Quality** watchlist **and cheap now** (cheap on
  price + cheap on earnings; analyst-target discount as tie-breaker).
- **A dip elevates a candidate** and adds the Dip-Justified test:
  - **Buy** = Quality + cheap + (if it dipped) **Dip Unjustified** + **not** a
    prolonged/stale decline + has analyst coverage.
  - **Avoid** = Dip **Justified** (real deterioration), *or* a prolonged decline,
    *or* no coverage, *or* not actually cheap.

**[OPEN]** exact cheapness thresholds (e.g., "traded higher >75% of the 3yr
window" AND "earnings yield ≥ Nth percentile of own history").

---

## 8 · Email

- **Trigger:** any **watchlist** ticker posts a **≥5% single-day drop.**
- **Content:** the ticker, the multi-window dip picture, and a one-word verdict —
  **Buy** or **Avoid** — with the evidence (Dip-Justified reasons, cheapness,
  quality, prolonged-decline flag). Sent only on days a trigger fires (often no
  email — that's correct).
- Deferred until the v2 measures are built and validated.

---

## 9 · Website / UI-UX and terminology principles

The site carries the always-on analysis for the whole watchlist / universe,
organised by the three pillars, with a Buy/Avoid verdict and full evidence per
name.

**Terminology principles (the separate workstream — [OPEN], to co-design):**
- **Professional, adult, precise** — no cute or "kiddish" tier names. Retire
  "Big / Some / Minimal," "Held up / Declining / No read," etc.
- **Consistent grammar** across pillars (e.g., all states are adjectives, or all
  are yes/no).
- **Say the question, answer it plainly.** "Dip Justified? — Yes / No" is the
  model: a real question, a binary answer, evidence beneath.
- **Neutral, not editorial** — "Warranted / Unwarranted," "Justified / Unjustified,"
  not "good / bad."
- A full lexicon pass (every label, chip, header, and card title) is its own
  effort; this spec only fixes the M5 header (**"Dip Justified"**) for now.

---

## 10 · Measurement inventory — carry-over vs change

| v1 measure | v2 disposition |
|---|---|
| M1 dip (% below 3yr high) | **Replaced** by multi-window dip (YTD/1/2/3/5yr) + single-day trigger + prolonged-decline flag |
| M2 reliable recovery | **Folded into Quality** as resilience *(open: gate vs display)* |
| M3 cheap vs price history | **Replaced** by the multi-window "traded above today %" percentile |
| M4 quality vs peers | **Folded into Quality** |
| M5 mispricing (YoY actuals) | **Replaced** by expectations-based **Dip Justified** (beat/miss + estimate revisions) |
| M6 cheap on earnings | **Kept** in Valuation *(open: cyclical normalisation)* |
| M7 hoarding floor | **Folded into Quality** |
| — | **New:** discount to analyst target (Valuation) |
| — | **New:** analyst-expectations engine (beat/miss, estimate revisions) |

Data additions vs v1: analyst estimates + surprises + target prices (yfinance).
Everything else (prices, SEC facts, filings, profiles, ratings) already flows.

---

## 11 · Open decisions to resolve together
1. Quality gate: M4 **High only**, or **High + Solid**?
2. Resilience (old M2): a hard gate, or a displayed read?
3. Cheap-on-earnings: add cyclical (mid-cycle) normalisation?
4. Exact cheapness thresholds for the daily buy list.
5. Analyst-target discount: confirmed as tie-breaker, not gate?
6. The full terminology lexicon (its own working session).
7. Does the name/tagline change, now that the dip is a catalyst rather than the
   definition? ("Buy the dip" → "Hoard quality when it's cheap.")

## Credits
Index constituents from S&P Dow Jones Indices; financial and filing data from the
US SEC's EDGAR system; GICS is S&P Dow Jones Indices / MSCI; prices, analyst
estimates, targets and profiles via the yfinance library. Investor-journey framing
developed with the project owner (the Hoarder profile).
