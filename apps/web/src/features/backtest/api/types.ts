import type { DataOrigin } from '@/components/sample-data';
import type {
  BacktestInput,
  BacktestResult as EngineBacktestResult,
  DecisionRule,
  RuleBacktestResult as EngineRuleBacktestResult
} from '../lib/engine';

export type {
  BacktestStats,
  DecisionRule,
  EquityPoint,
  RuleTrade,
  StrategyKind
} from '../lib/engine';

/** Where the prices and signals behind a backtest come from; 'sample' is not market data */
export type BacktestResult = EngineBacktestResult & { data: DataOrigin };
export type RuleBacktestResult = EngineRuleBacktestResult & { data: DataOrigin };

/** Strategy backtest settings; the price and signal history is looked up by symbol. */
export type StrategyBacktestParams = Omit<BacktestInput, 'candles' | 'signals'> & {
  symbol: string;
};

export type DecisionRuleBacktestParams = DecisionRule & { symbol: string };
