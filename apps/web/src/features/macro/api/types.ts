import type { ScoreDimension } from '@/features/market/api/types';
import type { DataFreshness, DataTimeliness } from '@/lib/data-quality';

export type BusinessCycle = 'leading' | 'coincident' | 'lagging';

export type UnitKind =
  | 'amount_currency'
  | 'count'
  | 'index'
  | 'rate_percent'
  | 'ratio'
  | 'price_per_unit'
  | 'other'
  | 'unknown';

export type MacroSeries = {
  id: string;
  /** Human-readable name shown to users, shared across countries */
  name: string;
  /** One plain sentence on what the indicator measures */
  explanation: string;
  /** Concept key matching the same indicator across countries */
  concept: string;
  /** Global acronym of the indicator (CPI, PPI, GDP...), whatever the country calls its own */
  acronym: string | null;
  source: string;
  /** The source's official title (shown in the tooltip) */
  title: string;
  units: string;
  frequency: string;
  seasonalAdjustment: string;
  country: string;
  /** Scorecard pillar, or 'markets' for reference prices (not scored) */
  dimension: ScoreDimension | 'external' | 'fiscal' | 'energy' | 'markets' | 'housing';
  /** When the series tends to turn relative to the business cycle */
  cycle: BusinessCycle | null;
  /** When the source last revised the series */
  lastUpdated: string | null;
  /** Who produces the data, e.g. the BLS */
  /** Unit kind (rule 23): only series with the same kind, currency and unit share a scale */
  unitKind: UnitKind | null;
  /** ISO currency of amounts and prices; null when dimensionless */
  currency: string | null;
  sourceName: string | null;
  /** The publishing organisation under one spelling, for grouping */
  publisher: string | null;
  /** ISO3.PILLAR.INDICATOR.FREQ.ADJUSTMENT, unique across series */
  canonicalCode: string | null;
  /** GROWTH, INFLATION, LABOR, MONETARY, SURVEYS, CONSUMPTION, TRADE, FISCAL, ENERGY, MARKETS or HOUSING */
  pillar: string | null;
  countryIso3: string | null;
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

/** Indicators that can be compared across countries on one basis. */
export type ComparableConcept = 'consumer_prices' | 'unemployment_rate';

export type ComparisonPoint = { period: string; value: number };

export type ComparisonRow = {
  iso3: string;
  country: string;
  /** The source's own ticker */
  seriesId: string;
  canonicalCode: string | null;
  publisher: string | null;
  sourceName: string | null;
  /** Latest period, on the comparison basis */
  period: string;
  value: number;
  /** Points against three months earlier */
  change3M: number | null;
  /** Points against twelve months earlier */
  change12M: number | null;
  /** True when the stored series was converted to the basis (the US price index) */
  converted: boolean;
  /** The units the series is stored in, as the source states */
  storedAs: string;
  usable: boolean;
  statusNote: string;
  history: ComparisonPoint[];
};

export type Comparison = {
  data: 'live' | 'sample';
  concept: ComparableConcept;
  name: string;
  explanation: string;
  /** What the compared number is, e.g. "Year-on-year change" */
  basis: string;
  unit: string;
  /** How each country's stored series was brought to the basis */
  method: string;
  higherIs: 'worse' | 'better';
  /** Ranked, highest first; unusable series last */
  rows: ComparisonRow[];
  /** Countries in the taxonomy with no series yet */
  missing: { iso3: string; name: string }[];
};

export type StudioFrequency =
  | 'daily'
  | 'weekly'
  | 'monthly'
  | 'quarterly'
  | 'semi_annual'
  | 'annual';
export type StudioMetric = 'actual' | 'poc';
export type Adjustment = 'SA' | 'NSA' | 'OTHER';

export type StudioSeries = {
  seriesId: string;
  canonicalCode: string | null;
  iso3: string;
  country: string;
  label: string;
  concept: string | null;
  nativeFrequency: StudioFrequency;
  adjustment: Adjustment;
  adjustmentText: string;
  units: string;
  /** The unit of the points: the source's own, "%", "pp" or "as published" */
  displayUnit: string;
  /** How a faster series was collapsed to the display frequency; null when it was not */
  aggregation: 'end' | 'mean' | 'sum' | null;
  metricNote: string | null;
  /** Series sharing an axis share a unit (overlay charts) */
  axis: number;
  publisher: string | null;
  /** Release date of the latest published value */
  lastVintage: string | null;
  usable: boolean;
  statusNote: string;
  points: { period: string; value: number }[];
};

export type StudioResult = {
  data: 'live' | 'sample';
  mode: 'countries' | 'indicators';
  name: string;
  metric: StudioMetric;
  frequency: StudioFrequency;
  pocName: string | null;
  allowedFrequencies: StudioFrequency[];
  /** Why some frequencies are unavailable */
  restriction: string | null;
  notices: string[];
  series: StudioSeries[];
};

export type StudioCatalogSeries = {
  seriesId: string;
  canonicalCode: string | null;
  iso3: string;
  concept: string | null;
  name: string;
  nativeFrequency: StudioFrequency;
  adjustment: Adjustment;
  units: string;
  source: string;
  publisher: string | null;
  lastPeriod: string | null;
  lastUpdated: string | null;
};

export type StudioCatalog = {
  data: 'live' | 'sample';
  maxCountries: number;
  frequencies: StudioFrequency[];
  indicators: { concept: string; name: string; explanation: string; countries: string[] }[];
  series: StudioCatalogSeries[];
};

export type StudioCountry = { iso3: string; iso2: string; name: string };

export type StudioQuery =
  | {
      mode: 'countries';
      concept: string;
      countries: string[];
      frequency: StudioFrequency | null;
      metric: StudioMetric;
      years: number;
    }
  | {
      mode: 'indicators';
      country: string;
      seriesIds: string[];
      frequency: StudioFrequency | null;
      metric: StudioMetric;
      years: number;
    };
