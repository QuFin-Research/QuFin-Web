'use client';

import Link from 'next/link';
import { useQuery, useSuspenseQuery } from '@tanstack/react-query';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from '@/components/ui/table';
import { marketQueries } from '@/features/market/api/queries';
import type { CountryScore, ScoreDimension } from '@/features/market/api/types';
import {
  ChangeText,
  ConvictionMeter,
  DirectionBadge,
  ProbabilityLabel
} from '@/features/market/components/signal-badge';
import { formatPrice } from '@/features/market/lib/format';
import { journalQueries } from '@/features/journal/api/queries';
import { cn } from '@/lib/utils';

export function OverviewKpis() {
  const { data: snapshots } = useSuspenseQuery(marketQueries.snapshots());
  // Client-only: the journal needs the user's session (or this browser's storage).
  const { data: decisions } = useQuery(journalQueries.list());
  const highConviction = snapshots.filter((s) => s.signal.conviction === 'high');
  const avgHitRate = snapshots.reduce((s, a) => s + a.hitRate, 0) / snapshots.length;
  const bullish = highConviction.filter((s) => s.signal.direction === 'long').length;

  const kpis = [
    {
      label: 'High-conviction signals',
      value: String(highConviction.length),
      hint: `${bullish} bullish · ${highConviction.length - bullish} bearish`
    },
    {
      label: 'Model hit rate (5-day)',
      value: `${(avgHitRate * 100).toFixed(1)}%`,
      hint: 'Walk-forward, all assets, all signals'
    },
    {
      label: 'Assets covered',
      value: String(snapshots.length),
      hint: 'FX · Metals · Energy · Crypto'
    },
    {
      label: 'Decisions logged',
      value: decisions ? String(decisions.length) : '–',
      hint: 'In your decision journal'
    }
  ];

  return (
    <div className='grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4'>
      {kpis.map((kpi) => (
        <Card key={kpi.label} size='sm'>
          <CardHeader>
            <CardDescription>{kpi.label}</CardDescription>
            <CardTitle className='font-mono text-2xl tabular-nums'>{kpi.value}</CardTitle>
          </CardHeader>
          <CardContent className='text-muted-foreground text-xs'>{kpi.hint}</CardContent>
        </Card>
      ))}
    </div>
  );
}

export function SignalsTable() {
  const { data: snapshots } = useSuspenseQuery(marketQueries.snapshots());
  const sorted = snapshots.toSorted(
    (a, b) => Math.abs(b.signal.probUp - 0.5) - Math.abs(a.signal.probUp - 0.5)
  );

  return (
    <Card>
      <CardHeader>
        <CardTitle>Today&apos;s signals</CardTitle>
        <CardDescription>
          5-day directional outlook, sorted by conviction. Select an asset to decide and backtest.
        </CardDescription>
      </CardHeader>
      <CardContent className='px-0'>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className='pl-4'>Asset</TableHead>
              <TableHead className='text-right'>Price</TableHead>
              <TableHead className='text-right'>1D</TableHead>
              <TableHead>Signal</TableHead>
              <TableHead className='text-right'>Prob.</TableHead>
              <TableHead>Conviction</TableHead>
              <TableHead className='hidden lg:table-cell'>Regime</TableHead>
              <TableHead className='hidden pr-4 text-right lg:table-cell'>Hit rate</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sorted.map((s) => (
              <TableRow key={s.asset.symbol} className='relative'>
                <TableCell className='pl-4'>
                  <Link
                    href={`/dashboard/markets/${s.asset.symbol}`}
                    className='font-medium after:absolute after:inset-0 hover:underline'
                  >
                    {s.asset.symbol}
                  </Link>
                  <div className='text-muted-foreground text-xs'>{s.asset.assetClass}</div>
                </TableCell>
                <TableCell className='text-right font-mono tabular-nums'>
                  {formatPrice(s.lastPrice, s.asset.precision)}
                </TableCell>
                <TableCell className='text-right'>
                  <ChangeText value={s.changePct} />
                </TableCell>
                <TableCell>
                  <DirectionBadge signal={s.signal} />
                </TableCell>
                <TableCell className='text-right'>
                  <ProbabilityLabel probUp={s.signal.probUp} />
                </TableCell>
                <TableCell>
                  <ConvictionMeter conviction={s.signal.conviction} />
                </TableCell>
                <TableCell className='text-muted-foreground hidden lg:table-cell'>
                  {s.regime}
                </TableCell>
                <TableCell className='hidden pr-4 text-right font-mono tabular-nums lg:table-cell'>
                  {(s.hitRate * 100).toFixed(1)}%
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}

const DIMENSIONS: { key: ScoreDimension; label: string }[] = [
  { key: 'growth', label: 'Growth' },
  { key: 'inflation', label: 'Inflation' },
  { key: 'labour', label: 'Labour' },
  { key: 'policy', label: 'Policy' },
  { key: 'sentiment', label: 'Sentiment' }
];

function ScoreCell({ value }: { value: number }) {
  const strength = Math.min(Math.abs(value) / 3, 1);
  return (
    <span
      className={cn(
        'inline-flex h-7 w-10 items-center justify-center rounded-md font-mono text-xs tabular-nums',
        value > 0 && 'text-bull',
        value < 0 && 'text-bear',
        value === 0 && 'text-muted-foreground'
      )}
      style={{
        backgroundColor:
          value === 0
            ? 'var(--muted)'
            : `color-mix(in oklch, var(${value > 0 ? '--bull' : '--bear'}) ${8 + strength * 22}%, transparent)`
      }}
    >
      {value > 0 ? '+' : ''}
      {Number.isInteger(value) ? value : value.toFixed(1)}
    </span>
  );
}

const pct = (v: number) => `${Math.round(v * 100)}%`;

/** Confidence: how much fresh evidence stands behind a score. It never changes the score. */
function ConfidenceText({ value }: { value: number | null | undefined }) {
  if (value === null || value === undefined) return null;
  return (
    <div
      className={cn(
        'mt-0.5 font-mono text-[10px] tabular-nums',
        value < 0.6 ? 'text-bear' : 'text-muted-foreground'
      )}
    >
      {pct(value)}
    </div>
  );
}

function PendingList({ row }: { row: CountryScore }) {
  const pending = row.pending ?? [];
  if (pending.length === 0) return null;
  return (
    <div className='border-t px-4 pt-3 text-xs'>
      <div className='mb-1 font-medium'>Pending releases that may move the {row.code} scores</div>
      <ul className='text-muted-foreground flex flex-col gap-0.5'>
        {pending.map((p) => (
          <li key={p.seriesId}>
            <span className='text-foreground font-mono'>{p.seriesId}</span>
            {p.period ? ` ${p.period.endsWith('-01') ? p.period.slice(0, 7) : p.period}` : ''} (
            {p.sourceName ?? 'unknown source'}): {p.reason}
            {p.sourceRelease && p.fredRelease && p.sourceRelease !== p.fredRelease
              ? `, source ${p.sourceRelease}, FRED ~${p.fredRelease}`
              : p.fredRelease
                ? `, ${p.fredRelease}`
                : ''}
          </li>
        ))}
      </ul>
    </div>
  );
}

export function CountryScorecard() {
  const { data: rows } = useSuspenseQuery(marketQueries.countryScores());
  const live = rows.some((r) => r.data === 'live');
  return (
    <Card>
      <CardHeader>
        <CardTitle className='flex items-center gap-2'>
          Macro scorecard
          <Badge variant={live ? 'outline' : 'secondary'}>
            {live ? `Live · as of ${rows[0].asOf}` : 'Sample data'}
          </Badge>
        </CardTitle>
        <CardDescription>
          {live
            ? 'Each pillar −3 to +3: indicators scored against their own 10-year history as published at the time, averaged over the fresh, usable ones. The percentage is confidence, the share of evidence that is fresh; late data lowers it, never the score. Size positions by confidence. Other economies appear once their data sources are connected.'
            : 'Illustrative scores. Connect the QuFin API and load macro data for live scorecards.'}
        </CardDescription>
      </CardHeader>
      <CardContent className='px-0'>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className='pl-4'>Economy</TableHead>
              {DIMENSIONS.map((d) => (
                <TableHead key={d.key} className='hidden text-center sm:table-cell'>
                  {d.label}
                </TableHead>
              ))}
              <TableHead className='pr-4 text-right'>Overall</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((row: CountryScore) => (
              <TableRow key={row.code}>
                <TableCell className='pl-4'>
                  <div className='font-medium'>{row.country}</div>
                  <div className='text-muted-foreground text-xs'>{row.currency}</div>
                </TableCell>
                {DIMENSIONS.map((d) => (
                  <TableCell key={d.key} className='hidden text-center sm:table-cell'>
                    <ScoreCell value={row.scores[d.key]} />
                    <ConfidenceText value={row.confidence?.[d.key]} />
                  </TableCell>
                ))}
                <TableCell
                  className={cn(
                    'pr-4 text-right font-mono tabular-nums',
                    row.overall > 0 ? 'text-bull' : row.overall < 0 ? 'text-bear' : ''
                  )}
                >
                  {row.overall > 0 ? '+' : ''}
                  {row.overall.toFixed(1)}
                  <ConfidenceText value={row.overallConfidence} />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        {rows
          .filter((r) => r.data === 'live')
          .map((r) => (
            <PendingList key={r.code} row={r} />
          ))}
      </CardContent>
    </Card>
  );
}
