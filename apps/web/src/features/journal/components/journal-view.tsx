'use client';

import { SampleDataBadge } from '@/components/sample-data';
import Link from 'next/link';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Empty, EmptyContent, EmptyDescription, EmptyHeader, EmptyTitle } from '@/components/ui/empty';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from '@/components/ui/table';
import { Icons } from '@/components/icons';
import { marketQueries } from '@/features/market/api/queries';
import { formatPct, formatPrice } from '@/features/market/lib/format';
import { formatDate } from '@/lib/format';
import { cn } from '@/lib/utils';
import { journalMutations, journalQueries } from '../api/queries';
import type { Decision } from '../api/types';

function openR(d: Decision, lastPrice: number) {
  const sign = d.direction === 'long' ? 1 : -1;
  const r = (sign * (lastPrice - d.entry)) / Math.abs(d.entry - d.stop);
  // Avoid showing "-0.00R" from rounding when the price has not moved.
  return Math.abs(r) < 0.005 ? 0 : r;
}

export function JournalView() {
  const queryClient = useQueryClient();
  const { data: decisions, error } = useQuery(journalQueries.list());
  const { data: snapshots } = useQuery(marketQueries.snapshots());
  const remove = useMutation({
    ...journalMutations.delete(),
    onError: (e) => toast.error(`Could not remove the decision: ${e.message}`),
    onSettled: () => queryClient.invalidateQueries({ queryKey: journalQueries.all() })
  });

  if (error) {
    return (
      <Empty className='border'>
        <EmptyHeader>
          <EmptyTitle>Could not load your journal</EmptyTitle>
          <EmptyDescription>{error.message}</EmptyDescription>
        </EmptyHeader>
      </Empty>
    );
  }
  if (!decisions) return <Skeleton className='h-80 w-full rounded-xl' />;

  if (decisions.length === 0) {
    return (
      <Empty className='border'>
        <EmptyHeader>
          <EmptyTitle>No decisions yet</EmptyTitle>
          <EmptyDescription>
            Open an asset, plan your trade, backtest it, then log it here to track how it plays out.
          </EmptyDescription>
        </EmptyHeader>
        <EmptyContent>
          <Button nativeButton={false} render={<Link href='/dashboard/markets' aria-label='Browse markets' />}>
            Browse markets
          </Button>
        </EmptyContent>
      </Empty>
    );
  }

  const priced = decisions.map((d) => {
    const snap = snapshots?.find((s) => s.asset.symbol === d.symbol);
    return { d, snap, r: snap ? openR(d, snap.lastPrice) : null };
  });
  const withR = priced.filter((p) => p.r !== null);
  const totalR = withR.reduce((s, p) => s + (p.r ?? 0), 0);
  const aligned = decisions.filter((d) => (d.signalProbUp >= 0.5 ? 'long' : 'short') === d.direction).length;

  return (
    <div className='flex flex-col gap-4'>
      <div className='grid grid-cols-1 gap-4 sm:grid-cols-3'>
        <Card size='sm'>
          <CardHeader>
            <CardDescription>Open decisions</CardDescription>
            <CardTitle className='font-mono text-2xl tabular-nums'>{decisions.length}</CardTitle>
          </CardHeader>
        </Card>
        <Card size='sm'>
          <CardHeader>
            <CardDescription>Open result (sum of R)</CardDescription>
            <CardTitle className={cn('font-mono text-2xl tabular-nums', totalR >= 0 ? 'text-bull' : 'text-bear')}>
              {totalR >= 0 ? '+' : ''}
              {totalR.toFixed(2)}R
            </CardTitle>
          </CardHeader>
        </Card>
        <Card size='sm'>
          <CardHeader>
            <CardDescription>Agreed with QuFin signal</CardDescription>
            <CardTitle className='font-mono text-2xl tabular-nums'>
              {formatPct(aligned / decisions.length, 0, false)}
            </CardTitle>
          </CardHeader>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className='flex items-center gap-2'>
            Decisions
            {decisions.some((d) => d.data !== 'live') && <SampleDataBadge />}
          </CardTitle>
          <CardDescription>
            Marked to the latest close. 1R is the distance from entry to stop. Decisions logged on
            sample data are marked to sample prices, not the market.
          </CardDescription>
        </CardHeader>
        <CardContent className='px-0'>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className='pl-4'>Logged</TableHead>
                <TableHead>Asset</TableHead>
                <TableHead className='text-right'>Entry</TableHead>
                <TableHead className='text-right'>Stop / Target</TableHead>
                <TableHead className='text-right'>Last</TableHead>
                <TableHead className='text-right'>Open R</TableHead>
                <TableHead className='hidden lg:table-cell'>Backtest at entry</TableHead>
                <TableHead className='hidden xl:table-cell'>Note</TableHead>
                <TableHead className='pr-4'>
                  <span className='sr-only'>Actions</span>
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {priced.map(({ d, snap, r }) => {
                const p = snap?.asset.precision ?? 2;
                return (
                  <TableRow key={d.id}>
                    <TableCell className='text-muted-foreground pl-4 text-xs'>
                      {formatDate(d.createdAt, { month: 'short' })}
                    </TableCell>
                    <TableCell>
                      <Link href={`/dashboard/markets/${d.symbol}`} className='font-medium hover:underline'>
                        {d.symbol}
                      </Link>
                      <div>
                        <Badge
                          variant='outline'
                          className={cn('mt-1 border-transparent', d.direction === 'long' ? 'bg-bull/12 text-bull' : 'bg-bear/12 text-bear')}
                        >
                          {d.direction === 'long' ? 'Long' : 'Short'}
                        </Badge>
                      </div>
                    </TableCell>
                    <TableCell className='text-right font-mono tabular-nums'>{formatPrice(d.entry, p)}</TableCell>
                    <TableCell className='text-right font-mono text-xs tabular-nums'>
                      <div className='text-bear'>{formatPrice(d.stop, p)}</div>
                      <div className='text-bull'>{formatPrice(d.target, p)}</div>
                    </TableCell>
                    <TableCell className='text-right font-mono tabular-nums'>
                      {snap ? formatPrice(snap.lastPrice, p) : '—'}
                    </TableCell>
                    <TableCell
                      className={cn(
                        'text-right font-mono tabular-nums',
                        r !== null && (r >= 0 ? 'text-bull' : 'text-bear')
                      )}
                    >
                      {r === null ? '—' : `${r >= 0 ? '+' : ''}${r.toFixed(2)}R`}
                    </TableCell>
                    <TableCell className='text-muted-foreground hidden text-xs lg:table-cell'>
                      {d.backtest
                        ? `${d.backtest.trades} trades · ${formatPct(d.backtest.winRate, 0, false)} win · ${d.backtest.avgR.toFixed(2)}R avg`
                        : 'No matching history'}
                    </TableCell>
                    <TableCell className='text-muted-foreground hidden max-w-56 truncate text-xs xl:table-cell'>
                      {d.note || '—'}
                    </TableCell>
                    <TableCell className='pr-4 text-right'>
                      <Button
                        variant='ghost'
                        size='icon-sm'
                        aria-label={`Remove ${d.symbol} decision`}
                        disabled={remove.isPending && remove.variables === d.id}
                        onClick={() => remove.mutate(d.id)}
                      >
                        <Icons.trash />
                      </Button>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
