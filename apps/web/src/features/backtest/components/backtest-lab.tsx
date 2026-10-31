'use client';

import { useMemo, useState } from 'react';
import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { Area, AreaChart, CartesianGrid, Line, LineChart, XAxis, YAxis } from 'recharts';
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
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { NativeSelect, NativeSelectOptGroup, NativeSelectOption } from '@/components/ui/native-select';
import { Skeleton } from '@/components/ui/skeleton';
import { marketQueries } from '@/features/market/api/queries';
import { listAssets } from '@/features/market/api/service';
import { formatPct } from '@/features/market/lib/format';
import { cn } from '@/lib/utils';
import { runBacktest, type StrategyKind } from '../lib/engine';

const STRATEGIES: { value: StrategyKind; label: string; hint: string }[] = [
  { value: 'all-signals', label: 'Follow signals', hint: 'Long or short whenever the edge clears your threshold' },
  { value: 'high-conviction', label: 'High conviction', hint: 'Trade only when the edge is 10 points or more' },
  { value: 'buy-hold', label: 'Buy & hold', hint: 'Benchmark: always long' }
];

const PERIODS = [
  { value: 252, label: '1 year' },
  { value: 504, label: '2 years' },
  { value: 750, label: '3 years' }
];

const equityConfig = {
  strategy: { label: 'Strategy', color: 'var(--chart-1)' },
  benchmark: { label: 'Buy & hold', color: 'var(--muted-foreground)' }
} satisfies ChartConfig;

const drawdownConfig = {
  drawdown: { label: 'Drawdown', color: 'var(--bear)' }
} satisfies ChartConfig;

function StatCard({ label, value, hint, tone }: { label: string; value: string; hint?: string; tone?: 'up' | 'down' }) {
  return (
    <Card size='sm'>
      <CardHeader>
        <CardDescription>{label}</CardDescription>
        <CardTitle
          className={cn(
            'font-mono text-xl tabular-nums',
            tone === 'up' && 'text-bull',
            tone === 'down' && 'text-bear'
          )}
        >
          {value}
        </CardTitle>
      </CardHeader>
      {hint && <CardContent className='text-muted-foreground text-xs'>{hint}</CardContent>}
    </Card>
  );
}

export function BacktestLab() {
  const assets = listAssets();
  const [symbol, setSymbol] = useState('XAUUSD');
  const [strategy, setStrategy] = useState<StrategyKind>('all-signals');
  const [minEdgePts, setMinEdgePts] = useState(5);
  const [rebalanceDays, setRebalanceDays] = useState(5);
  const [costBps, setCostBps] = useState(3);
  const [lookbackDays, setLookbackDays] = useState(504);

  const { data: detail } = useQuery({ ...marketQueries.asset(symbol), placeholderData: keepPreviousData });

  const result = useMemo(
    () =>
      detail
        ? runBacktest({
            candles: detail.candles,
            signals: detail.signals,
            strategy,
            minEdge: minEdgePts / 100,
            rebalanceDays,
            costBps,
            lookbackDays
          })
        : null,
    [detail, strategy, minEdgePts, rebalanceDays, costBps, lookbackDays]
  );

  const groups = Array.from(new Set(assets.map((a) => a.assetClass)));
  const s = result?.stats;

  return (
    <div className='grid grid-cols-1 gap-4 xl:grid-cols-4'>
      <Card className='xl:col-span-1 xl:self-start'>
        <CardHeader>
          <CardTitle>Setup</CardTitle>
          <CardDescription>Signals act on the next day&apos;s return. Costs are charged on every position change.</CardDescription>
        </CardHeader>
        <CardContent className='flex flex-col gap-4'>
          <div className='flex flex-col gap-1.5'>
            <Label htmlFor='bt-asset'>Asset</Label>
            <NativeSelect id='bt-asset' className='w-full' value={symbol} onChange={(e) => setSymbol(e.target.value)}>
              {groups.map((g) => (
                <NativeSelectOptGroup key={g} label={g}>
                  {assets
                    .filter((a) => a.assetClass === g)
                    .map((a) => (
                      <NativeSelectOption key={a.symbol} value={a.symbol}>
                        {a.symbol} · {a.name}
                      </NativeSelectOption>
                    ))}
                </NativeSelectOptGroup>
              ))}
            </NativeSelect>
          </div>
          <fieldset className='flex flex-col gap-1.5'>
            <legend className='mb-1.5 text-sm font-medium'>Strategy</legend>
            {STRATEGIES.map((st) => (
              <button
                key={st.value}
                type='button'
                onClick={() => setStrategy(st.value)}
                aria-pressed={strategy === st.value}
                className={cn(
                  'rounded-lg border px-3 py-2 text-left transition-colors',
                  strategy === st.value ? 'border-primary bg-accent' : 'hover:bg-muted'
                )}
              >
                <div className='text-sm font-medium'>{st.label}</div>
                <div className='text-muted-foreground text-xs'>{st.hint}</div>
              </button>
            ))}
          </fieldset>
          <div className='grid grid-cols-2 gap-3'>
            <div className='flex flex-col gap-1.5'>
              <Label htmlFor='bt-edge'>Min edge (pts)</Label>
              <Input
                id='bt-edge'
                type='number'
                min={0}
                max={20}
                disabled={strategy === 'buy-hold'}
                value={minEdgePts}
                onChange={(e) => setMinEdgePts(Number(e.target.value))}
              />
            </div>
            <div className='flex flex-col gap-1.5'>
              <Label htmlFor='bt-rebalance'>Rebalance (days)</Label>
              <Input id='bt-rebalance' type='number' min={1} max={20} value={rebalanceDays} onChange={(e) => setRebalanceDays(Math.max(1, Math.round(Number(e.target.value))))} />
            </div>
            <div className='flex flex-col gap-1.5'>
              <Label htmlFor='bt-cost'>Cost (bps/side)</Label>
              <Input id='bt-cost' type='number' min={0} step={0.5} value={costBps} onChange={(e) => setCostBps(Number(e.target.value))} />
            </div>
            <div className='flex flex-col gap-1.5'>
              <Label htmlFor='bt-period'>Period</Label>
              <NativeSelect id='bt-period' className='w-full' value={String(lookbackDays)} onChange={(e) => setLookbackDays(Number(e.target.value))}>
                {PERIODS.map((p) => (
                  <NativeSelectOption key={p.value} value={p.value}>
                    {p.label}
                  </NativeSelectOption>
                ))}
              </NativeSelect>
            </div>
          </div>
          <p className='text-muted-foreground text-xs'>
            Edge = how far the model&apos;s probability is from 50%. 5 pts means 55% or more one way.
          </p>
          <Button
            variant='outline'
            onClick={() => {
              setStrategy('all-signals');
              setMinEdgePts(5);
              setRebalanceDays(5);
              setCostBps(3);
              setLookbackDays(504);
            }}
          >
            Reset
          </Button>
        </CardContent>
      </Card>

      <div className='flex flex-col gap-4 xl:col-span-3'>
        {!result || !s ? (
          <Skeleton className='h-[560px] w-full rounded-xl' />
        ) : (
          <>
            <div className='grid grid-cols-2 gap-4 lg:grid-cols-4'>
              <StatCard
                label='Total return'
                value={formatPct(s.totalReturn)}
                hint={`Buy & hold ${formatPct(s.benchmarkReturn)}`}
                tone={s.totalReturn >= 0 ? 'up' : 'down'}
              />
              <StatCard label='Sharpe ratio' value={s.sharpe.toFixed(2)} hint={`Volatility ${formatPct(s.annualVol, 1, false)} a year`} />
              <StatCard label='Max drawdown' value={formatPct(s.maxDrawdown)} tone='down' hint={`CAGR ${formatPct(s.cagr)}`} />
              <StatCard
                label='Hit rate'
                value={formatPct(s.hitRate, 1, false)}
                hint={`${s.trades} trades · ${formatPct(s.exposure, 0, false)} time in market`}
              />
            </div>

            <Card>
              <CardHeader>
                <CardTitle>Equity curve</CardTitle>
                <CardDescription>Growth of 1 unit of capital, after costs</CardDescription>
              </CardHeader>
              <CardContent>
                <ChartContainer config={equityConfig} className='aspect-auto h-72 w-full'>
                  <LineChart data={result.equity} margin={{ left: 0, right: 8, top: 8 }}>
                    <CartesianGrid vertical={false} strokeDasharray='3 3' />
                    <XAxis dataKey='time' tickLine={false} axisLine={false} minTickGap={56} tickFormatter={(v: string) => v.slice(0, 7)} />
                    <YAxis tickLine={false} axisLine={false} width={40} domain={['auto', 'auto']} tickFormatter={(v: number) => v.toFixed(2)} />
                    <ChartTooltip content={<ChartTooltipContent indicator='line' />} />
                    <ChartLegend content={<ChartLegendContent />} />
                    <Line dataKey='benchmark' stroke='var(--color-benchmark)' strokeDasharray='4 4' dot={false} strokeWidth={1.25} />
                    <Line dataKey='strategy' stroke='var(--color-strategy)' dot={false} strokeWidth={2} />
                  </LineChart>
                </ChartContainer>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Drawdown</CardTitle>
                <CardDescription>Distance below the previous equity high</CardDescription>
              </CardHeader>
              <CardContent>
                <ChartContainer config={drawdownConfig} className='aspect-auto h-40 w-full'>
                  <AreaChart data={result.equity} margin={{ left: 0, right: 8, top: 8 }}>
                    <CartesianGrid vertical={false} strokeDasharray='3 3' />
                    <XAxis dataKey='time' tickLine={false} axisLine={false} minTickGap={56} tickFormatter={(v: string) => v.slice(0, 7)} />
                    <YAxis tickLine={false} axisLine={false} width={40} tickFormatter={(v: number) => `${Math.round(v * 100)}%`} />
                    <ChartTooltip content={<ChartTooltipContent indicator='line' />} />
                    <Area dataKey='drawdown' type='monotone' stroke='var(--color-drawdown)' fill='var(--color-drawdown)' fillOpacity={0.2} strokeWidth={1.25} />
                  </AreaChart>
                </ChartContainer>
              </CardContent>
            </Card>
            <p className='text-muted-foreground text-xs'>
              Preview engine running on sample data. Production backtests run on the server with
              point-in-time data and purged walk-forward validation. Past performance does not
              guarantee future results.
            </p>
          </>
        )}
      </div>
    </div>
  );
}
