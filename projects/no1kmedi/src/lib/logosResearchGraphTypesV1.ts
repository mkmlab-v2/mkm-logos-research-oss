import type { LogosGraphSliceNode } from "./logosResearchHighlightV1";

export const KIND_COLOR: Record<string, string> = {
  verse: "#5eead4",
  theme: "#fcd34d",
  regime: "#93c5fd",
  stage: "#c4b5fd",
  ghost: "#a78bfa",
  other: "#94a3b8",
};

export type LogosGraphSliceEdge = {
  src: string;
  dst: string;
};

export type LogosGraphSliceDoc = {
  nodes?: LogosGraphSliceNode[];
  edges?: LogosGraphSliceEdge[];
};
