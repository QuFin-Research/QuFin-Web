import { mutationOptions, queryOptions } from '@tanstack/react-query';
import { getAdminCoverage, getAdminJobs, getAdminStatus, startRefresh } from './service';

const POLL_WHILE_RUNNING = 3_000;
const POLL_IDLE = 60_000;

export const adminQueries = {
  all: () => ['admin'] as const,
  /** Only asked for by staff: everyone else would get a 403. */
  status: (enabled: boolean) =>
    queryOptions({
      queryKey: [...adminQueries.all(), 'status'] as const,
      queryFn: () => getAdminStatus(),
      enabled,
      retry: false,
      staleTime: 30_000,
      refetchInterval: (query) => (query.state.data?.running ? POLL_WHILE_RUNNING : POLL_IDLE)
    }),
  coverage: (enabled: boolean) =>
    queryOptions({
      queryKey: [...adminQueries.all(), 'coverage'] as const,
      queryFn: () => getAdminCoverage(),
      enabled,
      retry: false,
      staleTime: 30_000
    }),
  jobs: (enabled: boolean) =>
    queryOptions({
      queryKey: [...adminQueries.all(), 'jobs'] as const,
      queryFn: () => getAdminJobs(),
      enabled,
      retry: false
    })
};

export const adminMutations = {
  refresh: () => mutationOptions({ mutationFn: () => startRefresh() })
};
