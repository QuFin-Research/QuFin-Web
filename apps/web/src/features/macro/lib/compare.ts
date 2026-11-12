import type { Comparison } from '../api/types';

/** Position 0..1 of a value between zero and the largest, for the bar. Negative values show empty. */
export function compareScale(values: number[]): (v: number) => number {
  const max = Math.max(0, ...values);
  return (v) => (max <= 0 ? 0 : Math.min(1, Math.max(0, v / max)));
}

/** "1", "2", ... for ranked rows; unusable series are not ranked. */
export function rankLabel(index: number, usable: boolean): string {
  return usable ? String(index + 1) : '—';
}

/** A change in points: worse (up for prices and unemployment) reads red, better reads green. */
export function moveTone(value: number, higherIs: Comparison['higherIs']): string {
  if (value === 0) return 'text-muted-foreground';
  const worse = higherIs === 'worse' ? value > 0 : value < 0;
  return worse ? 'text-bear' : 'text-bull';
}

/** A figure with its unit, as the comparison states it: "3.7%". */
export function writeValue(value: number, unit: string): string {
  return `${value.toLocaleString('en-US', { minimumFractionDigits: 1, maximumFractionDigits: 1 })}${unit}`;
}

/** The SVG path of a small line chart that fills width x height; null with fewer than two points. */
export function sparkPath(values: number[], width: number, height: number): string | null {
  if (values.length < 2) return null;
  const min = Math.min(...values);
  const span = Math.max(...values) - min || 1;
  const pad = 2;
  return values
    .map((v, i) => {
      const x = (i / (values.length - 1)) * width;
      const y = height - pad - ((v - min) / span) * (height - 2 * pad);
      return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(' ');
}
