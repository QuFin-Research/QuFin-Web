export type CoverageHeadline = {
  countries: number;
  countriesWithGaps: number;
  /** Cells of the indicators that can exist for every country. */
  applicable: number;
  have: number;
  /** Stored but overdue, or declared and not loaded. */
  unusable: number;
  /** Not collected at all. */
  gap: number;
  coveragePct: number;
};

export type IndicatorGap = {
  concept: string;
  indicator: string;
  have: number;
  unusable: number;
  gap: number;
};

export type CountryGap = {
  iso3: string;
  country: string;
  have: number;
  unusable: number;
  gap: number;
};

export type CoverageSummary = {
  data: 'live';
  generatedAt: string;
  headline: CoverageHeadline;
  globalIndicators: number;
  byIndicator: IndicatorGap[];
  byCountry: CountryGap[];
  overdueSeries: string[];
};

export type StepStatus =
  | 'pending'
  | 'running'
  | 'ok'
  | 'overdue'
  | 'failed'
  | 'degraded'
  | 'skipped';

export type JobStep = {
  command: string;
  source: string;
  series: number;
  status: StepStatus;
  detail: string;
};

export type JobStatus = 'running' | 'succeeded' | 'failed' | 'interrupted';

export type JobRun = {
  data: 'live';
  id: string;
  job: string;
  status: JobStatus;
  requestedBy: string;
  startedAt: string;
  finishedAt: string | null;
  steps: JobStep[];
  error: string | null;
};

export type ScorecardState = 'updated' | 'partial' | 'stale';

export type ScorecardStatus = {
  state: ScorecardState;
  reason: string;
  latestPeriod: string | null;
  scoredSeries: number;
  usableSeries: number;
  overdueSeries: string[];
  dataLoadedAt: string | null;
};

export type AdminStatus = {
  data: 'live';
  scorecard: ScorecardStatus;
  coverage: CoverageHeadline;
  lastRun: JobRun | null;
  running: boolean;
  nextRefreshAllowedAt: string | null;
};
