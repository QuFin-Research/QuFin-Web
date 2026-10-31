import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { Direction } from '@/features/market/api/types';

// Decisions persist in this browser until the backend exists.
// Replace with POST/GET /v1/decisions once auth and the API are in place.

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
};

type JournalState = {
  decisions: Decision[];
  addDecision: (decision: Omit<Decision, 'id' | 'createdAt'>) => Decision;
  removeDecision: (id: string) => void;
};

export const useJournalStore = create<JournalState>()(
  persist(
    (set) => ({
      decisions: [],
      addDecision: (input) => {
        const decision: Decision = {
          ...input,
          id: crypto.randomUUID(),
          createdAt: new Date().toISOString()
        };
        set((state) => ({ decisions: [decision, ...state.decisions] }));
        return decision;
      },
      removeDecision: (id) =>
        set((state) => ({ decisions: state.decisions.filter((d) => d.id !== id) }))
    }),
    { name: 'qufin-journal', version: 1 }
  )
);
