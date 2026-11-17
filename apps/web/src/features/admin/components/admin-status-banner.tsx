'use client';

import { useEffect } from 'react';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { authQueries } from '@/features/auth/api/queries';
import { adminQueries } from '../api/queries';
import { adminAvailable } from '../api/service';
import {
  coverageLine,
  formatAgo,
  isStaff,
  needsAttention,
  scorecardBadge
} from '../lib/admin-status';

const TOAST_KEY = 'qufin-admin-status-toast';

/**
 * What admins and data scientists see at every sign-in, on every dashboard page: how much data
 * is missing and whether the scorecard is being kept up to date. Nobody else gets it (the API
 * answers 403 and this asks only for staff).
 */
export function AdminStatusBanner() {
  const { data: user } = useQuery(authQueries.me());
  const enabled = adminAvailable && isStaff(user?.role);
  const { data: status } = useQuery(adminQueries.status(enabled));

  // One toast per browser session, so signing in shows it and navigating does not repeat it.
  const attention = status ? needsAttention(status) : false;
  useEffect(() => {
    if (!status || !attention) return;
    try {
      if (sessionStorage.getItem(TOAST_KEY)) return;
      sessionStorage.setItem(TOAST_KEY, '1');
    } catch {
      // Storage blocked: show the banner only.
      return;
    }
    toast.warning(coverageLine(status.coverage), {
      description: `Scorecard: ${scorecardBadge(status.scorecard.state).label.toLowerCase()}.`
    });
  }, [status, attention]);

  if (!enabled || !status) return null;
  const badge = scorecardBadge(status.scorecard.state);
  const bad = status.scorecard.state === 'stale' || status.lastRun?.status === 'failed';
  return (
    <div className='px-4 pt-3 md:px-6'>
      <Alert variant={bad ? 'destructive' : 'default'}>
        <AlertTitle>
          Scorecard: {badge.label.toLowerCase()}
          {status.running ? ' · refresh running' : ''}
        </AlertTitle>
        <AlertDescription>
          <span>
            {coverageLine(status.coverage)} {status.scorecard.reason} Last refresh:{' '}
            {status.lastRun
              ? `${status.lastRun.status} ${formatAgo(status.lastRun.startedAt)}`
              : 'never'}
            .{' '}
          </span>
          <Link href='/dashboard/admin/data-health' className='underline underline-offset-4'>
            Open data health
          </Link>
        </AlertDescription>
      </Alert>
    </div>
  );
}
