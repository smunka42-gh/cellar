# Cellar — tenets

The standing principles for how Cellar is designed and built. Short,
opinionated, meant to settle arguments before they start. The list grows
as we learn.

---

## 1 · Simplify, and build for scale

Prefer the smallest design that works — in every part of the system.

- **Fewer metrics and signals.** Each score tracks the fewest metrics that
  actually carry its signal. A metric that duplicates another, or moves in
  lockstep with it, is removed — not kept "just in case."
- **Simpler pipelines.** Pull from EDGAR `frames` and yfinance in the
  fewest calls that do the job; favour bulk endpoints over per-company
  loops.
- **Separate the slow pull from the fast compute.** Raw data is pulled
  *once* into a local store, over an agreed set of tags, periods and
  frequency. All scoring then runs against that local store and finishes in
  seconds — never a fresh network pull on each change. We iterate on
  scoring logic constantly, so we agree the full list of what to pull up
  front, pull a generous-but-bounded superset one time, and compute from
  cache thereafter.

---

## 2 · When in doubt, take it out

Every score, tier, filter, tag and output must earn its place. The default
answer to "should we add this?" is *no*. Build the design a first-time user
understands without a manual.

- **No feature exists because it *might* be useful.** It exists because a
  concrete decision needs it.
- **Reproduce, don't reinvent.** If a result the user can already reach by
  moving a filter, we do not also build a named feature for it.
- **Continuous beats categorical** where a slider will do — one score with
  a threshold beats three hard-coded tiers.

---

## Credits

None yet.
