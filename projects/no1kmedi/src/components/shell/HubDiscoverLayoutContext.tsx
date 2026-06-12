"use client";

import { createContext, useContext, type ReactNode } from "react";

type HubDiscoverLayoutValue = {
  discoverMinimal: boolean;
};

const HubDiscoverLayoutContext = createContext<HubDiscoverLayoutValue>({
  discoverMinimal: false,
});

export function HubDiscoverLayoutProvider({
  discoverMinimal,
  children,
}: HubDiscoverLayoutValue & { children: ReactNode }) {
  return (
    <HubDiscoverLayoutContext.Provider value={{ discoverMinimal }}>
      {children}
    </HubDiscoverLayoutContext.Provider>
  );
}

export function useHubDiscoverLayout(): HubDiscoverLayoutValue {
  return useContext(HubDiscoverLayoutContext);
}
