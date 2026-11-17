'use client';

import { useQuery } from '@tanstack/react-query';
import { Badge } from '@/components/ui/badge';
import { authQueries } from '@/features/auth/api/queries';
import { adminQueries } from '../api/queries';
import { adminAvailable } from '../api/service';
import { formatAgo, isStaff, scorecardBadge } from '../lib/admin-status';

/**
 * Beside the scorecard, for admins and data scientists only: whether the backend is keeping the
 * scorecard's data up to date. A user who is not staff sees nothing (and no request is made).
 */
export function ScorecardStatusBadge() {
  const { data: user } = useQuery(authQueries.me());
  const enabled = adminAvailable && isStaff(user?.role);
  const { data: status } = useQuery(adminQueries.status(enabled));
  if (!enabled || !status) return null;
  const s = status.scorecard;
  const badge = scorecardBadge(s.state);
  const detail = [
    s.reason,
    s.latestPeriod ? `Latest period ${s.latestPeriod}.` : null,
    `Data last loaded ${formatAgo(s.dataLoadedAt)}.`,
    s.overdueSeries.length ? `Overdue: ${s.overdueSeries.join(', ')}.` : null
  ]
    .filter(Boolean)
    .join(' ');
  return (
    <Badge variant={badge.tone} title={detail} data-testid='scorecard-backend-status'>
      Backend: {badge.label.toLowerCase()}
    </Badge>
  );
}
