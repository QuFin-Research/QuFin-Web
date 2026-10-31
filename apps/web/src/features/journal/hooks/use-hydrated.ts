import { useSyncExternalStore } from 'react';

const subscribe = () => () => {};

/**
 * False during SSR and the first client render, true afterwards.
 * The journal lives in localStorage, so it must not render on the server.
 */
export function useHydrated() {
  return useSyncExternalStore(
    subscribe,
    () => true,
    () => false
  );
}
