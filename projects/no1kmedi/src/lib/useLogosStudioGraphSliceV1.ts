"use client";

import { useEffect, useState } from "react";

import type { LensContextMeshHopIndexDoc } from "@/lib/lensContextMeshBfsV1";
import type { LogosGraphSliceDoc } from "@/lib/logosResearchGraphTypesV1";

export const LOGOS_GRAPH_SLICE_URL = "/data/logos_studio/graph_slice_v1.json";
export const LOGOS_HOP_INDEX_URL = "/data/logos_studio/context_mesh_hop_index_v1.json";
/** Bump when graph_slice / hop_index artifacts change (stub patch · router sidecar). */
export const LOGOS_STUDIO_GRAPH_DATA_V = "2026-06-26-embed-stub-v1";
/** Max wait for graph_slice / hop_index fetch before surfacing error (ms). */
export const LOGOS_STUDIO_GRAPH_FETCH_TIMEOUT_MS = 30_000;

function fetchWithTimeout(url: string, timeoutMs: number): Promise<Response> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);
  return fetch(url, { cache: "no-store", signal: controller.signal }).finally(() => {
    window.clearTimeout(timer);
  });
}

export function useLogosStudioGraphSlice(enabled = true) {
  const [graphDoc, setGraphDoc] = useState<LogosGraphSliceDoc | null>(null);
  const [hopIndex, setHopIndex] = useState<LensContextMeshHopIndexDoc | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;
    (async () => {
      try {
        const cacheBust = `?v=${LOGOS_STUDIO_GRAPH_DATA_V}`;
        const timeoutMs = LOGOS_STUDIO_GRAPH_FETCH_TIMEOUT_MS;
        const [sliceRes, hopRes] = await Promise.all([
          fetchWithTimeout(`${LOGOS_GRAPH_SLICE_URL}${cacheBust}`, timeoutMs),
          fetchWithTimeout(`${LOGOS_HOP_INDEX_URL}${cacheBust}`, timeoutMs),
        ]);
        if (!sliceRes.ok) throw new Error(`graph_slice_http_${sliceRes.status}`);
        const data = (await sliceRes.json()) as LogosGraphSliceDoc;
        if (!cancelled) {
          setGraphDoc(data);
          setLoadError(null);
        }
        if (hopRes.ok && !cancelled) {
          setHopIndex((await hopRes.json()) as LensContextMeshHopIndexDoc);
        }
      } catch (e: unknown) {
        if (!cancelled) {
          if (e instanceof DOMException && e.name === "AbortError") {
            setLoadError("graph_slice_timeout_30s");
          } else {
            setLoadError(e instanceof Error ? e.message : "graph_slice_failed");
          }
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [enabled]);

  return { graphDoc, hopIndex, loadError };
}
