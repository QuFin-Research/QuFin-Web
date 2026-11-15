import type { Adjustment, MacroSeriesSummary } from '../api/types';

export type SourceHealth = {
  source: string;
  total: number;
  ok: number;
  /** Overdue, discontinued or awaiting review */
  notOk: number;
  sa: number;
  nsa: number;
  other: number;
};

/** The adjustment as the source states it: seasonally adjusted, not, or another treatment. */
export function adjustmentOf(text: string): Adjustment {
  const lowered = text.toLowerCase();
  if (lowered.startsWith('not seasonally') || lowered.startsWith('not adjusted')) return 'NSA';
  if (lowered.startsWith('seasonally')) return 'SA';
  return 'OTHER';
}

/** One row per source with its release check and SA / NSA coverage, largest source first. */
export function healthBySource(series: MacroSeriesSummary[]): SourceHealth[] {
  const rows = new Map<string, SourceHealth>();
  for (const s of series) {
    const row = rows.get(s.source) ?? {
      source: s.source,
      total: 0,
      ok: 0,
      notOk: 0,
      sa: 0,
      nsa: 0,
      other: 0
    };
    row.total += 1;
    if (s.freshness.status === 'ok') row.ok += 1;
    else row.notOk += 1;
    const tag = adjustmentOf(s.seasonalAdjustment);
    if (tag === 'SA') row.sa += 1;
    else if (tag === 'NSA') row.nsa += 1;
    else row.other += 1;
    rows.set(s.source, row);
  }
  return [...rows.values()].toSorted(
    (a, b) => b.total - a.total || a.source.localeCompare(b.source)
  );
}

/** Share 0-100 of a part, one decimal; 0 for an empty whole. */
export function percent(part: number, whole: number): number {
  return whole === 0 ? 0 : Math.round((part / whole) * 1000) / 10;
}
