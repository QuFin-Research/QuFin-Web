// ============================================================
// Admin Service — coverage, scorecard freshness and the refresh button
// ============================================================
//   GET  /v1/admin/status | /coverage | /jobs | /jobs/{id}   (admin or data scientist)
//   POST /v1/admin/jobs/refresh                              (admin only)
//
// The API decides who may call these (roles come from its settings); the web app only hides
// what a user cannot use.
// ============================================================

import { apiClient, isApiConfigured } from '@/lib/api-client';
import type { AdminStatus, CoverageSummary, JobRun } from './types';

export const adminAvailable = isApiConfigured;

export const getAdminStatus = () => apiClient<AdminStatus>('/v1/admin/status');
export const getAdminCoverage = () => apiClient<CoverageSummary>('/v1/admin/coverage');
export const getAdminJobs = () => apiClient<JobRun[]>('/v1/admin/jobs?limit=5');

/** An empty JSON body: the API requires one, so a cross-site form cannot start a run. */
export const startRefresh = () =>
  apiClient<JobRun>('/v1/admin/jobs/refresh', { method: 'POST', body: '{}' });
