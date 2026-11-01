'use client';

import { SampleDataBadge } from '@/components/sample-data';
import { useSuspenseQuery } from '@tanstack/react-query';
import { notFound } from 'next/navigation';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { marketQueries } from '../api/queries';
import { formatPrice } from '../lib/format';
import { DecisionPanel } from './decision-panel';
import { PriceChart } from './price-chart';
import { ChangeText } from './signal-badge';
import { SignalPanel } from './signal-panel';

export function AssetView({ symbol }: { symbol: string }) {
  const { data: detail } = useSuspenseQuery(marketQueries.asset(symbol));
  if (!detail) notFound();
  const { asset } = detail;

  return (
    <div className='flex flex-col gap-4'>
      <div className='flex flex-wrap items-end justify-between gap-3'>
        <div>
          <div className='flex items-center gap-2'>
            <h2 className='text-3xl font-bold tracking-tight'>{asset.symbol}</h2>
            <Badge variant='outline'>{asset.assetClass}</Badge>
          </div>
          <p className='text-muted-foreground text-sm'>{asset.name}</p>
        </div>
        <div className='text-right'>
          <div className='font-mono text-2xl tabular-nums'>
            {formatPrice(detail.lastPrice, asset.precision)}
          </div>
          <ChangeText value={detail.changePct} className='text-sm' />
        </div>
      </div>

      <div className='grid grid-cols-1 gap-4 xl:grid-cols-5'>
        <div className='flex flex-col gap-4 xl:col-span-3'>
          <Card>
            <CardHeader>
              <CardTitle className='flex items-center gap-2'>
                Daily price
                <SampleDataBadge origin={detail.data} />
              </CardTitle>
            </CardHeader>
            <CardContent>
              <PriceChart
                candles={detail.candles}
                signals={detail.signals}
                precision={asset.precision}
              />
            </CardContent>
          </Card>
          <SignalPanel detail={detail} />
        </div>
        <div className='xl:col-span-2'>
          <DecisionPanel detail={detail} />
        </div>
      </div>
    </div>
  );
}
