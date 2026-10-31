'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import * as z from 'zod';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { FieldGroup } from '@/components/ui/field';
import { Icons } from '@/components/icons';
import { QuFinLogo } from '@/components/layout/logo';
import { useAppForm } from '@/lib/form';
import { authMutations, authQueries } from '../api/queries';
import { authEnabled } from '../api/service';

type Mode = 'sign-in' | 'sign-up';

const COPY: Record<Mode, { title: string; description: string; submit: string }> = {
  'sign-in': {
    title: 'Sign in',
    description: 'Welcome back. Your journal and backtests are waiting.',
    submit: 'Sign in'
  },
  'sign-up': {
    title: 'Create your account',
    description: 'Keep a decision journal and backtest your own trade plans.',
    submit: 'Create account'
  }
};

const schemas = {
  'sign-in': z.object({
    email: z.email('Enter a valid email address.'),
    password: z.string().min(1, 'Enter your password.')
  }),
  'sign-up': z.object({
    email: z.email('Enter a valid email address.'),
    password: z
      .string()
      .min(12, 'Use at least 12 characters. A short phrase works well.')
      .max(128, 'Use 128 characters or fewer.')
  })
};

/** Only same-site paths, so the `next` parameter cannot redirect off QuFin. */
function safeNext(next: string | null) {
  return next && next.startsWith('/') && !next.startsWith('//') ? next : '/dashboard/overview';
}

export function AuthForm({ mode }: { mode: Mode }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const mutation = useMutation(
    mode === 'sign-in' ? authMutations.signIn() : authMutations.signUp()
  );
  const copy = COPY[mode];
  const next = safeNext(searchParams.get('next'));

  const form = useAppForm({
    defaultValues: { email: '', password: '' },
    validators: { onSubmit: schemas[mode] },
    onSubmit: async ({ value }) => {
      setError(null);
      try {
        const user = await mutation.mutateAsync(value);
        // Drop anything cached for a previous user before showing this one's data.
        queryClient.clear();
        queryClient.setQueryData(authQueries.me().queryKey, user);
        router.replace(next);
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Something went wrong. Try again.');
      }
    }
  });

  const otherMode = mode === 'sign-in' ? 'sign-up' : 'sign-in';
  const otherHref = `/auth/${otherMode}${next === '/dashboard/overview' ? '' : `?next=${encodeURIComponent(next)}`}`;

  return (
    <div className='flex min-h-svh flex-col items-center justify-center gap-6 p-4'>
      <Link href='/' aria-label='QuFin home'>
        <QuFinLogo />
      </Link>
      <Card className='w-full max-w-sm'>
        <CardHeader>
          <CardTitle>{copy.title}</CardTitle>
          <CardDescription>{copy.description}</CardDescription>
        </CardHeader>
        <CardContent>
          {!authEnabled ? (
            <Alert>
              <Icons.info />
              <AlertDescription>
                Accounts need the QuFin API. Set NEXT_PUBLIC_API_URL, or{' '}
                <Link href='/dashboard/overview' className='underline'>
                  explore the demo
                </Link>{' '}
                on sample data.
              </AlertDescription>
            </Alert>
          ) : (
            <form
              noValidate
              onSubmit={(e) => {
                e.preventDefault();
                form.handleSubmit();
              }}
            >
              <FieldGroup>
                {error && (
                  <Alert variant='destructive'>
                    <Icons.alertCircle />
                    <AlertDescription>{error}</AlertDescription>
                  </Alert>
                )}
                <form.AppField
                  name='email'
                  children={(field) => (
                    <field.TextField label='Email' type='email' autoComplete='email' required />
                  )}
                />
                <form.AppField
                  name='password'
                  children={(field) => (
                    <field.TextField
                      label='Password'
                      type='password'
                      autoComplete={mode === 'sign-in' ? 'current-password' : 'new-password'}
                      description={mode === 'sign-up' ? 'At least 12 characters.' : undefined}
                      required
                    />
                  )}
                />
                <form.AppForm>
                  <form.SubmitButton className='w-full'>{copy.submit}</form.SubmitButton>
                </form.AppForm>
              </FieldGroup>
            </form>
          )}
        </CardContent>
      </Card>
      {authEnabled && (
        <p className='text-muted-foreground text-sm'>
          {mode === 'sign-in' ? 'New to QuFin? ' : 'Already have an account? '}
          <Link href={otherHref} className='text-foreground underline underline-offset-4'>
            {mode === 'sign-in' ? 'Create an account' : 'Sign in'}
          </Link>
        </p>
      )}
    </div>
  );
}
