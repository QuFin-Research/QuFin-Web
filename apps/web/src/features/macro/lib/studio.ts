import type { StudioFrequency, StudioResult } from '../api/types';

export const FREQUENCY_ORDER: StudioFrequency[] = [
  'daily',
  'weekly',
  'monthly',
  'quarterly',
  'semi_annual',
  'annual'
];

export const FREQUENCY_LABEL: Record<StudioFrequency, string> = {
  daily: 'Daily',
  weekly: 'Weekly',
  monthly: 'Monthly',
  quarterly: 'Quarterly',
  semi_annual: 'Semi-Annual',
  annual: 'Annual'
};

/** Line colours, distinct in light and dark; ten, the most a chart may hold. */
export const SERIES_COLORS = [
  '#2563eb',
  '#dc2626',
  '#16a34a',
  '#d97706',
  '#9333ea',
  '#0891b2',
  '#db2777',
  '#65a30d',
  '#475569',
  '#ea580c'
];

/** The flag of a country from its ISO2 code; empty if the code is not two letters. */
export function flagEmoji(iso2: string): string {
  if (!/^[A-Za-z]{2}$/.test(iso2)) return '';
  return [...iso2.toUpperCase()]
    .map((c) => String.fromCodePoint(127397 + c.charCodeAt(0)))
    .join('');
}

/** "3 / 10 countries selected". */
export function selectionCounter(count: number, max: number, noun = 'countries'): string {
  return `${count} / ${max} ${noun} selected`;
}

/** Whether another item may be added without passing the cap. */
export function canAdd(count: number, max: number): boolean {
  return count < max;
}

/** Which of the six frequencies are on offer, given what the API allows. */
export function frequencyState(
  allowed: StudioFrequency[] | undefined
): { value: StudioFrequency; enabled: boolean }[] {
  const on = new Set(allowed ?? FREQUENCY_ORDER);
  return FREQUENCY_ORDER.map((value) => ({ value, enabled: on.has(value) }));
}

export type ChartRow = { period: string } & Record<string, number | string | null>;

/** One row per period with a column per series, for a chart that shares one crosshair. */
export function chartRows(result: StudioResult): ChartRow[] {
  const rows = new Map<string, ChartRow>();
  for (const s of result.series) {
    for (const p of s.points) {
      const row = rows.get(p.period) ?? ({ period: p.period } as ChartRow);
      row[s.seriesId] = p.value;
      rows.set(p.period, row);
    }
  }
  return [...rows.values()].toSorted((a, b) => a.period.localeCompare(b.period));
}

function quote(value: string): string {
  return /[",\n]/.test(value) ? `"${value.replace(/"/g, '""')}"` : value;
}

/** The chart as CSV: a period column, then one column per series with its unit and tags. */
export function toCsv(result: StudioResult): string {
  const header = [
    'period',
    ...result.series.map(
      (s) => `${s.label} [${s.displayUnit}, ${s.adjustment}, ${result.frequency}]`
    )
  ];
  const lines = chartRows(result).map((row) =>
    [row.period, ...result.series.map((s) => (row[s.seriesId] ?? '').toString())]
      .map(String)
      .map(quote)
      .join(',')
  );
  return [header.map(quote).join(','), ...lines].join('\n');
}

/** A value for a tooltip or axis: grouped thousands, up to two decimals. */
export function formatValue(value: number): string {
  const digits = Math.abs(value) >= 1000 ? 0 : 2;
  return value.toLocaleString('en-US', { maximumFractionDigits: digits });
}
