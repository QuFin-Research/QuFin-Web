# ADR 0005: Economy scorecard method

**Status:** Accepted; 8 pillars and 0-100 scale pending (1 Nov 2026)

## Context
The Blueprint's scorecard: direction-adjust, standardise against own history, pillar scores,
weighted economy score 0-100, pair score as base minus quote (section 04).

## Decision
- Each indicator is scored point in time against its own 10-year history on two parts, where it
  stands and its 3-month momentum, clipped to -3..+3 and flipped where higher is weaker.
- A pillar is the weighted average of its usable indicators with weights rescaled; late or missing
  data lowers a separate confidence and never moves the score. Weights = expert importance ×
  timeliness. A bias backtest gates any change (`scorecard-bias`).
- Pairs take the lower confidence of their two sides.

## Pending
- **8 pillars** (growth, inflation, labour, monetary policy, fiscal, external and trade, surveys
  and sentiment, financial conditions). Today there are 5: "sentiment" mixes surveys with
  financial conditions, and fiscal and external have no data yet (Treasury Fiscal Data, trade
  balance and current account are needed).
- **0-100 display scale:** the score is computed on -3..+3; the display maps linearly
  (score + 3) / 6 × 100.
- **Version 2 learned weights** (Phase 3), limited in how far they move from the priors.
