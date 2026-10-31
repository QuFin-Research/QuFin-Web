import { queryOptions } from '@tanstack/react-query';
import { getPositioning, getPositioningHistory } from './service';

export const positioningQueries = {
  all: () => ['positioning'] as const,
  list: () =>
    queryOptions({
      queryKey: [...positioningQueries.all(), 'list'] as const,
      queryFn: () => getPositioning()
    }),
  history: (symbol: string, weeks: number) =>
    queryOptions({
      queryKey: [...positioningQueries.all(), 'history', symbol, weeks] as const,
      queryFn: () => getPositioningHistory(symbol, weeks)
    })
};
