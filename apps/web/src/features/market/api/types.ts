export type AssetClass = 'FX' | 'Metals' | 'Energy' | 'Crypto';

export type Asset = {
  symbol: string;
  name: string;
  assetClass: AssetClass;
  /** Decimal places used when displaying prices */
  precision: number;
};

export type Candle = {
  /** Trading day, ISO date (YYYY-MM-DD) */
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
};

export type Direction = 'long' | 'short';

export type Conviction = 'low' | 'medium' | 'high';

export type Regime = 'Uptrend' | 'Downtrend' | 'Range' | 'High volatility';

/**
 * Model output for one asset on one day, made at that day's close and
 * forecasting the direction of the next `horizonDays` trading days.
 */
export type Signal = {
  time: string;
  /** Probability that price is higher after the horizon (0–1) */
  probUp: number;
  direction: Direction;
  conviction: Conviction;
  horizonDays: number;
};

export type SignalDriver = {
  name: string;
  category: 'Fundamental' | 'Technical' | 'Positioning' | 'Sentiment' | 'Macro';
  /** Signed contribution to the score; positive supports a long */
  contribution: number;
};

export type AssetSnapshot = {
  asset: Asset;
  lastPrice: number;
  changePct: number;
  regime: Regime;
  signal: Signal;
  /** Directional hit rate of past signals on this asset (walk-forward) */
  hitRate: number;
};

export type AssetDetail = AssetSnapshot & {
  candles: Candle[];
  signals: Signal[];
  drivers: SignalDriver[];
};

export type ScoreDimension = 'growth' | 'inflation' | 'labour' | 'policy' | 'sentiment';

export type ScorecardIndicator = {
  id: string;
  title: string;
  pillar: ScoreDimension;
  sourceName: string | null;
  /** Latest period used */
  period: string | null;
  /** Reading after the transform (level or % y/y) */
  value: number | null;
  /** −3..+3 against its own 10-year history */
  score: number | null;
  /** Importance × timeliness; 0 when not usable */
  weight: number;
  usable: boolean;
  status: string;
};

export type PendingRelease = {
  seriesId: string;
  title: string;
  sourceName: string | null;
  /** The period expected next */
  period: string | null;
  /** When the source publishes (or did) */
  sourceRelease: string | null;
  /** When FRED shows it */
  fredRelease: string | null;
  reason: string;
};

export type CountryScore = {
  code: string;
  country: string;
  currency: string;
  /** Each pillar −3 (very weak) to +3 (very strong): growth strong, inflation hot, labour tight, policy tight, sentiment upbeat */
  scores: Record<ScoreDimension, number>;
  overall: number;
  /** live: computed from the point-in-time macro store */
  data?: 'live' | 'sample';
  /** Share of each pillar's full evidence that is fresh and usable; never changes the score */
  confidence?: Record<ScoreDimension, number> | null;
  overallConfidence?: number | null;
  asOf?: string | null;
  indicators?: ScorecardIndicator[];
  /** Releases still to come that may move the scores */
  pending?: PendingRelease[];
};
