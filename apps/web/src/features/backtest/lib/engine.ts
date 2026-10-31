// ============================================================
// Backtest engine (client-side preview)
// ============================================================
// Runs in the browser on the mock series so the UI can be built and tested
// now. In production the same inputs go to POST /v1/backtests, which runs on
// point-in-time data with purged walk-forward validation on the server.
//
// Conventions: a signal is formed at day t's close and acts on day t+1's
// return (no look-ahead). Costs are charged on every change in position.
// ============================================================

import type { Candle, Direction, Signal } from '@/features/market/api/types';

export type StrategyKind = 'all-signals' | 'high-conviction' | 'buy-hold';

export type BacktestInput = {
  candles: Candle[];
  signals: Signal[];
  strategy: StrategyKind;
  /** Minimum |probUp − 0.5| needed to take a position */
  minEdge: number;
  /** Re-evaluate the position every N trading days */
  rebalanceDays: number;
  /** One-way cost in basis points (spread + commission + slippage) */
  costBps: number;
  /** Number of most recent trading days to test */
  lookbackDays: number;
};

export type EquityPoint = {
  time: string;
  strategy: number;
  benchmark: number;
  drawdown: number;
};

export type BacktestStats = {
  totalReturn: number;
  benchmarkReturn: number;
  cagr: number;
  annualVol: number;
  sharpe: number;
  maxDrawdown: number;
  hitRate: number;
  trades: number;
  exposure: number;
};

export type BacktestResult = { equity: EquityPoint[]; stats: BacktestStats };

const TRADING_DAYS = 252;

function targetPosition(signal: Signal, input: BacktestInput) {
  if (input.strategy === 'buy-hold') return 1;
  const edge = signal.probUp - 0.5;
  const threshold = input.strategy === 'high-conviction' ? Math.max(input.minEdge, 0.1) : input.minEdge;
  if (Math.abs(edge) < threshold) return 0;
  return edge > 0 ? 1 : -1;
}

export function runBacktest(input: BacktestInput): BacktestResult {
  const { candles, signals } = input;
  const start = Math.max(1, candles.length - input.lookbackDays);
  const cost = input.costBps / 10000;

  let equity = 1;
  let benchmark = 1;
  let peak = 1;
  let position = 0;
  let periodPnl = 0;
  let wins = 0;
  let periods = 0;
  let trades = 0;
  let daysInMarket = 0;
  let maxDrawdown = 0;
  const daily: number[] = [];
  const points: EquityPoint[] = [];

  for (let i = start; i < candles.length; i++) {
    const daysSinceStart = i - start;
    if (daysSinceStart % input.rebalanceDays === 0) {
      if (position !== 0) {
        periods++;
        if (periodPnl > 0) wins++;
      }
      periodPnl = 0;
      const next = targetPosition(signals[i - 1], input);
      if (next !== position) {
        equity *= 1 - cost * Math.abs(next - position);
        if (next !== 0) trades++;
        position = next;
      }
    }

    const ret = candles[i].close / candles[i - 1].close - 1;
    const pnl = position * ret;
    equity *= 1 + pnl;
    benchmark *= 1 + ret;
    periodPnl += pnl;
    daily.push(pnl);
    if (position !== 0) daysInMarket++;

    peak = Math.max(peak, equity);
    const dd = equity / peak - 1;
    maxDrawdown = Math.min(maxDrawdown, dd);
    points.push({ time: candles[i].time, strategy: equity, benchmark, drawdown: dd });
  }
  if (position !== 0) {
    periods++;
    if (periodPnl > 0) wins++;
  }

  const n = daily.length || 1;
  const mean = daily.reduce((s, r) => s + r, 0) / n;
  const sd = Math.sqrt(daily.reduce((s, r) => s + (r - mean) ** 2, 0) / n);
  const years = n / TRADING_DAYS;

  return {
    equity: points,
    stats: {
      totalReturn: equity - 1,
      benchmarkReturn: benchmark - 1,
      cagr: equity > 0 ? equity ** (1 / years) - 1 : -1,
      annualVol: sd * Math.sqrt(TRADING_DAYS),
      sharpe: sd > 0 ? (mean / sd) * Math.sqrt(TRADING_DAYS) : 0,
      maxDrawdown,
      hitRate: periods ? wins / periods : 0,
      trades,
      exposure: daysInMarket / n
    }
  };
}

// ------------------------------------------------------------
// Decision-rule backtest
// ------------------------------------------------------------
// "Backtest this decision": replays the user's trade plan (direction,
// stop and target distances, max holding days) on every past day where the
// QuFin signal agreed with that direction at the required conviction, and
// reports how that plan would have performed.

export type DecisionRule = {
  direction: Direction;
  /** Stop distance as a fraction of entry price, e.g. 0.01 = 1% */
  stopPct: number;
  /** Target distance as a fraction of entry price */
  targetPct: number;
  maxHoldDays: number;
  /** Only take setups where |probUp − 0.5| ≥ minEdge */
  minEdge: number;
  costBps: number;
};

export type RuleTrade = {
  entryTime: string;
  exitTime: string;
  outcome: 'target' | 'stop' | 'time';
  /** Return in R multiples (1R = stop distance), after costs */
  r: number;
};

export type RuleBacktestResult = {
  trades: RuleTrade[];
  winRate: number;
  avgR: number;
  expectancyPct: number;
  profitFactor: number;
  curve: { time: string; cumR: number }[];
};

export function backtestDecisionRule(
  candles: Candle[],
  signals: Signal[],
  rule: DecisionRule
): RuleBacktestResult {
  const trades: RuleTrade[] = [];
  const sign = rule.direction === 'long' ? 1 : -1;
  const costR = (2 * rule.costBps) / 10000 / rule.stopPct;

  let i = 0;
  while (i < candles.length - 1) {
    const s = signals[i];
    const agrees = (s.probUp >= 0.5 ? 1 : -1) === sign;
    if (!agrees || Math.abs(s.probUp - 0.5) < rule.minEdge) {
      i++;
      continue;
    }

    // Enter at the next day's open; exit on stop, target or time.
    const entry = candles[i + 1].open;
    const stop = entry * (1 - sign * rule.stopPct);
    const target = entry * (1 + sign * rule.targetPct);
    let exitIdx = Math.min(i + rule.maxHoldDays, candles.length - 1);
    let outcome: RuleTrade['outcome'] = 'time';
    let exitPrice = candles[exitIdx].close;

    for (let j = i + 1; j <= Math.min(i + rule.maxHoldDays, candles.length - 1); j++) {
      const c = candles[j];
      const hitStop = sign > 0 ? c.low <= stop : c.high >= stop;
      const hitTarget = sign > 0 ? c.high >= target : c.low <= target;
      // If both are touched on the same bar, assume the stop came first (conservative).
      if (hitStop) {
        outcome = 'stop';
        exitPrice = stop;
        exitIdx = j;
        break;
      }
      if (hitTarget) {
        outcome = 'target';
        exitPrice = target;
        exitIdx = j;
        break;
      }
    }

    const movePct = (sign * (exitPrice - entry)) / entry;
    trades.push({
      entryTime: candles[i + 1].time,
      exitTime: candles[exitIdx].time,
      outcome,
      r: movePct / rule.stopPct - costR
    });
    i = exitIdx + 1;
  }

  let cumR = 0;
  const curve = trades.map((t) => {
    cumR += t.r;
    return { time: t.exitTime, cumR: Number(cumR.toFixed(2)) };
  });
  const wins = trades.filter((t) => t.r > 0);
  const grossWin = wins.reduce((s, t) => s + t.r, 0);
  const grossLoss = Math.abs(trades.filter((t) => t.r <= 0).reduce((s, t) => s + t.r, 0));
  const avgR = trades.length ? cumR / trades.length : 0;

  return {
    trades,
    winRate: trades.length ? wins.length / trades.length : 0,
    avgR,
    expectancyPct: avgR * rule.stopPct,
    profitFactor: grossLoss > 0 ? grossWin / grossLoss : grossWin > 0 ? Infinity : 0,
    curve
  };
}
