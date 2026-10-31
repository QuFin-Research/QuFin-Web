'use client';

import { useState } from 'react';
import Link from 'next/link';
import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { Bar, CartesianGrid, ComposedChart, Line, ReferenceLine, XAxis, YAxis } from 'recharts';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig
} from '@/components/ui/chart';
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from '@/components/ui/empty';
import { NativeSelect, NativeSelectOption } from '@/components/ui/native-select';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from '@/components/ui/table';
import { cn } from '@/lib/utils';
import { positioningQueries } from '../api/queries';
import { positioningAvailable } from '../api/service';

const RANGES = [
  { weeks: 52, label: '1 year' },
  { weeks: 156, label: '3 years' },
  { weeks: 520, label: '10 years' }
];

const chartConfig = {
  netPctOi: { label: 'Net % of open interest', color: 'var(--chart-1)' },
  cotIndex: { label: 'COT index (3y)', color: 'var(--chart-3)' }
} satisfies ChartConfig;

const signed = (v: number) => `${v > 0 ? '+' : ''}${v.toLocaleString('en-US')}`;

/** Extremes of the 3-year range are where positioning gets crowded. */
function crowding(index: number | null) {
  if (index === null) return { label: 'Not enough history', tone: '' };
  if (index >= 90) return { label: 'Crowded long', tone: 'text-bull' };
  if (index <= 10) return { label: 'Crowded short', tone: 'text-bear' };
  return { label: 'Neutral', tone: 'text-muted-foreground' };
}

function IndexBar({ value }: { value: number | null }) {
  return (
    <div className='flex items-center gap-2'>
      <div className='bg-muted relative h-1.5 w-24 overflow-hidden rounded-full'>
        {value !== null && (
          <div
            className='bg-primary absolute top-0 h-full w-1.5 -translate-x-1/2 rounded-full'
            style={{ left: `${value}%` }}
          />
        )}
      </div>
      <span className='w-8 font-mono text-xs tabular-nums'>{value ?? '—'}</span>
    </div>
  );
}

export function PositioningView() {
  const { data: list, error } = useQuery(positioningQueries.list());
  const [symbol, setSymbol] = useState<string | null>(null);
  const [weeks, setWeeks] = useState(156);

  const selected = list?.find((s) => s.symbol === symbol) ?? list?.[0];
  const history = useQuery({
    ...positioningQueries.history(selected?.symbol ?? '', weeks),
    enabled: !!selected,
    placeholderData: keepPreviousData
  });

  if (error) {
    return (
      <Empty className='border'>
        <EmptyHeader>
          <EmptyTitle>Could not load positioning</EmptyTitle>
          <EmptyDescription>{error.message}</EmptyDescription>
        </EmptyHeader>
      </Empty>
    );
  }
  if (!list) return <Skeleton className='h-96 w-full rounded-xl' />;
  if (list.length === 0 || !selected) {
    return (
      <Empty className='border'>
        <EmptyHeader>
          <EmptyTitle>No positioning data yet</EmptyTitle>
          <EmptyDescription>
            {positioningAvailable ? (
              <>
                Load the CFTC reports (public, no key needed):{' '}
                <code className='bg-muted rounded px-1 font-mono text-xs'>
                  uv run --directory services/api python -m app.cli ingest-cftc
                </code>
              </>
            ) : (
              'Positioning comes from the QuFin API. Set NEXT_PUBLIC_API_URL to connect it.'
            )}
          </EmptyDescription>
        </EmptyHeader>
      </Empty>
    );
  }

  const reportDate = list[0].latest.reportDate;
  const releaseDate = list[0].latest.releaseDate;
  const unusable = list.filter((s) => !s.freshness.usable);

  return (
    <div className='flex flex-col gap-4'>
      {unusable.length > 0 && (
        <Alert variant='destructive'>
          <AlertTitle>
            CFTC reports overdue for {unusable.map((s) => s.symbol).join(', ')}: do not treat this
            positioning as current
          </AlertTitle>
          <AlertDescription>{unusable[0].freshness.reason}.</AlertDescription>
        </Alert>
      )}
      <Card>
        <CardHeader>
          <CardTitle>Large speculators</CardTitle>
          <CardDescription>
            CFTC non-commercial net positions as of {reportDate}, released {releaseDate}. Shown in
            each asset&apos;s direction (yen futures are flipped for USDJPY).
          </CardDescription>
        </CardHeader>
        <CardContent className='px-0'>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className='pl-4'>Asset</TableHead>
                <TableHead className='text-right'>Net contracts</TableHead>
                <TableHead className='text-right'>Weekly change</TableHead>
                <TableHead className='hidden text-right md:table-cell'>% of OI</TableHead>
                <TableHead>COT index (3y)</TableHead>
                <TableHead className='hidden pr-4 lg:table-cell'>Reading</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {list.map((s) => {
                const c = crowding(s.latest.cotIndex);
                return (
                  <TableRow
                    key={s.symbol}
                    className={cn('cursor-pointer', s.symbol === selected.symbol && 'bg-muted/60')}
                    onClick={() => setSymbol(s.symbol)}
                  >
                    <TableCell className='pl-4'>
                      <button
                        type='button'
                        className='text-left'
                        aria-pressed={s.symbol === selected.symbol}
                      >
                        <span className='font-mono text-sm font-medium'>{s.symbol}</span>
                        <span className='text-muted-foreground block max-w-56 truncate text-xs'>
                          {s.marketName}
                        </span>
                      </button>
                    </TableCell>
                    <TableCell
                      className={cn(
                        'text-right font-mono tabular-nums',
                        s.latest.net >= 0 ? 'text-bull' : 'text-bear'
                      )}
                    >
                      {signed(s.latest.net)}
                    </TableCell>
                    <TableCell className='text-muted-foreground text-right font-mono text-xs tabular-nums'>
                      {s.weeklyChange === null ? '—' : signed(s.weeklyChange)}
                    </TableCell>
                    <TableCell className='hidden text-right font-mono text-xs tabular-nums md:table-cell'>
                      {s.latest.netPctOi.toFixed(1)}%
                    </TableCell>
                    <TableCell>
                      <IndexBar value={s.latest.cotIndex} />
                    </TableCell>
                    <TableCell className={cn('hidden pr-4 text-xs lg:table-cell', c.tone)}>
                      {c.label}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className='flex flex-row flex-wrap items-start justify-between gap-3'>
          <div className='flex flex-col gap-1.5'>
            <CardTitle>
              <Link href={`/dashboard/markets/${selected.symbol}`} className='hover:underline'>
                {selected.symbol}
              </Link>{' '}
              positioning history
            </CardTitle>
            <CardDescription>
              Each week&apos;s COT index uses only the reports published up to that week.
            </CardDescription>
          </div>
          <NativeSelect
            size='sm'
            aria-label='History range'
            value={String(weeks)}
            onChange={(e) => setWeeks(Number(e.target.value))}
          >
            {RANGES.map((r) => (
              <NativeSelectOption key={r.weeks} value={r.weeks}>
                {r.label}
              </NativeSelectOption>
            ))}
          </NativeSelect>
        </CardHeader>
        <CardContent>
          {!history.data ? (
            <Skeleton className='h-72 w-full' />
          ) : (
            <ChartContainer config={chartConfig} className='aspect-auto h-72 w-full'>
              <ComposedChart data={history.data.points} margin={{ left: 0, right: 8, top: 8 }}>
                <CartesianGrid vertical={false} strokeDasharray='3 3' />
                <XAxis
                  dataKey='reportDate'
                  tickLine={false}
                  axisLine={false}
                  minTickGap={56}
                  tickFormatter={(v: string) => v.slice(0, 7)}
                />
                <YAxis
                  yAxisId='pct'
                  tickLine={false}
                  axisLine={false}
                  width={44}
                  tickFormatter={(v: number) => `${v}%`}
                />
                <YAxis
                  yAxisId='index'
                  orientation='right'
                  domain={[0, 100]}
                  tickLine={false}
                  axisLine={false}
                  width={32}
                />
                <ReferenceLine yAxisId='pct' y={0} stroke='var(--border)' />
                <ChartTooltip content={<ChartTooltipContent indicator='line' />} />
                <ChartLegend content={<ChartLegendContent />} />
                <Bar
                  yAxisId='pct'
                  dataKey='netPctOi'
                  fill='var(--color-netPctOi)'
                  fillOpacity={0.55}
                />
                <Line
                  yAxisId='index'
                  dataKey='cotIndex'
                  stroke='var(--color-cotIndex)'
                  dot={false}
                  strokeWidth={1.75}
                  connectNulls
                />
              </ComposedChart>
            </ChartContainer>
          )}
          <p className='text-muted-foreground mt-3 text-xs'>
            Source: CFTC Commitments of Traders, legacy futures-only report. Extreme readings show
            crowded positioning, which has historically been a weak contrarian signal, not a timing
            tool.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
