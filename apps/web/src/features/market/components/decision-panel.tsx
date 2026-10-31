'use client';

import { useMemo, useState } from 'react';
import Link from 'next/link';
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Area, AreaChart, CartesianGrid, ReferenceLine, XAxis, YAxis } from 'recharts';
import { toast } from 'sonner';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { ChartContainer, ChartTooltip, ChartTooltipContent, type ChartConfig } from '@/components/ui/chart';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { NativeSelect, NativeSelectOption } from '@/components/ui/native-select';
import { Skeleton } from '@/components/ui/skeleton';
import { Textarea } from '@/components/ui/textarea';
import { Icons } from '@/components/icons';
import { backtestQueries } from '@/features/backtest/api/queries';
import type { DecisionRuleBacktestParams } from '@/features/backtest/api/types';
import { journalMutations, journalQueries } from '@/features/journal/api/queries';
import { useDebounce } from '@/hooks/use-debounce';
import { cn } from '@/lib/utils';
import type { AssetClass, AssetDetail, Direction } from '../api/types';
import { formatPct, formatPrice } from '../lib/format';

const DEFAULT_COST_BPS: Record<AssetClass, number> = {
  FX: 1.5,
  Metals: 3,
  Energy: 4,
  Crypto: 10
};

const EDGE_OPTIONS = [
  { value: '0', label: 'Any signal that agrees' },
  { value: '0.05', label: 'Medium conviction or higher' },
  { value: '0.1', label: 'High conviction only' }
];

/** Average true range over the last `period` days, as a fraction of price */
function atrPct(detail: AssetDetail, period = 14) {
  const c = detail.candles.slice(-(period + 1));
  let sum = 0;
  for (let i = 1; i < c.length; i++) {
    sum += Math.max(c[i].high - c[i].low, Math.abs(c[i].high - c[i - 1].close), Math.abs(c[i].low - c[i - 1].close));
  }
  return sum / period / c[c.length - 1].close;
}

const curveConfig = {
  cumR: { label: 'Cumulative R', color: 'var(--chart-1)' }
} satisfies ChartConfig;

function Stat({ label, value, tone }: { label: string; value: string; tone?: 'up' | 'down' }) {
  return (
    <div className='bg-muted/50 rounded-lg px-3 py-2'>
      <div className='text-muted-foreground text-xs'>{label}</div>
      <div
        className={cn(
          'font-mono text-base tabular-nums',
          tone === 'up' && 'text-bull',
          tone === 'down' && 'text-bear'
        )}
      >
        {value}
      </div>
    </div>
  );
}

export function DecisionPanel({ detail }: { detail: AssetDetail }) {
  const { asset, lastPrice, signal } = detail;
  const p = asset.precision;
  const atr = useMemo(() => atrPct(detail), [detail]);
  const round = (v: number) => Number(v.toFixed(p));

  const [direction, setDirection] = useState<Direction>(signal.direction);
  const [entry, setEntry] = useState(round(lastPrice));
  const [stopDist, setStopDist] = useState(1.5 * atr);
  const [rewardRisk, setRewardRisk] = useState(2);
  const [maxHoldDays, setMaxHoldDays] = useState(10);
  const [minEdge, setMinEdge] = useState(signal.conviction === 'high' ? '0.1' : '0.05');
  const [costBps, setCostBps] = useState(DEFAULT_COST_BPS[asset.assetClass]);
  const [account, setAccount] = useState(10000);
  const [riskPct, setRiskPct] = useState(1);
  const [note, setNote] = useState('');
  const queryClient = useQueryClient();
  const create = useMutation({
    ...journalMutations.create(),
    onSuccess: (decision) => {
      toast.success(`${decision.direction === 'long' ? 'Long' : 'Short'} ${decision.symbol} logged`, {
        description: 'Track it in your decision journal.'
      });
      setNote('');
    },
    onError: (e) => toast.error(`Could not log the decision: ${e.message}`),
    onSettled: () => queryClient.invalidateQueries({ queryKey: journalQueries.all() })
  });

  const sign = direction === 'long' ? 1 : -1;
  const stop = entry * (1 - sign * stopDist);
  const target = entry * (1 + sign * stopDist * rewardRisk);
  const units = (account * (riskPct / 100)) / Math.abs(entry - stop || 1);
  const againstSignal = signal.conviction !== 'low' && direction !== signal.direction;

  const rule = useDebounce<DecisionRuleBacktestParams>(
    {
      symbol: asset.symbol,
      direction,
      stopPct: stopDist,
      targetPct: stopDist * rewardRisk,
      maxHoldDays,
      minEdge: Number(minEdge),
      costBps
    },
    250
  );
  // Same limits the API validates, so a half-typed value never reaches it.
  const ruleValid =
    rule.stopPct > 0 &&
    rule.stopPct <= 0.5 &&
    rule.targetPct > 0 &&
    rule.targetPct <= 2 &&
    Number.isInteger(rule.maxHoldDays) &&
    rule.maxHoldDays >= 1 &&
    rule.maxHoldDays <= 250 &&
    rule.costBps >= 0 &&
    rule.costBps <= 500;
  const { data: result, error: backtestError } = useQuery({
    ...backtestQueries.decisionRule(rule),
    enabled: ruleValid,
    placeholderData: keepPreviousData
  });

  const valid =
    entry > 0 && stopDist > 0 && rewardRisk > 0 && maxHoldDays >= 1 && riskPct > 0 && riskPct <= 10;

  function logDecision() {
    create.mutate({
      symbol: asset.symbol,
      direction,
      entry,
      stop: round(stop),
      target: round(target),
      riskPct,
      maxHoldDays,
      signalProbUp: signal.probUp,
      backtest:
        ruleValid && result?.trades.length
          ? { trades: result.trades.length, winRate: result.winRate, avgR: result.avgR }
          : null,
      note
    });
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Your decision</CardTitle>
        <CardDescription>
          Set your plan, see how it would have performed, then log it to your journal.
        </CardDescription>
      </CardHeader>
      <CardContent className='flex flex-col gap-5'>
        <div className='grid grid-cols-2 gap-2'>
          {(['long', 'short'] as const).map((d) => (
            <Button
              key={d}
              variant={direction === d ? 'default' : 'outline'}
              className={cn(
                direction === d && d === 'long' && 'bg-bull hover:bg-bull/85 text-white',
                direction === d && d === 'short' && 'bg-bear hover:bg-bear/85 text-white'
              )}
              onClick={() => setDirection(d)}
            >
              {d === 'long' ? <Icons.trendingUp /> : <Icons.trendingDown />}
              {d === 'long' ? 'Long' : 'Short'}
            </Button>
          ))}
        </div>

        {againstSignal && (
          <Alert>
            <Icons.warning />
            <AlertDescription>
              This trade goes against today&apos;s {signal.conviction}-conviction QuFin signal. The
              backtest below only uses past days when the signal agreed with your direction.
            </AlertDescription>
          </Alert>
        )}

        <div className='grid grid-cols-2 gap-3'>
          <div className='flex flex-col gap-1.5'>
            <Label htmlFor='entry'>Entry</Label>
            <Input id='entry' type='number' step={1 / 10 ** p} value={entry} onChange={(e) => setEntry(Number(e.target.value))} />
          </div>
          <div className='flex flex-col gap-1.5'>
            <Label htmlFor='stop-dist'>Stop distance (%)</Label>
            <Input
              id='stop-dist'
              type='number'
              step={0.1}
              min={0.1}
              value={Number((stopDist * 100).toFixed(2))}
              onChange={(e) => setStopDist(Number(e.target.value) / 100)}
            />
          </div>
          <div className='flex flex-col gap-1.5'>
            <Label htmlFor='rr'>Reward : risk</Label>
            <Input id='rr' type='number' step={0.25} min={0.25} value={rewardRisk} onChange={(e) => setRewardRisk(Number(e.target.value))} />
          </div>
          <div className='flex flex-col gap-1.5'>
            <Label htmlFor='hold'>Max holding (days)</Label>
            <Input id='hold' type='number' min={1} max={60} value={maxHoldDays} onChange={(e) => setMaxHoldDays(Math.round(Number(e.target.value)))} />
          </div>
        </div>

        <div className='grid grid-cols-3 gap-2 text-sm'>
          <Stat label='Stop' value={formatPrice(stop, p)} tone='down' />
          <Stat label='Target' value={formatPrice(target, p)} tone='up' />
          <Stat label='Stop vs ATR' value={`${(stopDist / atr).toFixed(1)}×`} />
        </div>

        <div className='grid grid-cols-2 gap-3'>
          <div className='flex flex-col gap-1.5'>
            <Label htmlFor='account'>Account size (USD)</Label>
            <Input id='account' type='number' min={0} step={1000} value={account} onChange={(e) => setAccount(Number(e.target.value))} />
          </div>
          <div className='flex flex-col gap-1.5'>
            <Label htmlFor='risk'>Risk per trade (%)</Label>
            <Input id='risk' type='number' min={0.1} max={5} step={0.25} value={riskPct} onChange={(e) => setRiskPct(Number(e.target.value))} />
          </div>
        </div>
        <p className='text-muted-foreground -mt-2 text-xs'>
          Position size ≈ <span className='text-foreground font-mono'>{units.toLocaleString('en-US', { maximumFractionDigits: units < 10 ? 3 : 0 })}</span>{' '}
          units, risking {formatPct(riskPct / 100, 2, false)} of the account if the stop is hit.
        </p>

        <div className='flex flex-col gap-3 border-t pt-4'>
          <div className='flex flex-wrap items-end justify-between gap-3'>
            <div>
              <h3 className='text-sm font-medium'>Backtest this decision</h3>
              <p className='text-muted-foreground text-xs'>
                Your plan replayed on {detail.candles.length} days of history, entering the day after
                each matching signal.
              </p>
            </div>
            <div className='flex gap-2'>
              <NativeSelect size='sm' value={minEdge} onChange={(e) => setMinEdge(e.target.value)} aria-label='Signal filter'>
                {EDGE_OPTIONS.map((o) => (
                  <NativeSelectOption key={o.value} value={o.value}>
                    {o.label}
                  </NativeSelectOption>
                ))}
              </NativeSelect>
              <Input
                aria-label='Cost per side (bps)'
                title='Cost per side (bps)'
                className='h-7 w-20'
                type='number'
                min={0}
                step={0.5}
                value={costBps}
                onChange={(e) => setCostBps(Number(e.target.value))}
              />
            </div>
          </div>

          {!ruleValid ? (
            <p className='text-muted-foreground text-sm'>
              Adjust the plan to backtest it: stop up to 50%, target up to 200%, hold 1–250 days.
            </p>
          ) : backtestError ? (
            <p className='text-muted-foreground text-sm'>
              Could not run the backtest: {backtestError.message}
            </p>
          ) : !result ? (
            <Skeleton className='h-56 w-full rounded-lg' />
          ) : result.trades.length === 0 ? (
            <p className='text-muted-foreground text-sm'>No past setups matched this plan.</p>
          ) : (
            <>
              <div className='grid grid-cols-2 gap-2 sm:grid-cols-4'>
                <Stat label='Trades' value={String(result.trades.length)} />
                <Stat label='Win rate' value={formatPct(result.winRate, 1, false)} />
                <Stat label='Avg R / trade' value={result.avgR.toFixed(2)} tone={result.avgR > 0 ? 'up' : 'down'} />
                <Stat
                  label='Profit factor'
                  value={Number.isFinite(result.profitFactor) ? result.profitFactor.toFixed(2) : '∞'}
                  tone={result.profitFactor >= 1 ? 'up' : 'down'}
                />
              </div>
              <ChartContainer config={curveConfig} className='aspect-auto h-40 w-full'>
                <AreaChart data={result.curve} margin={{ left: 0, right: 8, top: 8 }}>
                  <CartesianGrid vertical={false} strokeDasharray='3 3' />
                  <XAxis dataKey='time' tickLine={false} axisLine={false} minTickGap={48} tickFormatter={(v: string) => v.slice(0, 7)} />
                  <YAxis tickLine={false} axisLine={false} width={36} />
                  <ReferenceLine y={0} stroke='var(--border)' />
                  <ChartTooltip content={<ChartTooltipContent indicator='line' />} />
                  <Area dataKey='cumR' type='stepAfter' stroke='var(--color-cumR)' fill='var(--color-cumR)' fillOpacity={0.15} strokeWidth={1.5} />
                </AreaChart>
              </ChartContainer>
              <p className='text-muted-foreground text-xs'>
                Expectancy {formatPct(result.expectancyPct, 2)} per trade after costs. Same-bar stop
                and target hits count as losses. Past results do not guarantee future returns.
              </p>
            </>
          )}
        </div>

        <div className='flex flex-col gap-1.5'>
          <Label htmlFor='note'>Note (optional)</Label>
          <Textarea id='note' rows={2} placeholder='Why are you taking this trade?' value={note} onChange={(e) => setNote(e.target.value)} />
        </div>
        <div className='flex flex-wrap items-center gap-3'>
          <Button size='lg' disabled={!valid || create.isPending} onClick={logDecision}>
            <Icons.add />
            Log decision
          </Button>
          <Button size='lg' variant='ghost' nativeButton={false} render={<Link href='/dashboard/journal' aria-label='Open journal' />}>
            Open journal
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
