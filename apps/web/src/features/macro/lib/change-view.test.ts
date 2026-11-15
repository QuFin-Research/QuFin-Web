import { describe, expect, it } from 'vitest';
import { changeUnit, yearOnYear } from './change-view';

const monthly = [
  { period: '2024-01-01', value: 100 },
  { period: '2024-02-01', value: 110 },
  { period: '2025-01-01', value: 120 },
  { period: '2025-02-01', value: 99 }
];
const round = (v: number | null) => (v === null ? null : Math.round(v * 10) / 10);

describe('yearOnYear (rule 22: change views)', () => {
  it('takes the percent change against the same month a year earlier', () => {
    expect(yearOnYear(monthly, 'pct').map((p) => round(p.value))).toEqual([null, null, 20, -10]);
  });

  it('takes the change in points for rates and spreads', () => {
    expect(yearOnYear(monthly, 'diff').map((p) => p.value)).toEqual([null, null, 20, -11]);
  });

  it('never takes a percent change across a zero or negative base', () => {
    const crossing = [
      { period: '2024-01-01', value: -5 },
      { period: '2025-01-01', value: 5 }
    ];
    expect(yearOnYear(crossing, 'pct').map((p) => p.value)).toEqual([null, null]);
    expect(
      yearOnYear(
        [
          { period: '2024-01-01', value: 0 },
          { period: '2025-01-01', value: 5 }
        ],
        'pct'
      ).map((p) => p.value)
    ).toEqual([null, null]);
  });

  it('takes the change in own units across zero (balances)', () => {
    const crossing = [
      { period: '2024-01-01', value: -5 },
      { period: '2025-01-01', value: 5 }
    ];
    expect(yearOnYear(crossing, 'diff').map((p) => p.value)).toEqual([null, 10]);
  });

  it('matches a week-ending date a few days off the year-ago date', () => {
    const weekly = [
      { period: '2024-03-01', value: 200 },
      { period: '2025-03-04', value: 220 }
    ];
    expect(yearOnYear(weekly, 'pct').map((p) => Math.round(p.value ?? 0))).toEqual([0, 10]);
  });

  it('matches a daily series across a weekend gap and a leap day', () => {
    const daily = [
      { period: '2024-02-29', value: 50 },
      { period: '2025-03-01', value: 55 } // a Saturday: matched to the 2024 reading
    ];
    expect(yearOnYear(daily, 'pct')[1].value).toBeCloseTo(10, 6);
  });

  it('returns null when the year-ago reading is missing or null', () => {
    expect(
      yearOnYear(
        [
          { period: '2024-01-01', value: 100 },
          { period: '2025-06-01', value: 120 }
        ],
        'pct'
      ).map((p) => p.value)
    ).toEqual([null, null]);
    expect(
      yearOnYear(
        [
          { period: '2024-01-01', value: null },
          { period: '2025-01-01', value: 5 }
        ],
        'diff'
      ).map((p) => p.value)
    ).toEqual([null, null]);
  });

  it('keeps every period and order', () => {
    expect(yearOnYear(monthly, 'pct').map((p) => p.period)).toEqual(monthly.map((p) => p.period));
  });
});

describe('changeUnit', () => {
  it('is percent for pct series and points for diff series', () => {
    expect(changeUnit('pct')).toBe('%');
    expect(changeUnit('diff')).toBe('pt');
  });
});
