import type { BacktestInput, DecisionRule } from '../lib/engine';

export type {
  BacktestResult,
  BacktestStats,
  DecisionRule,
  EquityPoint,
  RuleBacktestResult,
  RuleTrade,
  StrategyKind
} from '../lib/engine';

/** Strategy backtest settings; the price and signal history is looked up by symbol. */
export type StrategyBacktestParams = Omit<BacktestInput, 'candles' | 'signals'> & {
  symbol: string;
};

export type DecisionRuleBacktestParams = DecisionRule & { symbol: string };
