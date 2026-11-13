'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from '@/components/ui/empty';
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
import { cn } from '@/lib/utils';
import { macroQueries } from '../api/queries';
import { macroAvailable } from '../api/service';
import type { ComparableConcept, Comparison, ComparisonRow } from '../api/types';
import { compareScale, moveTone, rankLabel, sparkPath, writeValue } from '../lib/compare';

const TABS: { value: ComparableConcept; label: string; hint: string }[] = [
  {
    value: 'consumer_prices',
    label: 'Consumer prices',
    hint: 'Inflation: how much more a basket costs than a year ago.'
  },
  {
    value: 'unemployment_rate',
    label: 'Unemployment',
    hint: 'The share of the labour force without a job, so country size drops out.'
  }
];

function Sparkline({ row }: { row: ComparisonRow }) {
  const d = sparkPath(
    row.history.map((p) => p.value),
    96,
    24
  );
  if (!d) return <span className='text-muted-foreground'>—</span>;
  return (
    <svg
      width={96}
      height={24}
      viewBox='0 0 96 24'
      role='img'
      aria-label={`${row.country} over the last ${row.history.length} months`}
      className='text-muted-foreground'
    >
      <path d={d} fill='none' stroke='currentColor' strokeWidth={1.5} />
    </svg>
  );
}

function Move({ value, higherIs }: { value: number | null; higherIs: Comparison['higherIs'] }) {
  if (value === null) return <span className='text-muted-foreground'>—</span>;
  return (
    <span className={cn('tabular-nums', moveTone(value, higherIs))}>
      {value > 0 ? '+' : ''}
      {value.toFixed(1)}
    </span>
  );
}

function CompareTable({ data }: { data: Comparison }) {
  const scale = compareScale(data.rows.filter((r) => r.usable).map((r) => r.value));
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className='w-10'>#</TableHead>
          <TableHead>Country</TableHead>
          <TableHead className='min-w-48'>{data.basis}</TableHead>
          <TableHead className='text-right'>3 months, pt</TableHead>
          <TableHead className='text-right'>12 months, pt</TableHead>
          <TableHead>36 months</TableHead>
          <TableHead>Latest</TableHead>
          <TableHead>Source</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {data.rows.map((r, i) => (
          <TableRow key={r.seriesId} className={cn(!r.usable && 'opacity-60')}>
            <TableCell className='text-muted-foreground tabular-nums'>
              {rankLabel(i, r.usable)}
            </TableCell>
            <TableCell>
              <div className='font-medium'>{r.country}</div>
              <div className='text-muted-foreground font-mono text-xs'>{r.iso3}</div>
            </TableCell>
            <TableCell>
              <div className='flex items-center gap-2'>
                <div className='bg-muted h-2 flex-1 rounded-full'>
                  {r.usable && (
                    <div
                      className='bg-primary h-2 rounded-full'
                      style={{ width: `${scale(r.value) * 100}%` }}
                    />
                  )}
                </div>
                <span className='w-16 text-right font-medium tabular-nums'>
                  {writeValue(r.value, data.unit)}
                </span>
              </div>
            </TableCell>
            <TableCell className='text-right'>
              <Move value={r.change3M} higherIs={data.higherIs} />
            </TableCell>
            <TableCell className='text-right'>
              <Move value={r.change12M} higherIs={data.higherIs} />
            </TableCell>
            <TableCell>
              <Sparkline row={r} />
            </TableCell>
            <TableCell className='whitespace-nowrap'>
              {r.period.slice(0, 7)}
              {!r.usable && (
                <Badge variant='destructive' className='ml-2' title={r.statusNote}>
                  Overdue
                </Badge>
              )}
            </TableCell>
            <TableCell>
              <div title={`${r.canonicalCode ?? r.seriesId}\nStored as: ${r.storedAs}`}>
                {r.publisher ?? r.sourceName ?? '—'}
              </div>
              {r.converted && (
                <Badge
                  variant='outline'
                  className='mt-1'
                  title={`Stored as ${r.storedAs}; QuFin computes the change on the same month a year earlier.`}
                >
                  converted from index
                </Badge>
              )}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

function Basis({ data }: { data: Comparison }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className='flex flex-wrap items-center gap-2'>
          {data.name}
          <Badge variant='outline'>
            {data.basis}, {data.unit}
          </Badge>
        </CardTitle>
        <CardDescription>{data.explanation}</CardDescription>
      </CardHeader>
      <CardContent className='text-muted-foreground space-y-1 text-sm'>
        <p>
          <span className='text-foreground font-medium'>How the numbers are made comparable: </span>
          {data.concept === 'consumer_prices'
            ? 'each office publishes its price index differently, so every country is read as the change on the same month a year earlier; the US index level is converted, the others are published that way.'
            : 'each country’s rate is the unemployed as a share of its own labour force (International Labour Organization definition, seasonally adjusted), so a large country and a small one can be ranked together.'}
        </p>
        <p>
          Method here: {data.method}. Moves are in percentage points, not percent. Rate of change
          and unemployment rates are shown as the source defines them; national definitions can
          still differ at the margin.
        </p>
      </CardContent>
    </Card>
  );
}

export function CompareView() {
  const [concept, setConcept] = useState<ComparableConcept>('consumer_prices');
  const { data, error, isPending } = useQuery({
    ...macroQueries.compare(concept),
    enabled: macroAvailable
  });

  if (!macroAvailable) {
    return (
      <Empty className='border'>
        <EmptyHeader>
          <EmptyTitle>No API connected</EmptyTitle>
          <EmptyDescription>
            Country comparisons come from the QuFin API. Set NEXT_PUBLIC_API_URL to connect it.
          </EmptyDescription>
        </EmptyHeader>
      </Empty>
    );
  }

  return (
    <div className='space-y-4'>
      <Tabs value={concept} onValueChange={(v) => setConcept(v as ComparableConcept)}>
        <TabsList>
          {TABS.map((t) => (
            <TabsTrigger key={t.value} value={t.value} title={t.hint}>
              {t.label}
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>

      {error ? (
        <Empty className='border'>
          <EmptyHeader>
            <EmptyTitle>Could not load the comparison</EmptyTitle>
            <EmptyDescription>{error.message}</EmptyDescription>
          </EmptyHeader>
        </Empty>
      ) : isPending || !data ? (
        <Skeleton className='h-96 w-full rounded-xl' />
      ) : (
        <>
          <Basis data={data} />
          <Card>
            <CardContent className='pt-6'>
              <CompareTable data={data} />
            </CardContent>
          </Card>
          {data.missing.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className='text-base'>
                  Not compared yet ({data.missing.length})
                </CardTitle>
                <CardDescription>
                  No live monthly series for these countries on this basis yet. They are left out
                  rather than filled with an annual or estimated figure.
                </CardDescription>
              </CardHeader>
              <CardContent className='flex flex-wrap gap-2'>
                {data.missing.map((m) => (
                  <Badge key={m.iso3} variant='outline' title={m.iso3}>
                    {m.name}
                  </Badge>
                ))}
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
