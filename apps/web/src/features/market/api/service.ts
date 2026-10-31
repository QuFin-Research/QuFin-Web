// ============================================================
// Market Service — Data Access Layer
// ============================================================
// Queries (queries.ts) and components import from here and stay the same
// whichever source is active.
//
// With NEXT_PUBLIC_API_URL set, data comes from the QuFin API (services/api):
//   GET /v1/assets                     → getSnapshots()
//   GET /v1/assets/{symbol}            → getAssetDetail(symbol)
//   GET /v1/scorecards/countries       → getCountryScores()
//
// Without it, the deterministic mock (src/features/market/lib/mock-data.ts)
// serves the same numbers locally, so the app also runs offline.
// ============================================================

import { ApiError, apiClient, isApiConfigured } from '@/lib/api-client';
import {
  ASSETS,
  countryScores,
  driversFor,
  getSeries,
  hitRateFor,
  regimeFor
} from '../lib/mock-data';
import type { Asset, AssetDetail, AssetSnapshot, CountryScore } from './types';

function toAsset({ symbol, name, assetClass, precision }: Asset): Asset {
  return { symbol, name, assetClass, precision };
}

function snapshotFor(symbol: string): AssetSnapshot | undefined {
  const spec = ASSETS.find((a) => a.symbol === symbol);
  const series = getSeries(symbol);
  if (!spec || !series) return undefined;
  const { candles, signals } = series;
  const last = candles[candles.length - 1];
  const prev = candles[candles.length - 2];
  return {
    data: 'sample',
    asset: toAsset(spec),
    lastPrice: last.close,
    changePct: (last.close / prev.close - 1) * 100,
    regime: regimeFor(candles),
    signal: signals[signals.length - 1],
    hitRate: hitRateFor(series)
  };
}

export async function getSnapshots(): Promise<AssetSnapshot[]> {
  if (isApiConfigured) return apiClient<AssetSnapshot[]>('/v1/assets');
  return ASSETS.map((a) => snapshotFor(a.symbol)!);
}

export async function getAssetDetail(symbol: string): Promise<AssetDetail | null> {
  if (isApiConfigured) {
    try {
      return await apiClient<AssetDetail>(`/v1/assets/${encodeURIComponent(symbol)}`);
    } catch (error) {
      if (error instanceof ApiError && (error.status === 404 || error.status === 422)) return null;
      throw error;
    }
  }
  const snapshot = snapshotFor(symbol.toUpperCase());
  const series = getSeries(symbol.toUpperCase());
  if (!snapshot || !series) return null;
  return {
    ...snapshot,
    candles: series.candles,
    signals: series.signals,
    drivers: driversFor(snapshot.asset, snapshot.signal)
  };
}

export async function getCountryScores(): Promise<CountryScore[]> {
  if (isApiConfigured) return apiClient<CountryScore[]>('/v1/scorecards/countries');
  return countryScores();
}

/** Static asset universe (same list the API serves); used for routing and pickers. */
export function listAssets(): Asset[] {
  return ASSETS.map(toAsset);
}
