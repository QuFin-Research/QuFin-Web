import { describe, expect, it } from 'vitest';
import type { StudioResult, StudioSeries } from '../api/types';
import { canAdd, chartRows, flagEmoji, frequencyState, selectionCounter, toCsv } from './studio';

const base: Omit<StudioSeries, 'seriesId' | 'label' | 'points'> = {
  canonicalCode: null,
  iso3: 'USA',
  country: 'United States',
  concept: 'unemployment_rate',
  nativeFrequency: 'monthly',
  adjustment: 'SA',
  adjustmentText: 'Seasonally Adjusted',
  units: 'Percent',
  displayUnit: 'Percent',
  aggregation: null,
  metricNote: null,
  axis: 0,
  publisher: null,
  lastVintage: '2026-10-02',
  usable: true,
  statusNote: ''
};

const result: StudioResult = {
  data: 'live',
  mode: 'countries',
  name: 'Unemployment Rate',
  metric: 'actual',
  frequency: 'monthly',
  pocName: null,
  allowedFrequencies: ['monthly', 'quarterly'],
  restriction: null,
  notices: [],
  series: [
    {
      ...base,
      seriesId: 'UNRATE',
      label: 'Unemployment Rate (USA)',
      points: [
        { period: '2026-08-01', value: 4.1 },
        { period: '2026-09-01', value: 4.2 }
      ]
    },
    {
      ...base,
      seriesId: 'X',
      label: 'Rate, with comma',
      points: [{ period: '2026-09-01', value: 3 }]
    }
  ]
};

describe('studio helpers', () => {
  it('draws a flag from an ISO2 code and nothing from a bad one', () => {
    expect(flagEmoji('us')).toBe('🇺🇸');
    expect(flagEmoji('USA')).toBe('');
  });

  it('counts the selection against the cap', () => {
    expect(selectionCounter(3, 10)).toBe('3 / 10 countries selected');
    expect(canAdd(9, 10)).toBe(true);
    expect(canAdd(10, 10)).toBe(false);
  });

  it('disables the frequencies the API does not allow', () => {
    const state = frequencyState(['monthly', 'quarterly']);
    expect(state.find((f) => f.value === 'weekly')?.enabled).toBe(false);
    expect(state.find((f) => f.value === 'quarterly')?.enabled).toBe(true);
    expect(frequencyState(undefined).every((f) => f.enabled)).toBe(true);
  });

  it('puts every series on one row per period, with gaps left empty', () => {
    const rows = chartRows(result);
    expect(rows.map((r) => r.period)).toEqual(['2026-08-01', '2026-09-01']);
    expect(rows[0].X).toBeUndefined();
    expect(rows[1]).toMatchObject({ UNRATE: 4.2, X: 3 });
  });

  it('writes a CSV that carries unit, adjustment and frequency', () => {
    const lines = toCsv(result).split('\n');
    expect(lines[0]).toBe(
      'period,"Unemployment Rate (USA) [Percent, SA, monthly]","Rate, with comma [Percent, SA, monthly]"'
    );
    expect(lines[1]).toBe('2026-08-01,4.1,');
    expect(lines[2]).toBe('2026-09-01,4.2,3');
  });
});
