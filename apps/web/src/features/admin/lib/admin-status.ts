import type { Role } from '@/features/auth/api/types';
import type { AdminStatus, CoverageHeadline, JobRun, ScorecardState } from '../api/types';

/** Admins and data scientists may read the admin views. */
export const isStaff = (role: Role | undefined) => role === 'admin' || role === 'data_scientist';

/** Only admins may start a refresh: it calls outside data sources. */
export const canStartRefresh = (role: Role | undefined) => role === 'admin';

export type Tone = 'secondary' | 'outline' | 'destructive';

const BADGES: Record<ScorecardState, { label: string; tone: Tone }> = {
  updated: { label: 'Updated', tone: 'secondary' },
  partial: { label: 'Partly updated', tone: 'outline' },
  stale: { label: 'Not updating', tone: 'destructive' }
};

export function scorecardBadge(state: ScorecardState): { label: string; tone: Tone } {
  return BADGES[state];
}

/** The sentence shown at sign-in: how much is missing, in words a person can act on. */
export function coverageLine(h: CoverageHeadline): string {
  if (h.applicable === 0) return 'No coverage data yet.';
  if (h.countriesWithGaps === 0) return `All ${h.countries} countries have every indicator.`;
  const parts = [`${h.gap} not collected`];
  if (h.unusable > 0) parts.push(`${h.unusable} overdue or not loaded`);
  return (
    `${h.countriesWithGaps} of ${h.countries} countries are missing indicators ` +
    `(${parts.join(', ')}); ${h.coveragePct}% covered.`
  );
}

export function formatAgo(iso: string | null | undefined, now: Date = new Date()): string {
  if (!iso) return 'never';
  const seconds = Math.max(0, Math.round((now.getTime() - new Date(iso).getTime()) / 1000));
  if (seconds < 90) return 'just now';
  const minutes = Math.round(seconds / 60);
  if (minutes < 90) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 48) return `${hours} h ago`;
  return `${Math.round(hours / 24)} days ago`;
}

export type RefreshButton = { disabled: boolean; label: string; hint: string | null };

/** What the Run button says and whether it can be pressed. */
export function refreshButton(
  role: Role | undefined,
  status: AdminStatus | undefined,
  pending: boolean,
  now: Date = new Date()
): RefreshButton {
  if (!canStartRefresh(role)) {
    return { disabled: true, label: 'Run refresh', hint: 'Only admins can start a refresh.' };
  }
  if (pending || status?.running) {
    return { disabled: true, label: 'Refreshing…', hint: 'A refresh is running.' };
  }
  const allowed = status?.nextRefreshAllowedAt;
  if (allowed && new Date(allowed) > now) {
    const minutes = Math.ceil((new Date(allowed).getTime() - now.getTime()) / 60_000);
    return {
      disabled: true,
      label: 'Run refresh',
      hint: `The last refresh started recently; available again in ${minutes} min.`
    };
  }
  return { disabled: false, label: 'Run refresh', hint: null };
}

export function stepProgress(run: JobRun | null | undefined): { done: number; total: number } {
  const steps = run?.steps ?? [];
  const finished = steps.filter((s) => !['pending', 'running'].includes(s.status));
  return { done: finished.length, total: steps.length };
}

/** A banner and toast are worth showing when something needs attention. */
export function needsAttention(status: AdminStatus): boolean {
  return (
    status.scorecard.state !== 'updated' ||
    status.coverage.countriesWithGaps > 0 ||
    status.lastRun?.status === 'failed'
  );
}
