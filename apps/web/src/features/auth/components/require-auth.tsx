'use client';

import { useEffect } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { Spinner } from '@/components/ui/spinner';
import { authQueries } from '../api/queries';
import { authEnabled } from '../api/service';

/**
 * Shows its children only to a signed-in user and sends everyone else to
 * sign-in. A UX guard: the API enforces access on every request regardless.
 * With accounts disabled (no API configured) the demo stays open.
 */
export function RequireAuth({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const {
    data: user,
    isPending,
    isError
  } = useQuery({
    ...authQueries.me(),
    enabled: authEnabled
  });
  const signedOut = authEnabled && !isPending && !isError && user === null;

  useEffect(() => {
    if (signedOut) router.replace(`/auth/sign-in?next=${encodeURIComponent(pathname)}`);
  }, [signedOut, pathname, router]);

  if (!authEnabled) return children;
  if (isError) {
    return (
      <div className='text-muted-foreground flex min-h-svh items-center justify-center p-4 text-sm'>
        Can&apos;t reach the QuFin API right now. Check that it is running and reload.
      </div>
    );
  }
  if (isPending || signedOut) {
    return (
      <div
        className='flex min-h-svh items-center justify-center'
        role='status'
        aria-label='Checking your session'
      >
        <Spinner className='size-6' />
      </div>
    );
  }
  return children;
}
