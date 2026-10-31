import { queryOptions } from '@tanstack/react-query';
import { runDecisionRuleBacktest, runStrategyBacktest } from './service';
import type { DecisionRuleBacktestParams, StrategyBacktestParams } from './types';

// Backtests are deterministic for given inputs, so results never go stale.
export const backtestQueries = {
  all: () => ['backtests'] as const,
  strategy: (params: StrategyBacktestParams) =>
    queryOptions({
      queryKey: [...backtestQueries.all(), 'strategy', params] as const,
      queryFn: () => runStrategyBacktest(params),
      staleTime: Infinity
    }),
  decisionRule: (params: DecisionRuleBacktestParams) =>
    queryOptions({
      queryKey: [...backtestQueries.all(), 'decision-rule', params] as const,
      queryFn: () => runDecisionRuleBacktest(params),
      staleTime: Infinity
    })
};
