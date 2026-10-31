import { queryOptions } from '@tanstack/react-query';
import { getMacroRevisions, getMacroSeries, getMacroSeriesList } from './service';
import type { MacroSeriesFilters } from './types';

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
  revisions: (id: string, period: string) =>
    queryOptions({
      queryKey: [...macroQueries.all(), 'revisions', id, period] as const,
      queryFn: () => getMacroRevisions(id, period)
    })
};
