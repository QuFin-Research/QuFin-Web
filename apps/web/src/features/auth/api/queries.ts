import { mutationOptions, queryOptions } from '@tanstack/react-query';
import { getCurrentUser, signIn, signOut, signUp } from './service';
import type { Credentials } from './types';

export const authQueries = {
  all: () => ['auth'] as const,
  me: () =>
    queryOptions({
      queryKey: [...authQueries.all(), 'me'] as const,
      queryFn: () => getCurrentUser(),
      staleTime: 5 * 60 * 1000
    })
};

export const authMutations = {
  signIn: () => mutationOptions({ mutationFn: (credentials: Credentials) => signIn(credentials) }),
  signUp: () => mutationOptions({ mutationFn: (credentials: Credentials) => signUp(credentials) }),
  signOut: () => mutationOptions({ mutationFn: () => signOut() })
};
