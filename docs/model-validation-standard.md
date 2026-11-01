# Model validation standard

Backlog task P0-19. No score, signal or model reaches users unless it meets this standard and has
a model card signed off by the Head of Data Science (Blueprint sections 01, 05, 11).
**Status:** draft for sign-off.

## 1. Data
- Point-in-time inputs only, read as published on each date (ADR 0002). Release dates from the
  source's real calendar; unknown dates err late.
- Every input passes the release-schedule check (on schedule, not discontinued, delays declared)
  and carries its origin. Sample or synthetic data never enters training or evaluation.

## 2. Labels
- Direction over a fixed horizon (1 week, 1 month) with a no-trade band, so tiny moves are not
  counted as wins; triple-barrier labels (target, stop, time) for trade-like evaluation;
  volatility-scaled returns for regression.

## 3. Validation
- Walk-forward testing with purging and embargo; combinatorial purged cross-validation for model
  selection. Random k-fold is never used on time series.
- Realistic costs: spreads by session, swaps and carry, slippage around releases.
- Baselines every model must beat after costs: random walk, carry, time-series momentum, PPP value.
- Results reported by year, regime and instrument, not only in aggregate.
- Every experiment is logged; report the deflated Sharpe ratio and the probability of backtest
  overfitting across all variants tried.

## 4. Metrics, always reported together
| Metric | Rule |
|---|---|
| Hit rate at a stated coverage | e.g. "57% on the 18% of weeks the model is confident"; never a hit rate without its coverage |
| Calibration | Brier score and reliability curve; stated 65% must be right about 65% of the time |
| Economic value after costs | Sharpe, Sortino, maximum drawdown, profit factor |
| Stability | Same metrics per year and regime |

Indicative honest ranges (Blueprint section 01): 51-55% daily, 54-60% weekly to monthly,
60-70% only for a high-conviction subset after forward testing. A result well above these is
treated as a leak or overfit until proven otherwise.

## 5. Scorecards
- The scorecard passes `python -m app.cli scorecard-bias`: mean difference between what users
  would have seen and complete information within ±0.25 per pillar.
- Phase 3 gate: scorecards add value over the baselines in walk-forward tests after costs.

## 6. Release to users
- At least 3-6 months of timestamped forward (paper) signals before any accuracy figure appears
  in marketing.
- A model card per model: purpose, data, training window, validation results, known failure
  modes, owner, approval date.
- Shadow mode before release: live predictions logged without being shown; they must match the
  backtest's behaviour.
- Drift monitoring and monthly retraining; quarterly model review.
