import { Suspense } from 'react';
import { HydrationBoundary, dehydrate } from '@tanstack/react-query';
import PageContainer from '@/components/layout/page-container';
import { Skeleton } from '@/components/ui/skeleton';
import { marketQueries } from '@/features/market/api/queries';
import { SignalsTable } from '@/features/overview/components/overview';
import { getQueryClient } from '@/lib/query-client';

export const metadata = {
  title: 'Markets'
};

export default function MarketsPage() {
  const queryClient = getQueryClient();
  void queryClient.prefetchQuery(marketQueries.snapshots());

  return (
    <PageContainer
      pageTitle='Markets'
      pageDescription='Pick an asset to review its signal, plan a trade and backtest your decision.'
    >
      <HydrationBoundary state={dehydrate(queryClient)}>
        <Suspense fallback={<Skeleton className='h-[520px] w-full rounded-xl' />}>
          <SignalsTable />
        </Suspense>
      </HydrationBoundary>
    </PageContainer>
  );
}
