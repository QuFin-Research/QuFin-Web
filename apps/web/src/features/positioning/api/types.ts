import type { DataFreshness } from '@/lib/data-quality';

export type PositioningPoint = {
  /** Positions as of this Tuesday */
  reportDate: string;
  /** When the CFTC made the report public */
  releaseDate: string;
  openInterest: number;
  /** Large speculators' net contracts, in the asset's direction */
  net: number;
  /** Net position as a % of open interest */
  netPctOi: number;
  /** Net position within its 3-year range: 0 most bearish, 100 most bullish */
  cotIndex: number | null;
};

export type PositioningSnapshot = {
  symbol: string;
  contractCode: string;
  marketName: string;
  latest: PositioningPoint;
  weeklyChange: number | null;
  /** Limits of this contract as a view of the market */
  caveat: string | null;
  /** Release status as of the requested date */
  freshness: DataFreshness;
};

export type PositioningHistory = {
  symbol: string;
  contractCode: string;
  marketName: string;
  asOf: string | null;
  /** Limits of this contract as a view of the market */
  caveat: string | null;
  /** Release status as of the requested date */
  freshness: DataFreshness;
  points: PositioningPoint[];
};
