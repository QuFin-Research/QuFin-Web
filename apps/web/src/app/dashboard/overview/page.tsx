import { Suspense } from 'react';
import { HydrationBoundary, dehydrate } from '@tanstack/react-query';
import PageContainer from '@/components/layout/page-container';
import { Skeleton } from '@/components/ui/skeleton';
import { marketQueries } from '@/features/market/api/queries';
import {
  CountryScorecard,
  OverviewKpis,
  SignalsTable
} from '@/features/overview/components/overview';
import { AS_OF } from '@/features/market/lib/mock-data';
import { formatDate } from '@/lib/format';
import { getQueryClient } from '@/lib/query-client';

export const metadata = {
  title: 'Overview'
};

export default function OverviewPage() {
  const queryClient = getQueryClient();
  void queryClient.prefetchQuery(marketQueries.snapshots());
  void queryClient.prefetchQuery(marketQueries.countryScores());

  return (
    <PageContainer
      pageTitle='Market overview'
      pageDescription={`Signals and macro scores as of the ${formatDate(AS_OF)} close. Research and decision support, not investment advice.`}
    >
      <HydrationBoundary state={dehydrate(queryClient)}>
        <Suspense fallback={<Skeleton className='h-[600px] w-full rounded-xl' />}>
          <div className='flex flex-col gap-4'>
            <OverviewKpis />
            <div className='grid grid-cols-1 gap-4 2xl:grid-cols-5'>
              <div className='2xl:col-span-3'>
                <SignalsTable />
              </div>
              <div className='2xl:col-span-2'>
                <CountryScorecard />
              </div>
            </div>
          </div>
        </Suspense>
      </HydrationBoundary>
    </PageContainer>
  );
}
