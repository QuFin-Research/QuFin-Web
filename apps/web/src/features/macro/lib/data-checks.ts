import type { MacroSeriesSummary } from '../api/types';

/** Below this weight a series counts as arriving late (the weight halves every 60 days). */
export const LATE_WEIGHT = 0.75;

export type LateGroup = {
  /** Indicator name, shared across countries */
  name: string;
  count: number;
  minWeight: number;
  maxWeight: number;
  minDays: number;
  maxDays: number;
  /** Publishers behind the group, e.g. the BIS */
  publishers: string[];
};

export type DataHealth = {
  total: number;
  usable: number;
  unusable: MacroSeriesSummary[];
  /** FRED shows the series later than its source does */
  delayed: MacroSeriesSummary[];
  late: LateGroup[];
  lateCount: number;
};

/** One row per indicator instead of one entry per country, lowest weight first. */
export function groupLate(list: MacroSeriesSummary[]): LateGroup[] {
  const groups = new Map<string, LateGroup>();
  for (const s of list) {
    const { weight, daysAfterPeriodEnd: days } = s.timeliness;
    const g = groups.get(s.name);
    if (!g) {
      groups.set(s.name, {
        name: s.name,
        count: 1,
        minWeight: weight,
        maxWeight: weight,
        minDays: days,
        maxDays: days,
        publishers: s.sourceName ? [s.sourceName] : []
      });
      continue;
    }
    g.count += 1;
    g.minWeight = Math.min(g.minWeight, weight);
    g.maxWeight = Math.max(g.maxWeight, weight);
    g.minDays = Math.min(g.minDays, days);
    g.maxDays = Math.max(g.maxDays, days);
    if (s.sourceName && !g.publishers.includes(s.sourceName)) g.publishers.push(s.sourceName);
  }
  return [...groups.values()].toSorted(
    (a, b) => a.minWeight - b.minWeight || a.name.localeCompare(b.name)
  );
}

/** Splits the stored series into what must be shown: unusable, delayed at FRED, and late. */
export function dataHealth(list: MacroSeriesSummary[]): DataHealth {
  const unusable = list.filter((s) => !s.freshness.usable);
  const usable = list.filter((s) => s.freshness.usable);
  const delayed = usable
    .filter((s) => s.timeliness.fredDelayDays > 0)
    .toSorted((a, b) => b.timeliness.fredDelayDays - a.timeliness.fredDelayDays);
  const lateSeries = usable.filter((s) => s.timeliness.weight < LATE_WEIGHT);
  return {
    total: list.length,
    usable: usable.length,
    unusable,
    delayed,
    late: groupLate(lateSeries),
    lateCount: lateSeries.length
  };
}

/** "0.12" for one value, "0.51 to 0.60" for a range. */
export function range(min: number, max: number, digits = 2): string {
  const a = min.toFixed(digits);
  const b = max.toFixed(digits);
  return a === b ? a : `${a} to ${b}`;
}
