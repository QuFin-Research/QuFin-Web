import { queryOptions } from '@tanstack/react-query';
import {
  getComparison,
  getMacroRevisions,
  getMacroSeries,
  getMacroSeriesList,
  getStudio,
  getStudioCatalog,
  getStudioCountries
} from './service';
import type { ComparableConcept, MacroSeriesFilters, StudioQuery } from './types';

export const macroQueries = {
  all: () => ['macro'] as const,
  list: () =>
    queryOptions({
      queryKey: [...macroQueries.all(), 'list'] as const,
      queryFn: () => getMacroSeriesList()
    }),
  series: (id: string, filters: MacroSeriesFilters) =>
    queryOptions({
      queryKey: [...macroQueries.all(), 'series', id, filters] as const,
      queryFn: () => getMacroSeries(id, filters)
    }),
  compare: (concept: ComparableConcept) =>
    queryOptions({
      queryKey: [...macroQueries.all(), 'compare', concept] as const,
      queryFn: () => getComparison(concept)
    }),
  revisions: (id: string, period: string) =>
    queryOptions({
      queryKey: [...macroQueries.all(), 'revisions', id, period] as const,
      queryFn: () => getMacroRevisions(id, period)
    })
};

export const studioQueries = {
  all: () => ['studio'] as const,
  catalog: () =>
    queryOptions({
      queryKey: [...studioQueries.all(), 'catalog'] as const,
      queryFn: () => getStudioCatalog()
    }),
  countries: () =>
    queryOptions({
      queryKey: [...studioQueries.all(), 'countries'] as const,
      queryFn: () => getStudioCountries()
    }),
  result: (query: StudioQuery) =>
    queryOptions({
      queryKey: [...studioQueries.all(), 'result', query] as const,
      queryFn: () => getStudio(query)
    })
};
