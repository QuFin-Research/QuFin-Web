'use client';

import { useState } from 'react';
import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { CartesianGrid, Line, LineChart, XAxis, YAxis } from 'recharts';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
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
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { FRESHNESS_LABEL } from '@/lib/data-quality';
import { cn } from '@/lib/utils';
import { macroQueries } from '../api/queries';
import { macroAvailable } from '../api/service';
import type { BusinessCycle, MacroSeriesSummary, SeriesChange } from '../api/types';

type CycleFilter = BusinessCycle | 'all';

const CYCLES: { value: CycleFilter; label: string; hint: string }[] = [
  { value: 'all', label: 'All', hint: 'Every series in the point-in-time store.' },
  {
    value: 'leading',
    label: 'Leading',
    hint: 'Tend to turn before the economy: orders, permits, hours, claims, the yield curve, sentiment.'
  },
  {
    value: 'coincident',
    label: 'Coincident',
    hint: 'Move with the economy: output, income, sales and payrolls.'
  },
  {
    value: 'lagging',
    label: 'Lagging',
    hint: 'Turn after the economy: unemployment duration, unit labour costs, services inflation, credit.'
  }
];

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

const formatChange = (c: SeriesChange) =>
  `${c.value > 0 ? '+' : ''}${c.value.toLocaleString('en-US', { maximumFractionDigits: 2 })}${c.unit === 'pt' ? ' pt' : '%'}`;

/** Latest moves: percent for quantities, points for rates and indexes, in one vintage. */
function ChangeCell({ series }: { series: MacroSeriesSummary }) {
  if (series.changes.length === 0) return <span className='text-muted-foreground'>—</span>;
  return (
    <div className='flex flex-col items-end gap-0.5'>
      {series.changes.map((c) => (
        <span
          key={c.horizon}
          className={cn(
            c.value > 0 ? 'text-bull' : c.value < 0 ? 'text-bear' : 'text-muted-foreground'
          )}
          title={c.unit === '% ann.' ? 'Annualised' : undefined}
        >
          <span className='text-muted-foreground mr-1'>{c.horizon}</span>
          {formatChange(c)}
          {c.unit === '% ann.' ? ' ann.' : ''}
        </span>
      ))}
      {series.publishedAsChange && (
        <span className='text-muted-foreground'>published as a growth rate</span>
      )}
    </div>
  );
}

function StatusBadge({ series }: { series: MacroSeriesSummary }) {
  const f = series.freshness;
  return (
    <Badge
      variant={f.usable ? 'outline' : 'destructive'}
      title={f.reason}
      className='whitespace-nowrap'
    >
      {FRESHNESS_LABEL[f.status]}
      {f.status === 'overdue' && f.daysOverdue > 0 ? ` ${f.daysOverdue}d` : ''}
    </Badge>
  );
}

/** Series that must not be used, and series that reach QuFin late (lower weight). */
function DataChecks({ list }: { list: MacroSeriesSummary[] }) {
  const unusable = list.filter((s) => !s.freshness.usable);
  const delayed = list.filter((s) => s.freshness.usable && s.timeliness.fredDelayDays > 0);
  const late = list
    .filter((s) => s.freshness.usable && s.timeliness.weight < 0.75)
    .toSorted((a, b) => a.timeliness.weight - b.timeliness.weight);
  return (
    <div className='flex flex-col gap-3'>
      {unusable.length > 0 && (
        <Alert variant='destructive'>
          <AlertTitle>
            {unusable.length} series not usable: excluded from signals and scorecards
          </AlertTitle>
          <AlertDescription>
            <ul className='list-disc pl-4'>
              {unusable.map((s) => (
                <li key={s.id}>
                  <span className='font-mono'>{s.id}</span> ({s.sourceName ?? 'unknown source'}):{' '}
                  {s.freshness.reason}
                </li>
              ))}
            </ul>
          </AlertDescription>
        </Alert>
      )}
      <Alert>
        <AlertTitle>
          {list.length - unusable.length} of {list.length} series are on their release schedule
        </AlertTitle>
        <AlertDescription>
          <p>
            Each series is checked against its frequency and usual release lag after every load.
            Data that reaches QuFin long after its period ended counts for less in scorecards: the
            weight halves for every 60 days.
          </p>
          {delayed.length > 0 && (
            <ul className='mt-2 list-disc pl-4'>
              {delayed.map((s) => (
                <li key={s.id}>
                  <span className='font-mono'>{s.id}</span> ({s.sourceName}) reaches FRED{' '}
                  {s.timeliness.fredDelayDays} days after the source publishes it.{' '}
                  {s.timeliness.delayNote} Weight {s.timeliness.weight.toFixed(2)}.
                </li>
              ))}
            </ul>
          )}
          {late.length > 0 && (
            <p className='mt-2'>
              Lowest weights:{' '}
              {late
                .map(
                  (s) =>
                    `${s.id} ${s.timeliness.weight.toFixed(2)} (${s.timeliness.daysAfterPeriodEnd} days after its period ends)`
                )
                .join(', ')}
              .
            </p>
          )}
        </AlertDescription>
      </Alert>
    </div>
  );
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
  const [cycle, setCycle] = useState<CycleFilter>('all');
  const [asOf, setAsOf] = useState('');
  const [period, setPeriod] = useState<string | null>(null);

  const visible = cycle === 'all' ? list : list?.filter((s) => s.cycle === cycle);
  const selected = visible?.find((s) => s.id === selectedId) ?? visible?.[0] ?? list?.[0];
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
      <DataChecks list={list} />
      <Card>
        <CardHeader className='flex flex-row flex-wrap items-start justify-between gap-3'>
          <div className='flex flex-col gap-1.5'>
            <CardTitle>Series</CardTitle>
            <CardDescription>
              {CYCLES.find((c) => c.value === cycle)?.hint} Every published vintage is stored, so
              any date can be replayed exactly as it was known then.
            </CardDescription>
          </div>
          <Tabs value={cycle} onValueChange={(v) => setCycle(v as CycleFilter)}>
            <TabsList>
              {CYCLES.map((c) => (
                <TabsTrigger key={c.value} value={c.value}>
                  {c.label}
                </TabsTrigger>
              ))}
            </TabsList>
          </Tabs>
        </CardHeader>
        <CardContent className='px-0'>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className='pl-4'>Series</TableHead>
                <TableHead>Pillar</TableHead>
                <TableHead className='hidden lg:table-cell'>Cycle</TableHead>
                <TableHead className='text-right'>Latest period</TableHead>
                <TableHead className='text-right'>Change</TableHead>
                <TableHead className='hidden md:table-cell'>Released</TableHead>
                <TableHead className='hidden text-right sm:table-cell'>Weight</TableHead>
                <TableHead className='pr-4'>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(visible ?? []).map((s) => (
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
                      <span className='text-muted-foreground/80 block max-w-80 truncate text-xs'>
                        {s.sourceName}
                        {s.releaseName ? ` · ${s.releaseName}` : ''}
                      </span>
                    </button>
                  </TableCell>
                  <TableCell>
                    <Badge variant='outline' className='capitalize'>
                      {s.dimension}
                    </Badge>
                  </TableCell>
                  <TableCell className='text-muted-foreground hidden text-xs capitalize lg:table-cell'>
                    {s.cycle ?? '—'}
                  </TableCell>
                  <TableCell className='text-right font-mono text-xs tabular-nums'>
                    {s.lastPeriod ?? '—'}
                  </TableCell>
                  <TableCell className='text-right font-mono text-xs tabular-nums'>
                    <ChangeCell series={s} />
                  </TableCell>
                  <TableCell className='hidden font-mono text-xs tabular-nums md:table-cell'>
                    <span className='block'>{s.timeliness.latestSourceRelease ?? '—'}</span>
                    {s.timeliness.fredDelayDays > 0 && (
                      <span className='text-muted-foreground block'>
                        FRED ~{s.timeliness.latestFredRelease}
                      </span>
                    )}
                  </TableCell>
                  <TableCell className='hidden text-right font-mono text-xs tabular-nums sm:table-cell'>
                    {s.timeliness.weight.toFixed(2)}
                  </TableCell>
                  <TableCell className='pr-4'>
                    <StatusBadge series={s} />
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
              <span className='block'>
                Source: {selected.sourceName ?? 'unknown'}
                {selected.releaseName ? `, ${selected.releaseName}` : ''}. Latest period released{' '}
                {selected.timeliness.latestSourceRelease ?? '—'}
                {selected.timeliness.fredDelayDays > 0
                  ? ` by the source, about ${selected.timeliness.latestFredRelease} on FRED`
                  : ''}
                . {selected.freshness.reason}.
              </span>
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
