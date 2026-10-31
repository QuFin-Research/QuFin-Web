'use client';

import { useState } from 'react';
import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { CartesianGrid, Line, LineChart, XAxis, YAxis } from 'recharts';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
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
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
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
import { macroQueries } from '../api/queries';
import { macroAvailable } from '../api/service';
import type { MacroSeriesSummary } from '../api/types';

const chartConfig = {
  latest: { label: 'Latest', color: 'var(--chart-1)' },
  asOf: { label: 'As published then', color: 'var(--chart-3)' }
} satisfies ChartConfig;

const fmt = (v: number | null | undefined) =>
  v === null || v === undefined ? '—' : v.toLocaleString('en-US', { maximumFractionDigits: 3 });

/** Five years back from the series' last period keeps the chart readable. */
function chartStart(series: MacroSeriesSummary) {
  if (!series.lastPeriod) return undefined;
  const d = new Date(`${series.lastPeriod}T00:00:00Z`);
  d.setUTCFullYear(d.getUTCFullYear() - 5);
  return d.toISOString().slice(0, 10);
}

function SetupHint() {
  return (
    <Empty className='border'>
      <EmptyHeader>
        <EmptyTitle>No macro data yet</EmptyTitle>
        <EmptyDescription>
          {macroAvailable ? (
            <>
              Load the FRED/ALFRED series with a free FRED API key: set QUFIN_FRED_API_KEY in
              services/api/.env, then run{' '}
              <code className='bg-muted rounded px-1 font-mono text-xs'>
                uv run --directory services/api python -m app.cli ingest-fred
              </code>
            </>
          ) : (
            'Macro data comes from the QuFin API. Set NEXT_PUBLIC_API_URL to connect it.'
          )}
        </EmptyDescription>
      </EmptyHeader>
    </Empty>
  );
}

export function MacroView() {
  const { data: list, error } = useQuery(macroQueries.list());
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [asOf, setAsOf] = useState('');
  const [period, setPeriod] = useState<string | null>(null);

  const selected = list?.find((s) => s.id === selectedId) ?? list?.[0];
  const start = selected ? chartStart(selected) : undefined;

  const latest = useQuery({
    ...macroQueries.series(selected?.id ?? '', { start }),
    enabled: !!selected,
    placeholderData: keepPreviousData
  });
  const past = useQuery({
    ...macroQueries.series(selected?.id ?? '', { start, asOf }),
    enabled: !!selected && !!asOf,
    placeholderData: keepPreviousData
  });
  const revisionPeriod = period ?? latest.data?.observations.at(-1)?.period ?? null;
  const revisions = useQuery({
    ...macroQueries.revisions(selected?.id ?? '', revisionPeriod ?? ''),
    enabled: !!selected && !!revisionPeriod
  });

  if (error) {
    return (
      <Empty className='border'>
        <EmptyHeader>
          <EmptyTitle>Could not load macro data</EmptyTitle>
          <EmptyDescription>{error.message}</EmptyDescription>
        </EmptyHeader>
      </Empty>
    );
  }
  if (!list) return <Skeleton className='h-96 w-full rounded-xl' />;
  if (list.length === 0 || !selected) return <SetupHint />;

  const pastByPeriod = new Map(
    (asOf ? past.data?.observations : [])?.map((o) => [o.period, o.value]) ?? []
  );
  const chartData = (latest.data?.observations ?? []).map((o) => ({
    period: o.period,
    latest: o.value,
    asOf: pastByPeriod.get(o.period) ?? null
  }));
  const recent = (latest.data?.observations ?? []).slice(-12).toReversed();

  return (
    <div className='flex flex-col gap-4'>
      <Card>
        <CardHeader>
          <CardTitle>Series</CardTitle>
          <CardDescription>
            Every published vintage is stored, so any date can be replayed exactly as it was known
            then.
          </CardDescription>
        </CardHeader>
        <CardContent className='px-0'>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className='pl-4'>Series</TableHead>
                <TableHead>Pillar</TableHead>
                <TableHead className='hidden md:table-cell'>Units</TableHead>
                <TableHead className='text-right'>Latest period</TableHead>
                <TableHead className='hidden pr-4 text-right sm:table-cell'>Vintage rows</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {list.map((s) => (
                <TableRow
                  key={s.id}
                  className={cn('cursor-pointer', s.id === selected.id && 'bg-muted/60')}
                  onClick={() => {
                    setSelectedId(s.id);
                    setPeriod(null);
                  }}
                >
                  <TableCell className='pl-4'>
                    <button type='button' className='text-left' aria-pressed={s.id === selected.id}>
                      <span className='font-mono text-sm font-medium'>{s.id}</span>
                      <span className='text-muted-foreground block max-w-80 truncate text-xs'>
                        {s.title}
                      </span>
                    </button>
                  </TableCell>
                  <TableCell>
                    <Badge variant='outline' className='capitalize'>
                      {s.dimension}
                    </Badge>
                  </TableCell>
                  <TableCell className='text-muted-foreground hidden max-w-56 truncate text-xs md:table-cell'>
                    {s.units}
                  </TableCell>
                  <TableCell className='text-right font-mono text-xs tabular-nums'>
                    {s.lastPeriod ?? '—'}
                  </TableCell>
                  <TableCell className='hidden pr-4 text-right font-mono text-xs tabular-nums sm:table-cell'>
                    {s.vintageRows.toLocaleString('en-US')}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <div className='grid grid-cols-1 gap-4 xl:grid-cols-3'>
        <Card className='xl:col-span-2'>
          <CardHeader>
            <CardTitle>{selected.title}</CardTitle>
            <CardDescription>
              {selected.units} · {selected.frequency} · {selected.seasonalAdjustment}
            </CardDescription>
          </CardHeader>
          <CardContent className='flex flex-col gap-4'>
            <div className='flex flex-wrap items-end gap-3'>
              <div className='flex flex-col gap-1.5'>
                <Label htmlFor='macro-asof'>As published on</Label>
                <Input
                  id='macro-asof'
                  type='date'
                  className='w-44'
                  value={asOf}
                  onChange={(e) => setAsOf(e.target.value)}
                />
              </div>
              {asOf && (
                <Button variant='ghost' size='sm' onClick={() => setAsOf('')}>
                  Clear
                </Button>
              )}
              <p className='text-muted-foreground max-w-md text-xs'>
                Pick a date to overlay the data as it was published that day. Gaps and differences
                are later releases and revisions a backtest must not see.
              </p>
            </div>
            {latest.isPending ? (
              <Skeleton className='h-72 w-full' />
            ) : (
              <ChartContainer config={chartConfig} className='aspect-auto h-72 w-full'>
                <LineChart data={chartData} margin={{ left: 0, right: 8, top: 8 }}>
                  <CartesianGrid vertical={false} strokeDasharray='3 3' />
                  <XAxis
                    dataKey='period'
                    tickLine={false}
                    axisLine={false}
                    minTickGap={56}
                    tickFormatter={(v: string) => v.slice(0, 7)}
                  />
                  <YAxis
                    tickLine={false}
                    axisLine={false}
                    width={56}
                    domain={['auto', 'auto']}
                    tickFormatter={(v: number) => fmt(v)}
                  />
                  <ChartTooltip content={<ChartTooltipContent indicator='line' />} />
                  {asOf && <ChartLegend content={<ChartLegendContent />} />}
                  <Line
                    dataKey='latest'
                    stroke='var(--color-latest)'
                    dot={false}
                    strokeWidth={2}
                    connectNulls
                  />
                  {asOf && (
                    <Line
                      dataKey='asOf'
                      stroke='var(--color-asOf)'
                      strokeDasharray='4 3'
                      dot={false}
                      strokeWidth={1.75}
                    />
                  )}
                </LineChart>
              </ChartContainer>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Revisions</CardTitle>
            <CardDescription>
              {revisionPeriod
                ? `How the ${revisionPeriod} figure changed after its first print.`
                : 'Pick a period.'}
            </CardDescription>
          </CardHeader>
          <CardContent className='flex flex-col gap-4'>
            {revisions.data ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Published</TableHead>
                    <TableHead className='text-right'>Value</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {revisions.data.revisions.map((r, i) => (
                    <TableRow key={r.realtimeStart}>
                      <TableCell className='font-mono text-xs tabular-nums'>
                        {r.realtimeStart}
                        {i === 0 && <span className='text-muted-foreground ml-2'>first print</span>}
                        {r.realtimeEnd === null && (
                          <span className='text-muted-foreground ml-2'>current</span>
                        )}
                      </TableCell>
                      <TableCell className='text-right font-mono tabular-nums'>
                        {fmt(r.value)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <Skeleton className='h-24 w-full' />
            )}
            <div>
              <h3 className='mb-1.5 text-sm font-medium'>Recent periods</h3>
              <div className='flex flex-wrap gap-1.5'>
                {recent.map((o) => (
                  <Button
                    key={o.period}
                    size='xs'
                    variant={o.period === revisionPeriod ? 'default' : 'outline'}
                    className='font-mono'
                    onClick={() => setPeriod(o.period)}
                  >
                    {o.period.slice(0, 7)}
                  </Button>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
