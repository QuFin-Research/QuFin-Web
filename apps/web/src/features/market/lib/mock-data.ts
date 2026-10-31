// ============================================================
// Mock market data — deterministic stand-in for the QuFin API
// ============================================================
// Prices follow a random walk with a slowly-changing hidden drift. The mock
// "model" sees a noisy reading of that drift, which gives signals a realistic
// edge (roughly 55–60% directional hit rate, higher on high conviction) rather
// than the fake 90%+ numbers a demo would usually show.
//
// Everything is seeded by symbol and anchored to AS_OF, so server and client
// render identical data and backtests are reproducible.
// ============================================================

import type {
  Asset,
  Candle,
  Conviction,
  CountryScore,
  Regime,
  ScoreDimension,
  Signal,
  SignalDriver
} from '../api/types';

export const AS_OF = '2026-10-30';
export const HISTORY_DAYS = 780;
export const SIGNAL_HORIZON_DAYS = 5;

type AssetSpec = Asset & { basePrice: number; dailyVol: number };

export const ASSETS: AssetSpec[] = [
  { symbol: 'EURUSD', name: 'Euro / US Dollar', assetClass: 'FX', precision: 5, basePrice: 1.08, dailyVol: 0.0045 },
  { symbol: 'GBPUSD', name: 'British Pound / US Dollar', assetClass: 'FX', precision: 5, basePrice: 1.27, dailyVol: 0.005 },
  { symbol: 'USDJPY', name: 'US Dollar / Japanese Yen', assetClass: 'FX', precision: 3, basePrice: 148, dailyVol: 0.0055 },
  { symbol: 'AUDUSD', name: 'Australian Dollar / US Dollar', assetClass: 'FX', precision: 5, basePrice: 0.66, dailyVol: 0.006 },
  { symbol: 'XAUUSD', name: 'Gold', assetClass: 'Metals', precision: 2, basePrice: 2350, dailyVol: 0.009 },
  { symbol: 'XAGUSD', name: 'Silver', assetClass: 'Metals', precision: 3, basePrice: 28, dailyVol: 0.016 },
  { symbol: 'WTI', name: 'WTI Crude Oil', assetClass: 'Energy', precision: 2, basePrice: 78, dailyVol: 0.019 },
  { symbol: 'BRENT', name: 'Brent Crude Oil', assetClass: 'Energy', precision: 2, basePrice: 82, dailyVol: 0.018 },
  { symbol: 'NATGAS', name: 'Natural Gas (Henry Hub)', assetClass: 'Energy', precision: 3, basePrice: 2.6, dailyVol: 0.032 },
  { symbol: 'BTCUSD', name: 'Bitcoin', assetClass: 'Crypto', precision: 0, basePrice: 64000, dailyVol: 0.028 },
  { symbol: 'ETHUSD', name: 'Ether', assetClass: 'Crypto', precision: 1, basePrice: 3100, dailyVol: 0.034 }
];

function hashString(value: string) {
  let h = 2166136261;
  for (let i = 0; i < value.length; i++) {
    h ^= value.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

/** mulberry32 — small, fast, seedable PRNG */
function createRng(seed: number) {
  let a = seed;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function gaussian(rng: () => number) {
  const u = Math.max(rng(), 1e-12);
  const v = rng();
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
}

const sigmoid = (x: number) => 1 / (1 + Math.exp(-x));

/** Weekday dates ending at AS_OF, oldest first */
function tradingDays(count: number): string[] {
  const days: string[] = [];
  const d = new Date(`${AS_OF}T00:00:00Z`);
  while (days.length < count) {
    const dow = d.getUTCDay();
    if (dow !== 0 && dow !== 6) days.push(d.toISOString().slice(0, 10));
    d.setUTCDate(d.getUTCDate() - 1);
  }
  return days.toReversed();
}

export function convictionFor(probUp: number): Conviction {
  const edge = Math.abs(probUp - 0.5);
  if (edge >= 0.1) return 'high';
  if (edge >= 0.05) return 'medium';
  return 'low';
}

type Series = { candles: Candle[]; signals: Signal[]; drift: number[] };

const cache = new Map<string, Series>();

export function getSeries(symbol: string): Series | undefined {
  const spec = ASSETS.find((a) => a.symbol === symbol);
  if (!spec) return undefined;
  const cached = cache.get(symbol);
  if (cached) return cached;

  const rng = createRng(hashString(symbol));
  const days = tradingDays(HISTORY_DAYS);
  const sigma = spec.dailyVol;
  // Hidden drift: AR(1) with stationary s.d. of 0.15σ, persistent over a few weeks.
  const phi = 0.9;
  const driftSd = 0.15 * sigma;
  const driftShock = driftSd * Math.sqrt(1 - phi * phi);

  const candles: Candle[] = [];
  const signals: Signal[] = [];
  const driftPath: number[] = [];
  let drift = 0;
  let price = spec.basePrice;

  for (const time of days) {
    drift = phi * drift + driftShock * gaussian(rng);
    // Weak pull back towards the starting level keeps multi-year ranges realistic.
    const ret = drift - 0.01 * Math.log(price / spec.basePrice) + sigma * gaussian(rng);
    const open = price;
    const close = open * Math.exp(ret);
    const wick = () => Math.abs(gaussian(rng)) * sigma * 0.45;
    const high = Math.max(open, close) * (1 + wick());
    const low = Math.min(open, close) * (1 - wick());
    candles.push({ time, open, high, low, close });
    driftPath.push(drift);
    price = close;

    // The model observes the hidden drift with noise.
    const score = drift / driftSd + gaussian(rng);
    const probUp = sigmoid(0.35 * score);
    signals.push({
      time,
      probUp,
      direction: probUp >= 0.5 ? 'long' : 'short',
      conviction: convictionFor(probUp),
      horizonDays: SIGNAL_HORIZON_DAYS
    });
  }

  // Centre the path on the asset's reference level (geometric mean of closes).
  const meanLog = candles.reduce((sum, c) => sum + Math.log(c.close), 0) / candles.length;
  const scale = spec.basePrice / Math.exp(meanLog);
  for (const c of candles) {
    c.open *= scale;
    c.high *= scale;
    c.low *= scale;
    c.close *= scale;
  }

  const series = { candles, signals, drift: driftPath };
  cache.set(symbol, series);
  return series;
}

export function regimeFor(candles: Candle[]): Regime {
  const recent = candles.slice(-40);
  const rets = recent.slice(1).map((c, i) => Math.log(c.close / recent[i].close));
  const mean = rets.reduce((s, r) => s + r, 0) / rets.length;
  const vol = Math.sqrt(rets.reduce((s, r) => s + (r - mean) ** 2, 0) / rets.length);
  const longRets = candles.slice(-260);
  const longVol = Math.sqrt(
    longRets
      .slice(1)
      .map((c, i) => Math.log(c.close / longRets[i].close) ** 2)
      .reduce((s, r) => s + r, 0) /
      (longRets.length - 1)
  );
  if (vol > longVol * 1.35) return 'High volatility';
  const trendT = (mean / (vol || 1)) * Math.sqrt(rets.length);
  if (trendT > 1) return 'Uptrend';
  if (trendT < -1) return 'Downtrend';
  return 'Range';
}

/** Share of past signals whose direction matched the forward return */
export function hitRateFor(series: Series) {
  const { candles, signals } = series;
  let hits = 0;
  let total = 0;
  for (let i = 0; i + SIGNAL_HORIZON_DAYS < candles.length; i++) {
    const fwd = candles[i + SIGNAL_HORIZON_DAYS].close - candles[i].close;
    const up = signals[i].probUp >= 0.5;
    if ((fwd > 0) === up) hits++;
    total++;
  }
  return total ? hits / total : 0;
}

const DRIVERS: Record<Asset['assetClass'], { name: string; category: SignalDriver['category'] }[]> = {
  FX: [
    { name: '2Y rate differential', category: 'Fundamental' },
    { name: 'CFTC net positioning', category: 'Positioning' },
    { name: 'PMI surprise index', category: 'Macro' },
    { name: '20-day momentum', category: 'Technical' },
    { name: 'News sentiment', category: 'Sentiment' }
  ],
  Metals: [
    { name: 'US real yields', category: 'Fundamental' },
    { name: 'US Dollar index trend', category: 'Macro' },
    { name: 'CFTC managed-money positioning', category: 'Positioning' },
    { name: '50-day trend', category: 'Technical' },
    { name: 'Geopolitical risk index', category: 'Sentiment' }
  ],
  Energy: [
    { name: 'EIA inventory surprise', category: 'Fundamental' },
    { name: 'OPEC+ supply outlook', category: 'Macro' },
    { name: 'CFTC net positioning', category: 'Positioning' },
    { name: 'Term-structure carry', category: 'Technical' },
    { name: 'Geopolitical risk index', category: 'Sentiment' }
  ],
  Crypto: [
    { name: 'ETF net flows', category: 'Positioning' },
    { name: 'Global liquidity (M2)', category: 'Macro' },
    { name: 'Funding rates', category: 'Positioning' },
    { name: '20-day momentum', category: 'Technical' },
    { name: 'Social sentiment', category: 'Sentiment' }
  ]
};

/** Splits the latest score into signed driver contributions for the explainer */
export function driversFor(asset: Asset, signal: Signal): SignalDriver[] {
  const rng = createRng(hashString(`${asset.symbol}:${signal.time}`));
  const total = (signal.probUp - 0.5) * 10;
  const raw = DRIVERS[asset.assetClass].map(() => gaussian(rng) * 0.8 + total / 5);
  const sum = raw.reduce((s, v) => s + v, 0);
  const shift = (total - sum) / raw.length;
  return DRIVERS[asset.assetClass]
    .map((d, i) => ({ ...d, contribution: Number((raw[i] + shift).toFixed(2)) }))
    .toSorted((a, b) => Math.abs(b.contribution) - Math.abs(a.contribution));
}

const COUNTRIES: Omit<CountryScore, 'scores' | 'overall'>[] = [
  { code: 'US', country: 'United States', currency: 'USD' },
  { code: 'EA', country: 'Euro Area', currency: 'EUR' },
  { code: 'GB', country: 'United Kingdom', currency: 'GBP' },
  { code: 'JP', country: 'Japan', currency: 'JPY' },
  { code: 'CN', country: 'China', currency: 'CNY' },
  { code: 'CA', country: 'Canada', currency: 'CAD' },
  { code: 'AU', country: 'Australia', currency: 'AUD' },
  { code: 'CH', country: 'Switzerland', currency: 'CHF' },
  { code: 'SA', country: 'Saudi Arabia', currency: 'SAR' },
  { code: 'AE', country: 'United Arab Emirates', currency: 'AED' }
];

const DIMENSIONS: ScoreDimension[] = ['growth', 'inflation', 'labour', 'policy', 'sentiment'];

export function countryScores(): CountryScore[] {
  return COUNTRIES.map((c) => {
    const rng = createRng(hashString(`score:${c.code}:${AS_OF}`));
    const scores = Object.fromEntries(
      DIMENSIONS.map((d) => [d, Math.max(-3, Math.min(3, Math.round(gaussian(rng) * 1.4)))])
    ) as Record<ScoreDimension, number>;
    const overall = Number(
      (DIMENSIONS.reduce((s, d) => s + scores[d], 0) / DIMENSIONS.length).toFixed(1)
    );
    return { ...c, scores, overall };
  }).toSorted((a, b) => b.overall - a.overall);
}
