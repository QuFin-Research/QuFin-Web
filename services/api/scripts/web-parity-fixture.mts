// Regenerates tests/fixtures/web_parity.json from the web app's TypeScript mock data and
// backtest engine, so the Python port can be checked against it.
//   node scripts/web-parity-fixture.mts > tests/fixtures/web_parity.json
import {
  ASSETS,
  countryScores,
  driversFor,
  getSeries,
  hitRateFor,
  regimeFor
} from '../../../apps/web/src/features/market/lib/mock-data.ts';
import { backtestDecisionRule, runBacktest } from '../../../apps/web/src/features/backtest/lib/engine.ts';

const STRATEGIES = ['all-signals', 'high-conviction', 'buy-hold'] as const;
const DIRECTIONS = ['long', 'short'] as const;

const assets: Record<string, unknown> = {};
for (const a of ASSETS) {
  const s = getSeries(a.symbol)!;
  const last = s.signals[s.signals.length - 1];
  assets[a.symbol] = {
    candleCount: s.candles.length,
    firstCandle: s.candles[0],
    lastCandle: s.candles[s.candles.length - 1],
    lastSignal: last,
    regime: regimeFor(s.candles),
    hitRate: hitRateFor(s),
    drivers: driversFor(a, last),
    strategy: STRATEGIES.map((strategy) => ({
      strategy,
      stats: runBacktest({ candles: s.candles, signals: s.signals, strategy, minEdge: 0.05, rebalanceDays: 5, costBps: 3, lookbackDays: 504 }).stats
    })),
    rule: DIRECTIONS.map((direction) => {
      const r = backtestDecisionRule(s.candles, s.signals, { direction, stopPct: 0.01, targetPct: 0.02, maxHoldDays: 10, minEdge: 0.05, costBps: 2 });
      return {
        direction,
        trades: r.trades.length,
        firstTrade: r.trades[0] ?? null,
        winRate: r.winRate,
        avgR: r.avgR,
        profitFactor: Number.isFinite(r.profitFactor) ? r.profitFactor : null,
        finalCumR: r.curve.at(-1)?.cumR ?? 0
      };
    })
  };
}

console.log(JSON.stringify({ countries: countryScores(), assets }, null, 1));
