import { Suspense } from 'react';
import { HydrationBoundary, dehydrate } from '@tanstack/react-query';
import { notFound } from 'next/navigation';
import PageContainer from '@/components/layout/page-container';
import { Skeleton } from '@/components/ui/skeleton';
import { marketQueries } from '@/features/market/api/queries';
import { listAssets } from '@/features/market/api/service';
import { AssetView } from '@/features/market/components/asset-view';
import { getQueryClient } from '@/lib/query-client';

type PageProps = { params: Promise<{ symbol: string }> };

export async function generateMetadata({ params }: PageProps) {
  const { symbol } = await params;
  return { title: symbol.toUpperCase() };
}

export default async function AssetPage({ params }: PageProps) {
  const symbol = (await params).symbol.toUpperCase();
  if (!listAssets().some((a) => a.symbol === symbol)) notFound();

  const queryClient = getQueryClient();
  void queryClient.prefetchQuery(marketQueries.asset(symbol));

  return (
    <PageContainer>
      <HydrationBoundary state={dehydrate(queryClient)}>
        <Suspense fallback={<Skeleton className='h-[720px] w-full rounded-xl' />}>
          <AssetView symbol={symbol} />
        </Suspense>
      </HydrationBoundary>
    </PageContainer>
  );
}
