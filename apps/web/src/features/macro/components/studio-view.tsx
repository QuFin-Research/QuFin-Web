'use client';

import { useMemo, useRef, useState } from 'react';
import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { CartesianGrid, Line, LineChart, XAxis, YAxis } from 'recharts';
import { Icons } from '@/components/icons';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { ChartContainer, ChartTooltip, type ChartConfig } from '@/components/ui/chart';
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from '@/components/ui/empty';
import { Input } from '@/components/ui/input';
import {
  NativeSelect,
  NativeSelectOptGroup,
  NativeSelectOption
} from '@/components/ui/native-select';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { cn } from '@/lib/utils';
import { studioQueries } from '../api/queries';
import { macroAvailable } from '../api/service';
import type {
  StudioCatalog,
  StudioCountry,
  StudioFrequency,
  StudioMetric,
  StudioQuery,
  StudioResult
} from '../api/types';
import {
  FREQUENCY_LABEL,
  SERIES_COLORS,
  canAdd,
  chartRows,
  flagEmoji,
  formatValue,
  frequencyState,
  selectionCounter,
  toCsv
} from '../lib/studio';

type Mode = 'countries' | 'indicators';

function download(name: string, blob: Blob) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
}

function exportPng(host: HTMLElement | null, name: string) {
  const svg = host?.querySelector('svg.recharts-surface');
  if (!svg) return;
  const { width, height } = svg.getBoundingClientRect();
  const copy = svg.cloneNode(true) as SVGElement;
  copy.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
  copy.setAttribute('width', String(width));
  copy.setAttribute('height', String(height));
  const image = new Image();
  image.addEventListener('load', () => {
    const canvas = document.createElement('canvas');
    canvas.width = width * 2;
    canvas.height = height * 2;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(image, 0, 0, canvas.width, canvas.height);
    canvas.toBlob((blob) => blob && download(name, blob));
  });
  image.src = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(
    new XMLSerializer().serializeToString(copy)
  )}`;
}

function CountryPicker({
  countries,
  available,
  selected,
  max,
  onChange
}: {
  countries: StudioCountry[];
  available: Set<string>;
  selected: string[];
  max: number;
  onChange: (next: string[]) => void;
}) {
  const [search, setSearch] = useState('');
  const byIso3 = new Map(countries.map((c) => [c.iso3, c]));
  const shown = countries.filter(
    (c) => available.has(c.iso3) && c.name.toLowerCase().includes(search.trim().toLowerCase())
  );
  const toggle = (iso3: string) =>
    onChange(
      selected.includes(iso3)
        ? selected.filter((c) => c !== iso3)
        : canAdd(selected.length, max)
          ? [...selected, iso3]
          : selected
    );
  return (
    <div className='space-y-2'>
      <div className='flex flex-wrap items-center gap-2'>
        <span className='text-sm font-medium'>{selectionCounter(selected.length, max)}</span>
        {selected.map((iso3) => (
          <Badge key={iso3} variant='secondary' className='gap-1'>
            {flagEmoji(byIso3.get(iso3)?.iso2 ?? '')} {byIso3.get(iso3)?.name ?? iso3}
            <button
              type='button'
              aria-label={`Remove ${byIso3.get(iso3)?.name ?? iso3}`}
              onClick={() => toggle(iso3)}
            >
              <Icons.close className='size-3' />
            </button>
          </Badge>
        ))}
      </div>
      <div className='relative'>
        <Icons.search className='text-muted-foreground absolute top-2.5 left-2.5 size-4' />
        <Input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder='Search countries'
          className='pl-8'
          aria-label='Search countries'
        />
      </div>
      <div className='grid max-h-48 grid-cols-2 gap-1 overflow-y-auto sm:grid-cols-3'>
        {shown.map((c) => {
          const on = selected.includes(c.iso3);
          const blocked = !on && !canAdd(selected.length, max);
          return (
            <button
              key={c.iso3}
              type='button'
              disabled={blocked}
              aria-pressed={on}
              title={blocked ? `At most ${max} countries` : undefined}
              onClick={() => toggle(c.iso3)}
              className={cn(
                'hover:bg-muted flex items-center gap-2 rounded-md border px-2 py-1 text-left text-sm',
                on && 'border-primary bg-primary/10',
                blocked && 'cursor-not-allowed opacity-40'
              )}
            >
              <span>{flagEmoji(c.iso2)}</span>
              <span className='truncate'>{c.name}</span>
            </button>
          );
        })}
        {shown.length === 0 && (
          <p className='text-muted-foreground col-span-full text-sm'>No country matches.</p>
        )}
      </div>
    </div>
  );
}

function FrequencyPills({
  allowed,
  value,
  onChange
}: {
  allowed: StudioFrequency[] | undefined;
  value: StudioFrequency | null;
  onChange: (f: StudioFrequency) => void;
}) {
  return (
    <div className='flex flex-wrap gap-1' role='group' aria-label='Frequency'>
      {frequencyState(allowed).map(({ value: f, enabled }) => (
        <Button
          key={f}
          type='button'
          size='sm'
          variant={value === f ? 'default' : 'outline'}
          disabled={!enabled}
          onClick={() => onChange(f)}
        >
          {FREQUENCY_LABEL[f]}
        </Button>
      ))}
    </div>
  );
}

type TooltipProps = {
  active?: boolean;
  payload?: { dataKey?: string | number; color?: string; value?: number | string }[];
  label?: string | number;
  result: StudioResult;
};

function StudioTooltip({ active, payload, label, result }: TooltipProps) {
  if (!active || !payload?.length) return null;
  return (
    <div className='bg-background rounded-md border p-2 text-xs shadow-md'>
      <div className='mb-1 font-medium'>{String(label)}</div>
      {payload.map((p) => {
        const s = result.series.find((x) => x.seriesId === p.dataKey);
        return (
          <div key={String(p.dataKey)} className='flex items-center gap-2'>
            <span className='size-2 rounded-full' style={{ background: p.color }} aria-hidden />
            <span className='flex-1'>{s?.label ?? String(p.dataKey)}</span>
            <span className='font-medium tabular-nums'>
              {typeof p.value === 'number' ? formatValue(p.value) : '—'}
              {s ? ` ${s.displayUnit}` : ''}
            </span>
            {s && <span className='text-muted-foreground'>{s.adjustment}</span>}
          </div>
        );
      })}
    </div>
  );
}

function StudioChart({
  result,
  host
}: {
  result: StudioResult;
  host: React.RefObject<HTMLDivElement | null>;
}) {
  const rows = useMemo(() => chartRows(result), [result]);
  const config: ChartConfig = Object.fromEntries(
    result.series.map((s, i) => [s.seriesId, { label: s.label, color: SERIES_COLORS[i] }])
  );
  const axes = [...new Set(result.series.map((s) => s.axis))];
  return (
    <div ref={host}>
      <ChartContainer config={config} className='h-96 w-full'>
        <LineChart data={rows} margin={{ left: 8, right: 8, top: 8 }}>
          <CartesianGrid vertical={false} />
          <XAxis dataKey='period' tickFormatter={(v: string) => v.slice(0, 7)} minTickGap={32} />
          {axes.map((axis, i) => (
            <YAxis
              key={axis}
              yAxisId={String(axis)}
              orientation={i % 2 === 0 ? 'left' : 'right'}
              hide={i > 1}
              width={64}
              tickFormatter={(v: number) => formatValue(v)}
              domain={['auto', 'auto']}
            />
          ))}
          <ChartTooltip cursor content={<StudioTooltip result={result} />} />
          {result.series.map((s, i) => (
            <Line
              key={s.seriesId}
              dataKey={s.seriesId}
              yAxisId={String(s.axis)}
              stroke={SERIES_COLORS[i]}
              strokeWidth={2}
              dot={false}
              connectNulls
              isAnimationActive={false}
            />
          ))}
        </LineChart>
      </ChartContainer>
    </div>
  );
}

function SeriesTable({ result }: { result: StudioResult }) {
  return (
    <div className='overflow-x-auto'>
      <table className='w-full text-sm'>
        <thead>
          <tr className='text-muted-foreground border-b text-left'>
            <th className='py-1 pr-3'>Series</th>
            <th className='pr-3'>Adjustment</th>
            <th className='pr-3'>Native</th>
            <th className='pr-3'>Shown as</th>
            <th className='pr-3'>Latest release</th>
            <th>Source</th>
          </tr>
        </thead>
        <tbody>
          {result.series.map((s, i) => (
            <tr key={s.seriesId} className='border-b last:border-0'>
              <td className='py-1 pr-3'>
                <span
                  className='mr-2 inline-block size-2 rounded-full'
                  style={{ background: SERIES_COLORS[i] }}
                  aria-hidden
                />
                {s.label}
                {!s.usable && (
                  <Badge variant='destructive' className='ml-2' title={s.statusNote}>
                    Overdue
                  </Badge>
                )}
              </td>
              <td className='pr-3'>
                <Badge
                  variant={s.adjustment === 'SA' ? 'secondary' : 'outline'}
                  title={s.adjustmentText}
                >
                  {s.adjustment}
                </Badge>
              </td>
              <td className='pr-3'>{FREQUENCY_LABEL[s.nativeFrequency]}</td>
              <td className='pr-3' title={s.metricNote ?? undefined}>
                {s.displayUnit}
                {s.aggregation
                  ? `, ${s.aggregation === 'end' ? 'period end' : s.aggregation === 'mean' ? 'period average' : 'period sum'}`
                  : ''}
              </td>
              <td className='pr-3 whitespace-nowrap'>{s.lastVintage ?? '—'}</td>
              <td>{s.publisher ?? '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Controls({ catalog, countries }: { catalog: StudioCatalog; countries: StudioCountry[] }) {
  const host = useRef<HTMLDivElement>(null);
  const [mode, setMode] = useState<Mode>('countries');
  const [concept, setConcept] = useState('unemployment_rate');
  const [picked, setPicked] = useState<string[]>(['USA', 'DEU']);
  const [country, setCountry] = useState('USA');
  const [seriesIds, setSeriesIds] = useState<string[]>([]);
  const [frequency, setFrequency] = useState<StudioFrequency | null>(null);
  const [metric, setMetric] = useState<StudioMetric>('actual');
  const [years, setYears] = useState(10);

  const indicator = catalog.indicators.find((i) => i.concept === concept);
  const available = new Set(indicator?.countries ?? []);
  const countrySeries = catalog.series.filter((s) => s.iso3 === country);
  const overlayIds = seriesIds.filter((id) => countrySeries.some((s) => s.seriesId === id));

  const query: StudioQuery | null =
    mode === 'countries'
      ? picked.length
        ? {
            mode,
            concept,
            countries: picked.filter((c) => available.has(c)),
            frequency,
            metric,
            years
          }
        : null
      : overlayIds.length
        ? { mode, country, seriesIds: overlayIds, frequency, metric, years }
        : null;
  const ready = query !== null && (query.mode === 'indicators' || query.countries.length > 0);
  const { data, error, isFetching } = useQuery({
    ...studioQueries.result(
      query ?? { mode: 'countries', concept, countries: [], frequency: null, metric, years }
    ),
    enabled: ready,
    placeholderData: keepPreviousData,
    retry: false
  });

  const toggleSeries = (id: string) =>
    setSeriesIds(
      overlayIds.includes(id)
        ? overlayIds.filter((x) => x !== id)
        : canAdd(overlayIds.length, catalog.maxCountries)
          ? [...overlayIds, id]
          : overlayIds
    );

  return (
    <div className='space-y-4'>
      <Tabs value={mode} onValueChange={(v) => setMode(v as Mode)}>
        <TabsList>
          <TabsTrigger value='countries'>
            Multi-Country Comparison (1 indicator, up to {catalog.maxCountries} countries)
          </TabsTrigger>
          <TabsTrigger value='indicators'>Single-Country Multi-Indicator Overlay</TabsTrigger>
        </TabsList>
      </Tabs>

      <Card>
        <CardHeader>
          <CardTitle className='text-base'>
            {mode === 'countries'
              ? 'Choose an indicator and countries'
              : 'Choose a country and indicators'}
          </CardTitle>
          {mode === 'countries' && indicator && (
            <CardDescription>{indicator.explanation}</CardDescription>
          )}
        </CardHeader>
        <CardContent className='space-y-4'>
          {mode === 'countries' ? (
            <>
              <NativeSelect
                aria-label='Indicator'
                value={concept}
                onChange={(e) => setConcept(e.target.value)}
              >
                {catalog.indicators.map((i) => (
                  <NativeSelectOption key={i.concept} value={i.concept}>
                    {i.name} ({i.countries.length})
                  </NativeSelectOption>
                ))}
              </NativeSelect>
              <CountryPicker
                countries={countries}
                available={available}
                selected={picked.filter((c) => available.has(c))}
                max={catalog.maxCountries}
                onChange={setPicked}
              />
            </>
          ) : (
            <>
              <NativeSelect
                aria-label='Country'
                value={country}
                onChange={(e) => setCountry(e.target.value)}
              >
                {countries
                  .filter((c) => catalog.series.some((s) => s.iso3 === c.iso3))
                  .map((c) => (
                    <NativeSelectOption key={c.iso3} value={c.iso3}>
                      {flagEmoji(c.iso2)} {c.name}
                    </NativeSelectOption>
                  ))}
              </NativeSelect>
              <p className='text-sm font-medium'>
                {selectionCounter(overlayIds.length, catalog.maxCountries, 'indicators')}
              </p>
              <div className='grid max-h-56 gap-1 overflow-y-auto sm:grid-cols-2'>
                {countrySeries.map((s) => {
                  const on = overlayIds.includes(s.seriesId);
                  return (
                    <button
                      key={s.seriesId}
                      type='button'
                      aria-pressed={on}
                      disabled={!on && !canAdd(overlayIds.length, catalog.maxCountries)}
                      onClick={() => toggleSeries(s.seriesId)}
                      className={cn(
                        'hover:bg-muted flex items-center justify-between gap-2 rounded-md border px-2 py-1 text-left text-sm',
                        on && 'border-primary bg-primary/10'
                      )}
                    >
                      <span className='truncate' title={s.units}>
                        {s.name}
                      </span>
                      <span className='text-muted-foreground shrink-0 text-xs'>
                        {FREQUENCY_LABEL[s.nativeFrequency]} · {s.adjustment}
                      </span>
                    </button>
                  );
                })}
              </div>
            </>
          )}

          <div className='flex flex-wrap items-center gap-4'>
            <div className='flex items-center gap-2 text-sm font-medium'>
              <span>Metric</span>
              <NativeSelect
                aria-label='Metric'
                value={metric}
                onChange={(e) => setMetric(e.target.value as StudioMetric)}
              >
                <NativeSelectOptGroup label='Metric'>
                  <NativeSelectOption value='actual'>Actual Value</NativeSelectOption>
                  <NativeSelectOption value='poc'>PoC (Percentage of Change)</NativeSelectOption>
                </NativeSelectOptGroup>
              </NativeSelect>
            </div>
            <div className='flex items-center gap-2 text-sm font-medium'>
              <span>History</span>
              <NativeSelect
                aria-label='History'
                value={String(years)}
                onChange={(e) => setYears(Number(e.target.value))}
              >
                <NativeSelectOption value='10'>10 years</NativeSelectOption>
                <NativeSelectOption value='20'>20 years</NativeSelectOption>
                <NativeSelectOption value='30'>30 years</NativeSelectOption>
                <NativeSelectOption value='40'>Since 1986 (40 years)</NativeSelectOption>
              </NativeSelect>
            </div>
            <FrequencyPills
              allowed={data?.allowedFrequencies}
              value={frequency ?? data?.frequency ?? null}
              onChange={setFrequency}
            />
          </div>
          {data?.restriction && (
            <p className='text-muted-foreground text-sm' role='status'>
              {data.restriction}
            </p>
          )}
        </CardContent>
      </Card>

      {!ready ? (
        <Empty className='border'>
          <EmptyHeader>
            <EmptyTitle>Nothing selected</EmptyTitle>
            <EmptyDescription>Pick at least one item to draw the chart.</EmptyDescription>
          </EmptyHeader>
        </Empty>
      ) : error ? (
        <Alert variant='destructive'>
          <AlertTitle>Could not build the comparison</AlertTitle>
          <AlertDescription>
            {error.message}{' '}
            {frequency && (
              <Button variant='link' size='sm' onClick={() => setFrequency(null)}>
                Use the common frequency
              </Button>
            )}
          </AlertDescription>
        </Alert>
      ) : !data ? (
        <Skeleton className='h-96 w-full rounded-xl' />
      ) : (
        <>
          {data.notices.map((n) => (
            <Alert key={n}>
              <AlertDescription>{n}</AlertDescription>
            </Alert>
          ))}
          <Card className={cn(isFetching && 'opacity-70')}>
            <CardHeader>
              <CardTitle className='flex flex-wrap items-center gap-2 text-base'>
                {data.name}
                <Badge variant='outline'>
                  {FREQUENCY_LABEL[data.frequency]}
                  {data.pocName ? `, ${data.pocName}` : ', actual value'}
                </Badge>
              </CardTitle>
              <div className='flex gap-2'>
                <Button
                  size='sm'
                  variant='outline'
                  onClick={() =>
                    download('qufin-compare.csv', new Blob([toCsv(data)], { type: 'text/csv' }))
                  }
                >
                  Export CSV
                </Button>
                <Button
                  size='sm'
                  variant='outline'
                  onClick={() => exportPng(host.current, 'qufin-compare.png')}
                >
                  Export PNG
                </Button>
              </div>
            </CardHeader>
            <CardContent className='space-y-4'>
              <StudioChart result={data} host={host} />
              <SeriesTable result={data} />
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}

export function StudioView() {
  const catalog = useQuery({ ...studioQueries.catalog(), enabled: macroAvailable });
  const countries = useQuery({ ...studioQueries.countries(), enabled: macroAvailable });

  if (!macroAvailable) {
    return (
      <Empty className='border'>
        <EmptyHeader>
          <EmptyTitle>No API connected</EmptyTitle>
          <EmptyDescription>
            The comparison studio reads the QuFin API. Set NEXT_PUBLIC_API_URL to connect it.
          </EmptyDescription>
        </EmptyHeader>
      </Empty>
    );
  }
  if (catalog.error || countries.error) {
    return (
      <Empty className='border'>
        <EmptyHeader>
          <EmptyTitle>Could not load the studio</EmptyTitle>
          <EmptyDescription>{(catalog.error ?? countries.error)?.message}</EmptyDescription>
        </EmptyHeader>
      </Empty>
    );
  }
  if (!catalog.data || !countries.data) return <Skeleton className='h-96 w-full rounded-xl' />;
  return <Controls catalog={catalog.data} countries={countries.data} />;
}
