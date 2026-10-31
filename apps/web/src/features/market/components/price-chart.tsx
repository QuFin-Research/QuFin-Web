'use client';

import { useEffect, useRef, useState } from 'react';
import { useTheme } from 'next-themes';
import {
  CandlestickSeries,
  ColorType,
  createChart,
  createSeriesMarkers,
  type IChartApi,
  type SeriesMarker,
  type Time
} from 'lightweight-charts';
import { Button } from '@/components/ui/button';
import type { Candle, Signal } from '@/features/market/api/types';
import { resolveCssColor } from '@/features/market/lib/format';

const RANGES = [
  { label: '3M', days: 63 },
  { label: '6M', days: 126 },
  { label: '1Y', days: 252 },
  { label: 'All', days: 0 }
] as const;

/** Marks each flip in the high-conviction call, so the chart shows when the model changed its mind */
function signalMarkers(signals: Signal[], bull: string, bear: string): SeriesMarker<Time>[] {
  const markers: SeriesMarker<Time>[] = [];
  let last: Signal['direction'] | null = null;
  for (const s of signals) {
    if (s.conviction !== 'high' || s.direction === last) continue;
    last = s.direction;
    const long = s.direction === 'long';
    markers.push({
      time: s.time as Time,
      position: long ? 'belowBar' : 'aboveBar',
      shape: long ? 'arrowUp' : 'arrowDown',
      color: long ? bull : bear,
      size: 0.8
    });
  }
  return markers;
}

export function PriceChart({
  candles,
  signals,
  precision
}: {
  candles: Candle[];
  signals: Signal[];
  precision: number;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const [range, setRange] = useState<(typeof RANGES)[number]['label']>('6M');
  const { resolvedTheme } = useTheme();

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const bull = resolveCssColor('var(--bull)', '#10b981');
    const bear = resolveCssColor('var(--bear)', '#ef4444');
    const text = resolveCssColor('var(--muted-foreground)');
    const grid = resolveCssColor('var(--border)');

    const chart = createChart(el, {
      autoSize: true,
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: text,
        fontFamily: 'inherit',
        attributionLogo: true
      },
      grid: { vertLines: { color: grid }, horzLines: { color: grid } },
      rightPriceScale: { borderColor: grid },
      timeScale: { borderColor: grid },
      crosshair: { mode: 0 }
    });
    const series = chart.addSeries(CandlestickSeries, {
      upColor: bull,
      downColor: bear,
      borderVisible: false,
      wickUpColor: bull,
      wickDownColor: bear,
      priceFormat: { type: 'price', precision, minMove: 1 / 10 ** precision }
    });
    series.setData(candles.map((c) => ({ ...c, time: c.time as Time })));
    createSeriesMarkers(series, signalMarkers(signals, bull, bear));
    chartRef.current = chart;

    return () => {
      chart.remove();
      chartRef.current = null;
    };
    // resolvedTheme: rebuild so the chart picks up the new theme colours
    // oxlint-disable-next-line react/exhaustive-effect-dependencies
  }, [candles, signals, precision, resolvedTheme]);

  useEffect(() => {
    const chart = chartRef.current;
    if (!chart) return;
    const days = RANGES.find((r) => r.label === range)?.days ?? 0;
    if (days === 0) chart.timeScale().fitContent();
    else chart.timeScale().setVisibleLogicalRange({ from: candles.length - days, to: candles.length + 2 });
    // resolvedTheme: re-apply the range after a theme rebuild
    // oxlint-disable-next-line react/exhaustive-effect-dependencies
  }, [range, candles.length, resolvedTheme]);

  return (
    <div className='flex flex-col gap-2'>
      <div className='flex items-center justify-between gap-2'>
        <p className='text-muted-foreground text-xs'>
          Arrows mark each change in the high-conviction call.
        </p>
        <div className='flex gap-1'>
          {RANGES.map((r) => (
            <Button
              key={r.label}
              size='xs'
              variant={range === r.label ? 'secondary' : 'ghost'}
              onClick={() => setRange(r.label)}
            >
              {r.label}
            </Button>
          ))}
        </div>
      </div>
      <div ref={containerRef} className='h-[380px] w-full' />
    </div>
  );
}
