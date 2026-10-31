// ============================================================
// Backtest Service — Data Access Layer
// ============================================================
// With NEXT_PUBLIC_API_URL set, backtests run on the server:
//   POST /v1/backtests  { kind: 'strategy' | 'decision-rule', ... }
// (requires a signed-in user). Without it, the same engine runs in the
// browser on the mock series (src/features/backtest/lib/engine.ts).
// ============================================================

import { apiClient, isApiConfigured } from '@/lib/api-client';
import { getAssetDetail } from '@/features/market/api/service';
import { backtestDecisionRule, runBacktest } from '../lib/engine';
import type {
  BacktestResult,
  DecisionRuleBacktestParams,
  RuleBacktestResult,
  StrategyBacktestParams
} from './types';

async function seriesFor(symbol: string) {
  const detail = await getAssetDetail(symbol);
  if (!detail) throw new Error(`Unknown symbol ${symbol}`);
  return detail;
}

export async function runStrategyBacktest(params: StrategyBacktestParams): Promise<BacktestResult> {
  if (isApiConfigured) {
    const { equity, stats } = await apiClient<BacktestResult>('/v1/backtests', {
      method: 'POST',
      body: JSON.stringify({ kind: 'strategy', ...params })
    });
    return { equity, stats };
  }
  const { symbol, ...settings } = params;
  const { candles, signals } = await seriesFor(symbol);
  return runBacktest({ candles, signals, ...settings });
}

export async function runDecisionRuleBacktest(
  params: DecisionRuleBacktestParams
): Promise<RuleBacktestResult> {
  if (isApiConfigured) {
    const result = await apiClient<
      Omit<RuleBacktestResult, 'profitFactor'> & { profitFactor: number | null }
    >('/v1/backtests', {
      method: 'POST',
      body: JSON.stringify({ kind: 'decision-rule', ...params })
    });
    // JSON has no Infinity: the API sends null when there are wins and no losses.
    return {
      trades: result.trades,
      winRate: result.winRate,
      avgR: result.avgR,
      expectancyPct: result.expectancyPct,
      profitFactor: result.profitFactor ?? Infinity,
      curve: result.curve
    };
  }
  const { symbol, ...rule } = params;
  const { candles, signals } = await seriesFor(symbol);
  return backtestDecisionRule(candles, signals, rule);
}
