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

export type MacroSeriesSummary = MacroSeries & {
  ingestedAt: string;
  firstPeriod: string | null;
  lastPeriod: string | null;
  vintageRows: number;
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
