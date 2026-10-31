// ============================================================
// Positioning Service — CFTC Commitments of Traders via the QuFin API
// ============================================================
//   GET /v1/positioning?asOf=
//   GET /v1/positioning/{symbol}?weeks=&asOf=
//
// Positioning data only exists in the API (ingested from the CFTC); without
// NEXT_PUBLIC_API_URL there is nothing to show.
// ============================================================

import { apiClient, isApiConfigured } from '@/lib/api-client';
import type { PositioningHistory, PositioningSnapshot } from './types';

export const positioningAvailable = isApiConfigured;

export async function getPositioning(): Promise<PositioningSnapshot[]> {
  if (!positioningAvailable) return [];
  return apiClient<PositioningSnapshot[]>('/v1/positioning');
}

export async function getPositioningHistory(
  symbol: string,
  weeks: number
): Promise<PositioningHistory> {
  return apiClient<PositioningHistory>(
    `/v1/positioning/${encodeURIComponent(symbol)}?weeks=${weeks}`
  );
}
