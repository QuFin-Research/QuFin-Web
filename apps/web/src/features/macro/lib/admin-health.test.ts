import { describe, expect, it } from 'vitest';
import type { MacroSeriesSummary } from '../api/types';
import { adjustmentOf, healthBySource, percent } from './admin-health';

const make = (source: string, adjustment: string, status: string) =>
  ({
    source,
    seasonalAdjustment: adjustment,
    freshness: { status }
  }) as unknown as MacroSeriesSummary;

describe('admin health', () => {
  it('reads SA, NSA and other adjustments as the source words them', () => {
    expect(adjustmentOf('Seasonally Adjusted Annual Rate')).toBe('SA');
    expect(adjustmentOf('Not Seasonally Adjusted')).toBe('NSA');
    expect(adjustmentOf('Amplitude Adjusted (OECD)')).toBe('OTHER');
  });

  it('counts the release check and adjustment per source', () => {
    const rows = healthBySource([
      make('fred', 'Seasonally Adjusted', 'ok'),
      make('fred', 'Not Seasonally Adjusted', 'overdue'),
      make('ecb', 'Not Seasonally Adjusted', 'ok')
    ]);
    expect(rows[0]).toMatchObject({ source: 'fred', total: 2, ok: 1, notOk: 1, sa: 1, nsa: 1 });
    expect(rows[1]).toMatchObject({ source: 'ecb', total: 1, ok: 1, nsa: 1 });
  });

  it('gives a percentage and survives an empty whole', () => {
    expect(percent(1, 3)).toBe(33.3);
    expect(percent(0, 0)).toBe(0);
  });
});
