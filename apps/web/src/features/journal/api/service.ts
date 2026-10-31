// ============================================================
// Journal Service — Data Access Layer
// ============================================================
// With NEXT_PUBLIC_API_URL set, decisions belong to the signed-in user:
//   GET /v1/decisions, POST /v1/decisions, DELETE /v1/decisions/{id}
// Without it, they persist in this browser (utils/store.ts). Browser
// storage only exists on the client, so call these from client code.
// ============================================================

import { apiClient, isApiConfigured } from '@/lib/api-client';
import { useJournalStore } from '../utils/store';
import type { Decision, NewDecision } from './types';

export async function getDecisions(): Promise<Decision[]> {
  if (isApiConfigured) return apiClient<Decision[]>('/v1/decisions');
  return useJournalStore.getState().decisions;
}

export async function createDecision(input: NewDecision): Promise<Decision> {
  if (isApiConfigured) {
    return apiClient<Decision>('/v1/decisions', { method: 'POST', body: JSON.stringify(input) });
  }
  return useJournalStore.getState().addDecision(input);
}

export async function deleteDecision(id: string): Promise<void> {
  if (isApiConfigured) {
    return apiClient<void>(`/v1/decisions/${encodeURIComponent(id)}`, { method: 'DELETE' });
  }
  useJournalStore.getState().removeDecision(id);
}
