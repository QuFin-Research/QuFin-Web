'use client';

import Link from 'next/link';
import { useSuspenseQuery } from '@tanstack/react-query';
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
import { useHydrated } from '@/features/journal/hooks/use-hydrated';
import { useJournalStore } from '@/features/journal/utils/store';
import { cn } from '@/lib/utils';

export function OverviewKpis() {
  const { data: snapshots } = useSuspenseQuery(marketQueries.snapshots());
  const decisions = useJournalStore((s) => s.decisions);
  const hydrated = useHydrated();
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
      value: hydrated ? String(decisions.length) : '–',
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
      {value}
    </span>
  );
}

export function CountryScorecard() {
  const { data: rows } = useSuspenseQuery(marketQueries.countryScores());
  return (
    <Card>
      <CardHeader>
        <CardTitle>Macro scorecard</CardTitle>
        <CardDescription>
          Each pillar scored −3 to +3 from official releases versus trend and consensus.
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
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
