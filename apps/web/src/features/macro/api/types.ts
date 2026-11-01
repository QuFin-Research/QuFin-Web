import type { ScoreDimension } from '@/features/market/api/types';
import type { DataFreshness, DataTimeliness } from '@/lib/data-quality';

export type BusinessCycle = 'leading' | 'coincident' | 'lagging';

export type MacroSeries = {
  id: string;
  source: string;
  title: string;
  units: string;
  frequency: string;
  seasonalAdjustment: string;
  country: string;
  dimension: ScoreDimension;
  /** When the series tends to turn relative to the business cycle */
  cycle: BusinessCycle | null;
  /** When the source last revised the series */
  lastUpdated: string | null;
  /** Who produces the data, e.g. the BLS */
  sourceName: string | null;
  /** The release the series is published in */
  releaseName: string | null;
};

export type SeriesChange = {
  /** "1m", "3m", "1y"; "q/q" and "y/y" for quarterly series */
  horizon: string;
  value: number;
  /** "%", "% ann." (annualised) or "pt" (in the series' own units) */
  unit: string;
};

export type MacroSeriesSummary = MacroSeries & {
  ingestedAt: string;
  firstPeriod: string | null;
  lastPeriod: string | null;
  vintageRows: number;
  /** pct: percent change; diff: change in the series' own units */
  changeKind: 'pct' | 'diff';
  /** The source already publishes it as a change or growth rate */
  publishedAsChange: boolean;
  /** Latest moves, each within one vintage */
  changes: SeriesChange[];
  freshness: DataFreshness;
  timeliness: DataTimeliness;
};

export type MacroObservation = {
  period: string;
  value: number | null;
  /** When this value was first published */
  realtimeStart: string;
};

export type MacroSeriesData = {
  series: MacroSeries;
  /** Release status of the series today */
  freshness: DataFreshness;
  timeliness: DataTimeliness;
  /** Latest moves as published on asOf */
  changes: SeriesChange[];
  /** Real-time date of this view; null means latest */
  asOf: string | null;
  observations: MacroObservation[];
};

export type MacroRevision = {
  realtimeStart: string;
  /** Null while this is still the current value */
  realtimeEnd: string | null;
  value: number | null;
};

export type MacroRevisionHistory = {
  series: MacroSeries;
  period: string;
  revisions: MacroRevision[];
};

export type MacroSeriesFilters = {
  asOf?: string;
  start?: string;
};
