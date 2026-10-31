'use client';

import { useQuery } from '@tanstack/react-query';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { marketQueries } from '@/features/market/api/queries';
import { cn } from '@/lib/utils';

/** Where a number comes from. "sample": generated for development, not market data. */
export type DataOrigin = 'live' | 'sample';

export const SAMPLE_DATA_NOTE =
  'Sample data generated for development: not market data and not a trading signal.';

/** Marks one card or value as sample data. Shown whether or not the user is signed in. */
export function SampleDataBadge({ className }: { className?: string }) {
  return (
    <Badge variant='destructive' title={SAMPLE_DATA_NOTE} className={cn('shrink-0', className)}>
      Sample data
    </Badge>
  );
}

/**
 * Site-wide warning while prices and signals are sample data. It stays until the API reports
 * live market data for every asset, and shows while that is still loading or unknown.
 */
export function SampleDataBanner() {
  const { data: snapshots } = useQuery(marketQueries.snapshots());
  const live = !!snapshots?.length && snapshots.every((s) => s.data === 'live');
  if (live) return null;
  return (
    <div className='px-4 pt-3 md:px-6'>
      <Alert variant='destructive'>
        <AlertTitle>Prices and signals are sample data. Do not trade on them.</AlertTitle>
        <AlertDescription>
          Prices, charts, signals, hit rates, drivers, backtests and decision tests are generated
          for development; they are not market data and not trading signals. Live data: Macro data,
          Positioning and the US macro scorecard.
        </AlertDescription>
      </Alert>
    </div>
  );
}
