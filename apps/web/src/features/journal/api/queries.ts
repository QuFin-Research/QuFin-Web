import { mutationOptions, queryOptions } from '@tanstack/react-query';
import { createDecision, deleteDecision, getDecisions } from './service';
import type { NewDecision } from './types';

export const journalQueries = {
  all: () => ['journal'] as const,
  list: () =>
    queryOptions({
      queryKey: [...journalQueries.all(), 'list'] as const,
      queryFn: () => getDecisions()
    })
};

export const journalMutations = {
  create: () => mutationOptions({ mutationFn: (input: NewDecision) => createDecision(input) }),
  delete: () => mutationOptions({ mutationFn: (id: string) => deleteDecision(id) })
};
