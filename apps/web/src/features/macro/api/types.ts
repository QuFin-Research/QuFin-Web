import type { ScoreDimension } from '@/features/market/api/types';

export type MacroSeries = {
  id: string;
  source: string;
  title: string;
  units: string;
  frequency: string;
  seasonalAdjustment: string;
  country: string;
  dimension: ScoreDimension;
  /** When the source last revised the series */
  lastUpdated: string | null;
};

export type MacroSeriesSummary = MacroSeries & {
  ingestedAt: string;
  firstPeriod: string | null;
  lastPeriod: string | null;
  vintageRows: number;
};

export type MacroObservation = {
  period: string;
  value: number | null;
  /** When this value was first published */
  realtimeStart: string;
};

export type MacroSeriesData = {
  series: MacroSeries;
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
