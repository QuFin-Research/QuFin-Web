import type { DataOrigin } from '@/components/sample-data';
import type { Direction } from '@/features/market/api/types';

export type Decision = {
  id: string;
  symbol: string;
  direction: Direction;
  entry: number;
  stop: number;
  target: number;
  /** Risk per trade as a % of account */
  riskPct: number;
  maxHoldDays: number;
  /** QuFin signal at the time of the decision */
  signalProbUp: number;
  /** Rule-backtest summary captured when the decision was logged */
  backtest: { trades: number; winRate: number; avgR: number } | null;
  note: string;
  createdAt: string;
  /** Origin of the market data the decision was logged on; older entries lack it */
  data?: DataOrigin;
};

export type NewDecision = Omit<Decision, 'id' | 'createdAt' | 'data'>;
