// ============================================================
// Macro Service — point-in-time macro data from the QuFin API
// ============================================================
//   GET /v1/macro/series
//   GET /v1/macro/series/{id}?asOf=&start=
//   GET /v1/macro/series/{id}/revisions?period=
//
// Macro data only exists in the API (ingested from FRED/ALFRED); without
// NEXT_PUBLIC_API_URL there is nothing to show.
// ============================================================

import { apiClient, isApiConfigured } from '@/lib/api-client';
import type {
  Comparison,
  ComparableConcept,
  MacroRevisionHistory,
  MacroSeriesData,
  MacroSeriesFilters,
  MacroSeriesSummary,
  StudioCatalog,
  StudioCountry,
  StudioQuery,
  StudioResult
} from './types';

export const macroAvailable = isApiConfigured;

export async function getMacroSeriesList(): Promise<MacroSeriesSummary[]> {
  if (!macroAvailable) return [];
  return apiClient<MacroSeriesSummary[]>('/v1/macro/series');
}

export async function getMacroSeries(
  id: string,
  filters: MacroSeriesFilters = {}
): Promise<MacroSeriesData> {
  const params = new URLSearchParams();
  if (filters.asOf) params.set('asOf', filters.asOf);
  if (filters.start) params.set('start', filters.start);
  const query = params.size ? `?${params}` : '';
  return apiClient<MacroSeriesData>(`/v1/macro/series/${encodeURIComponent(id)}${query}`);
}

export async function getMacroRevisions(id: string, period: string): Promise<MacroRevisionHistory> {
  return apiClient<MacroRevisionHistory>(
    `/v1/macro/series/${encodeURIComponent(id)}/revisions?period=${encodeURIComponent(period)}`
  );
}

export async function getComparison(concept: ComparableConcept): Promise<Comparison> {
  return apiClient<Comparison>(`/v1/macro/compare/${concept}`);
}

export async function getStudioCatalog(): Promise<StudioCatalog> {
  return apiClient<StudioCatalog>('/v1/studio/catalog');
}

export async function getStudioCountries(): Promise<StudioCountry[]> {
  return apiClient<StudioCountry[]>('/v1/macro/countries');
}

export async function getStudio(query: StudioQuery): Promise<StudioResult> {
  const params = new URLSearchParams();
  if (query.frequency) params.set('frequency', query.frequency);
  params.set('metric', query.metric);
  params.set('years', String(query.years));
  if (query.mode === 'countries') {
    params.set('concept', query.concept);
    query.countries.forEach((c) => params.append('countries', c));
    return apiClient<StudioResult>(`/v1/studio/compare?${params}`);
  }
  params.set('country', query.country);
  query.seriesIds.forEach((id) => params.append('seriesIds', id));
  return apiClient<StudioResult>(`/v1/studio/overlay?${params}`);
}
