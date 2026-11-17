import { describe, expect, it } from 'vitest';
import type { AdminStatus, CoverageHeadline, JobRun } from '../api/types';
import {
  canStartRefresh,
  coverageLine,
  formatAgo,
  isStaff,
  needsAttention,
  refreshButton,
  scorecardBadge,
  stepProgress
} from './admin-status';

const headline: CoverageHeadline = {
  countries: 87,
  countriesWithGaps: 84,
  applicable: 2697,
  have: 948,
  unusable: 8,
  gap: 1741,
  coveragePct: 35.2
};
const status = (over: Partial<AdminStatus> = {}): AdminStatus => ({
  data: 'live',
  scorecard: {
    state: 'updated',
    reason: '',
    latestPeriod: '2026-09-01',
    scoredSeries: 40,
    usableSeries: 40,
    overdueSeries: [],
    dataLoadedAt: null
  },
  coverage: headline,
  lastRun: null,
  running: false,
  nextRefreshAllowedAt: null,
  ...over
});
const NOW = new Date('2026-11-17T12:00:00Z');

describe('roles', () => {
  it('lets admins and data scientists read, and only admins run', () => {
    expect(isStaff('admin') && isStaff('data_scientist')).toBe(true);
    expect(isStaff('user') || isStaff(undefined)).toBe(false);
    expect(canStartRefresh('admin')).toBe(true);
    expect(canStartRefresh('data_scientist')).toBe(false);
  });
});

describe('coverage line', () => {
  it('says how many countries are missing what', () => {
    expect(coverageLine(headline)).toBe(
      '84 of 87 countries are missing indicators (1741 not collected, 8 overdue or not loaded); 35.2% covered.'
    );
  });
  it('is quiet when nothing is missing and honest when nothing is known', () => {
    expect(coverageLine({ ...headline, countriesWithGaps: 0 })).toBe(
      'All 87 countries have every indicator.'
    );
    expect(coverageLine({ ...headline, applicable: 0 })).toBe('No coverage data yet.');
  });
});

describe('scorecard badge', () => {
  it('marks a scorecard that is not updating as destructive', () => {
    expect(scorecardBadge('stale')).toEqual({ label: 'Not updating', tone: 'destructive' });
    expect(scorecardBadge('updated').tone).toBe('secondary');
  });
});

describe('refresh button', () => {
  it('is disabled for a data scientist, with the reason', () => {
    const b = refreshButton('data_scientist', status(), false, NOW);
    expect(b.disabled).toBe(true);
    expect(b.hint).toMatch(/admins/);
  });
  it('is disabled while a run is in progress or being started', () => {
    expect(refreshButton('admin', status({ running: true }), false, NOW).label).toBe('Refreshing…');
    expect(refreshButton('admin', status(), true, NOW).disabled).toBe(true);
  });
  it('waits out the minimum interval and then opens', () => {
    const soon = status({ nextRefreshAllowedAt: '2026-11-17T12:10:00Z' });
    const wait = refreshButton('admin', soon, false, NOW);
    expect(wait.disabled).toBe(true);
    expect(wait.hint).toMatch(/10 min/);
    expect(refreshButton('admin', soon, false, new Date('2026-11-17T12:11:00Z')).disabled).toBe(
      false
    );
  });
});

describe('formatting and progress', () => {
  it('says how long ago', () => {
    expect(formatAgo(null, NOW)).toBe('never');
    expect(formatAgo('2026-11-17T11:59:30Z', NOW)).toBe('just now');
    expect(formatAgo('2026-11-17T11:15:00Z', NOW)).toBe('45 min ago');
    expect(formatAgo('2026-11-17T06:00:00Z', NOW)).toBe('6 h ago');
    expect(formatAgo('2026-11-10T12:00:00Z', NOW)).toBe('7 days ago');
  });
  it('counts finished steps', () => {
    const run = {
      steps: [{ status: 'ok' }, { status: 'running' }, { status: 'skipped' }]
    } as unknown as JobRun;
    expect(stepProgress(run)).toEqual({ done: 2, total: 3 });
    expect(stepProgress(null)).toEqual({ done: 0, total: 0 });
  });
});

describe('needs attention', () => {
  it('is false only when updated, complete and the last run did not fail', () => {
    const clean = status({ coverage: { ...headline, countriesWithGaps: 0 } });
    expect(needsAttention(clean)).toBe(false);
    expect(needsAttention(status())).toBe(true);
    expect(needsAttention({ ...clean, lastRun: { status: 'failed' } as unknown as JobRun })).toBe(
      true
    );
  });
});
