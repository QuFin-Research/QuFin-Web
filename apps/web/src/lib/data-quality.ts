/** Release-schedule status the API attaches to every data series. */
export type DataFreshness = {
  status: 'ok' | 'overdue' | 'discontinued' | 'review';
  /** False when overdue, discontinued or awaiting review: not current data */
  usable: boolean;
  /** When the next release is expected */
  nextDue: string | null;
  /** Usual days from a period to its first release */
  typicalLagDays: number;
  daysOverdue: number;
  reason: string;
};

/** How late data reaches QuFin, and the weight it gets in scorecards. */
export type DataTimeliness = {
  /** 0-1: halves every 60 days between the end of a period and the day QuFin can read it */
  weight: number;
  sourceLagDays: number;
  /** Days FRED publishes after the source (licensing) */
  fredDelayDays: number;
  daysAfterPeriodEnd: number;
  /** When the source first published the latest period */
  latestSourceRelease: string | null;
  /** When FRED shows the latest period */
  latestFredRelease: string | null;
  delayNote: string | null;
};

export const FRESHNESS_LABEL: Record<DataFreshness['status'], string> = {
  ok: 'On schedule',
  overdue: 'Overdue',
  discontinued: 'Discontinued',
  review: 'Needs review'
};
