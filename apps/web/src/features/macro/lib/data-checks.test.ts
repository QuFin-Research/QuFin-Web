import { describe, expect, it } from 'vitest';
import type { MacroSeriesSummary } from '../api/types';
import { dataHealth, groupLate, range } from './data-checks';

function series(
  id: string,
  name: string,
  weight: number,
  days: number,
  extra: { usable?: boolean; fredDelayDays?: number; sourceName?: string } = {}
): MacroSeriesSummary {
  return {
    id,
    name,
    sourceName: extra.sourceName ?? 'BIS',
    freshness: { usable: extra.usable ?? true },
    timeliness: {
      weight,
      daysAfterPeriodEnd: days,
      fredDelayDays: extra.fredDelayDays ?? 0
    }
  } as unknown as MacroSeriesSummary;
}

describe('groupLate', () => {
  it('collapses the same indicator across countries into one row', () => {
    const rows = groupLate([
      series('A_GB', 'Credit-to-GDP Gap', 0.12, 181),
      series('A_JP', 'Credit-to-GDP Gap', 0.12, 181),
      series('B_GB', 'Foreign Exchange Reserves', 0.51, 59),
      series('B_JP', 'Foreign Exchange Reserves', 0.59, 46, { sourceName: 'IMF' })
    ]);
    expect(rows).toHaveLength(2);
    expect(rows[0]).toMatchObject({ name: 'Credit-to-GDP Gap', count: 2, minWeight: 0.12 });
    expect(rows[1]).toMatchObject({
      name: 'Foreign Exchange Reserves',
      count: 2,
      minWeight: 0.51,
      maxWeight: 0.59,
      minDays: 46,
      maxDays: 59,
      publishers: ['BIS', 'IMF']
    });
  });

  it('puts the lowest weight first', () => {
    const rows = groupLate([series('a', 'B', 0.5, 60), series('b', 'A', 0.2, 100)]);
    expect(rows.map((r) => r.name)).toEqual(['A', 'B']);
  });
});

describe('dataHealth', () => {
  const list = [
    series('1', 'Unemployment Rate', 1, 20),
    series('2', 'Old Series', 0.3, 200, { usable: false }),
    series('3', 'Consumer Confidence', 0.76, 30, { fredDelayDays: 30 }),
    series('4', 'Credit-to-GDP Gap', 0.12, 181)
  ];

  it('counts usable, unusable, delayed and late series', () => {
    const h = dataHealth(list);
    expect(h.total).toBe(4);
    expect(h.usable).toBe(3);
    expect(h.unusable.map((s) => s.id)).toEqual(['2']);
    expect(h.delayed.map((s) => s.id)).toEqual(['3']);
    expect(h.lateCount).toBe(1);
    expect(h.late[0].name).toBe('Credit-to-GDP Gap');
  });

  it('never counts an unusable series as late', () => {
    expect(dataHealth(list).late.map((g) => g.name)).not.toContain('Old Series');
  });
});

describe('range', () => {
  it('shows one value or a range', () => {
    expect(range(0.12, 0.12)).toBe('0.12');
    expect(range(0.51, 0.6)).toBe('0.51 to 0.60');
  });
});
