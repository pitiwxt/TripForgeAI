/**
 * TravelStoreProvider — React Context provider for the Zustand store.
 *
 * Required for Next.js App Router to ensure per-request store isolation
 * and avoid global state leaking across SSR requests.
 */

"use client";

import {
  type ReactNode,
  createContext,
  useRef,
  useContext,
} from "react";
import { type StoreApi, useStore } from "zustand";
import { type TravelState, createTravelStore } from "@/stores/travel-store";

// ── Context ────────────────────────────────────────────────────────────
const TravelStoreContext = createContext<StoreApi<TravelState> | null>(null);

// ── Provider ───────────────────────────────────────────────────────────
export function TravelStoreProvider({ children }: { children: ReactNode }) {
  const storeRef = useRef<StoreApi<TravelState>>(undefined);

  if (!storeRef.current) {
    storeRef.current = createTravelStore();
  }

  return (
    <TravelStoreContext.Provider value={storeRef.current}>
      {children}
    </TravelStoreContext.Provider>
  );
}

// ── Hook ───────────────────────────────────────────────────────────────
/**
 * Custom hook to access the travel store with a selector.
 * ALWAYS use a selector to avoid unnecessary re-renders.
 *
 * @example
 * const messages = useTravelStore((s) => s.messages);
 * const sendMessage = useTravelStore((s) => s.sendMessage);
 */
export function useTravelStore<T>(selector: (state: TravelState) => T): T {
  const context = useContext(TravelStoreContext);

  if (!context) {
    throw new Error(
      "useTravelStore must be used within a TravelStoreProvider"
    );
  }

  return useStore(context, selector);
}
