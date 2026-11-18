'use client';

import { useEffect, useRef } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from '@/components/ui/empty';
import { Progress } from '@/components/ui/progress';
import { Skeleton } from '@/components/ui/skeleton';
import { Spinner } from '@/components/ui/spinner';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from '@/components/ui/table';
import { authQueries } from '@/features/auth/api/queries';
import { adminMutations, adminQueries } from '../api/queries';
import { adminAvailable } from '../api/service';
import type { JobRun, StepStatus } from '../api/types';
import {
  coverageLine,
  formatAgo,
  isStaff,
  refreshButton,
  scorecardBadge,
  stepProgress
} from '../lib/admin-status';

const STEP_TONE: Record<StepStatus, 'secondary' | 'outline' | 'destructive'> = {
  pending: 'outline',
  running: 'outline',
  ok: 'secondary',
  overdue: 'outline',
  failed: 'destructive',
  degraded: 'destructive',
  skipped: 'outline'
};

function Tile({ label, value, note }: { label: string; value: string; note?: string }) {
  return (
    <div className='rounded-lg border p-3'>
      <div className='text-muted-foreground text-xs'>{label}</div>
      <div className='text-2xl font-semibold tabular-nums'>{value}</div>
      {note ? <div className='text-muted-foreground text-xs'>{note}</div> : null}
    </div>
  );
}

function LastRun({ run }: { run: JobRun }) {
  const { done, total } = stepProgress(run);
  const tone =
    run.status === 'failed' || run.status === 'interrupted' ? 'destructive' : 'secondary';
  return (
    <div className='space-y-3'>
      <div className='flex flex-wrap items-center gap-2 text-sm'>
        <Badge variant={run.status === 'running' ? 'outline' : tone}>
          {run.status === 'running' ? 'Running' : run.status}
        </Badge>
        <span className='text-muted-foreground'>
          started {formatAgo(run.startedAt)} by {run.requestedBy}
          {run.finishedAt ? `, finished ${formatAgo(run.finishedAt)}` : ''}
        </span>
      </div>
      {total > 0 ? (
        <Progress value={total ? (100 * done) / total : 0}>
          <span className='text-muted-foreground text-xs'>
            {done} of {total} steps
          </span>
        </Progress>
      ) : (
        <p className='text-muted-foreground text-sm'>Nothing was due: no series needed loading.</p>
      )}
      {run.error ? <p className='text-destructive text-sm'>{run.error}</p> : null}
      {total > 0 ? (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Source</TableHead>
              <TableHead className='text-right'>Series</TableHead>
              <TableHead>Result</TableHead>
              <TableHead className='hidden md:table-cell'>Detail</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {run.steps.map((step, i) => (
              <TableRow key={`${step.command}-${i}`}>
                <TableCell className='font-medium'>{step.source}</TableCell>
                <TableCell className='text-right tabular-nums'>{step.series}</TableCell>
                <TableCell>
                  <Badge variant={STEP_TONE[step.status]}>
                    {step.status === 'running' ? <Spinner className='mr-1 size-3' /> : null}
                    {step.status}
                  </Badge>
                </TableCell>
                <TableCell className='text-muted-foreground hidden max-w-md truncate md:table-cell'>
                  {step.detail}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      ) : null}
    </div>
  );
}

export function CoveragePanel() {
  const queryClient = useQueryClient();
  const { data: user, isPending: userPending } = useQuery(authQueries.me());
  const staff = isStaff(user?.role);
  const enabled = adminAvailable && staff;
  const { data: status } = useQuery(adminQueries.status(enabled));
  const { data: coverage, error } = useQuery(adminQueries.coverage(enabled));
  const refresh = useMutation({
    ...adminMutations.refresh(),
    onError: (e) => toast.error(e.message),
    onSettled: () => queryClient.invalidateQueries({ queryKey: adminQueries.all() })
  });

  // When a run finishes, the numbers above it may have changed: read them again.
  const wasRunning = useRef(false);
  const running = status?.running ?? false;
  useEffect(() => {
    if (wasRunning.current && !running) {
      void queryClient.invalidateQueries({ queryKey: [...adminQueries.all(), 'coverage'] });
    }
    wasRunning.current = running;
  }, [running, queryClient]);

  if (!adminAvailable) {
    return (
      <Empty className='border'>
        <EmptyHeader>
          <EmptyTitle>No API connected</EmptyTitle>
          <EmptyDescription>Set NEXT_PUBLIC_API_URL to connect the admin views.</EmptyDescription>
        </EmptyHeader>
      </Empty>
    );
  }
  if (userPending) return <Skeleton className='h-64 w-full rounded-xl' />;
  if (!staff) {
    return (
      <Empty className='border'>
        <EmptyHeader>
          <EmptyTitle>Admins and data scientists only</EmptyTitle>
          <EmptyDescription>
            Your account does not have access to the coverage view. Roles are set on the server.
          </EmptyDescription>
        </EmptyHeader>
      </Empty>
    );
  }
  if (error) {
    return (
      <Empty className='border'>
        <EmptyHeader>
          <EmptyTitle>Could not load coverage</EmptyTitle>
          <EmptyDescription>{error.message}</EmptyDescription>
        </EmptyHeader>
      </Empty>
    );
  }
  if (!coverage || !status) return <Skeleton className='h-64 w-full rounded-xl' />;

  const h = coverage.headline;
  const button = refreshButton(user?.role, status, refresh.isPending);
  const badge = scorecardBadge(status.scorecard.state);
  return (
    <div className='space-y-4'>
      <Card>
        <CardHeader>
          <CardTitle className='flex flex-wrap items-center gap-2'>
            Data coverage
            <Badge variant={badge.tone} title={status.scorecard.reason}>
              Scorecard: {badge.label}
            </Badge>
          </CardTitle>
          <CardDescription>{coverageLine(h)}</CardDescription>
        </CardHeader>
        <CardContent className='space-y-4'>
          <div className='grid grid-cols-2 gap-3 md:grid-cols-4'>
            <Tile
              label='Countries with gaps'
              value={`${h.countriesWithGaps} / ${h.countries}`}
              note='of the indicators that can exist for them'
            />
            <Tile label='Not collected' value={String(h.gap)} note='country-indicator pairs' />
            <Tile
              label='Overdue or not loaded'
              value={String(h.unusable)}
              note={
                coverage.overdueSeries.length
                  ? `${coverage.overdueSeries.length} stored series past their release`
                  : undefined
              }
            />
            <Tile
              label='Covered'
              value={`${h.coveragePct}%`}
              note={`${h.have} of ${h.applicable} pairs, ${coverage.globalIndicators} indicators`}
            />
          </div>
          <div className='grid gap-4 lg:grid-cols-2'>
            <div>
              <h3 className='mb-2 text-sm font-medium'>Indicators missing in most countries</h3>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Indicator</TableHead>
                    <TableHead className='text-right'>Have</TableHead>
                    <TableHead className='text-right'>Overdue</TableHead>
                    <TableHead className='text-right'>Missing</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {coverage.byIndicator.map((row) => (
                    <TableRow key={row.concept}>
                      <TableCell>{row.indicator}</TableCell>
                      <TableCell className='text-right tabular-nums'>{row.have}</TableCell>
                      <TableCell className='text-right tabular-nums'>{row.unusable}</TableCell>
                      <TableCell className='text-right font-medium tabular-nums'>
                        {row.gap}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
            <div>
              <h3 className='mb-2 text-sm font-medium'>Countries missing the most indicators</h3>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Country</TableHead>
                    <TableHead className='text-right'>Have</TableHead>
                    <TableHead className='text-right'>Overdue</TableHead>
                    <TableHead className='text-right'>Missing</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {coverage.byCountry.map((row) => (
                    <TableRow key={row.iso3}>
                      <TableCell>{row.country}</TableCell>
                      <TableCell className='text-right tabular-nums'>{row.have}</TableCell>
                      <TableCell className='text-right tabular-nums'>{row.unusable}</TableCell>
                      <TableCell className='text-right font-medium tabular-nums'>
                        {row.gap}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Refresh data</CardTitle>
          <CardDescription>
            Loads what the sources have published since, for the series that are due or overdue, one
            source at a time. Scorecard: {status.scorecard.reason} Last data loaded{' '}
            {formatAgo(status.scorecard.dataLoadedAt)}.
          </CardDescription>
        </CardHeader>
        <CardContent className='space-y-4'>
          <div className='flex flex-wrap items-center gap-3'>
            <Button disabled={button.disabled} onClick={() => refresh.mutate()}>
              {status.running || refresh.isPending ? <Spinner className='mr-2 size-4' /> : null}
              {button.label}
            </Button>
            {button.hint ? (
              <span className='text-muted-foreground text-sm'>{button.hint}</span>
            ) : null}
          </div>
          {status.lastRun ? (
            <LastRun run={status.lastRun} />
          ) : (
            <p className='text-muted-foreground text-sm'>No refresh has been run yet.</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
