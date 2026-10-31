import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { Decision, NewDecision } from '../api/types';

// Offline fallback for the journal: decisions persist in this browser when no
// API is configured. With the API, journal/api/service.ts uses /v1/decisions.

type JournalState = {
  decisions: Decision[];
  addDecision: (decision: NewDecision) => Decision;
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
          createdAt: new Date().toISOString(),
          // The offline app only has sample prices and signals.
          data: 'sample'
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
