// ============================================================
// Market Service — Data Access Layer
// ============================================================
// This is the ONLY file to change when the FastAPI backend is ready.
// Queries (queries.ts) and components import from here and stay the same.
//
// Target endpoints (FastAPI, per the QuFin Platform Blueprint):
//   GET /v1/assets                     → getSnapshots()
//   GET /v1/assets/{symbol}            → getAssetDetail(symbol)
//   GET /v1/scorecards/countries       → getCountryScores()
// Replace each body with:  return apiClient<T>('/v1/...')
//
// Current: deterministic mock data (src/features/market/lib/mock-data.ts)
// ============================================================

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
    asset: toAsset(spec),
    lastPrice: last.close,
    changePct: (last.close / prev.close - 1) * 100,
    regime: regimeFor(candles),
    signal: signals[signals.length - 1],
    hitRate: hitRateFor(series)
  };
}

export async function getSnapshots(): Promise<AssetSnapshot[]> {
  return ASSETS.map((a) => snapshotFor(a.symbol)!);
}

export async function getAssetDetail(symbol: string): Promise<AssetDetail | null> {
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
  return countryScores();
}

export function listAssets(): Asset[] {
  return ASSETS.map(toAsset);
}
