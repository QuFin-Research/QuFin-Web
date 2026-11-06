// ============================================================
// Chart views (rule 22 in RULEBOOK.md): the actual values, or the change over a year.
// Percent change only for strictly positive quantities and price/volume indexes ("pct");
// rates, spreads, ratios and diffusion indexes change in their own units ("diff");
// a series the source already publishes as a change gets no change view.
// ============================================================

export type ChartView = 'actual' | 'change';
export type ChangeKind = 'pct' | 'diff';
export type Point = { period: string; value: number | null };

const DAY = 86_400_000;
/** A year-ago reading may sit a few days off (weekends, week-ending dates). */
const TOLERANCE_DAYS = 7;

const toMs = (period: string) => Date.parse(`${period}T00:00:00Z`);

/** Change of every point against the same date a year earlier; null where it cannot be taken. */
export function yearOnYear(points: readonly Point[], kind: ChangeKind): Point[] {
  const ms = points.map((p) => toMs(p.period));
  const out: Point[] = [];
  let j = 0;
  for (let i = 0; i < points.length; i++) {
    const current = points[i];
    const target = new Date(ms[i]);
    target.setUTCFullYear(target.getUTCFullYear() - 1);
    const t = target.getTime();
    while (j + 1 < points.length && ms[j + 1] <= t) j++;
    const prior = points[j];
    let value: number | null = null;
    if (
      current.value !== null &&
      prior.value !== null &&
      ms[j] <= t &&
      t - ms[j] <= TOLERANCE_DAYS * DAY
    ) {
      if (kind === 'diff') value = current.value - prior.value;
      else if (prior.value > 0 && current.value > 0)
        value = (current.value / prior.value - 1) * 100;
    }
    out.push({ period: current.period, value });
  }
  return out;
}

/** The unit shown with the change view. */
export const changeUnit = (kind: ChangeKind) => (kind === 'pct' ? '%' : 'pt');
