import { queryOptions } from '@tanstack/react-query';
import { getAssetDetail, getCountryScores, getSnapshots } from './service';

// Reads: query key + fetcher in one place, shared by server prefetch and client hooks.
export const marketQueries = {
  all: () => ['market'] as const,
  snapshots: () =>
    queryOptions({
      queryKey: [...marketQueries.all(), 'snapshots'] as const,
      queryFn: () => getSnapshots()
    }),
  asset: (symbol: string) =>
    queryOptions({
      queryKey: [...marketQueries.all(), 'asset', symbol] as const,
      queryFn: () => getAssetDetail(symbol)
    }),
  countryScores: () =>
    queryOptions({
      queryKey: [...marketQueries.all(), 'country-scores'] as const,
      queryFn: () => getCountryScores()
    })
};
