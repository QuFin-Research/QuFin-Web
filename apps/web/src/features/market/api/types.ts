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

export type CountryScore = {
  code: string;
  country: string;
  currency: string;
  /** Each dimension scored −3 (very weak) to +3 (very strong) */
  scores: Record<ScoreDimension, number>;
  overall: number;
};
