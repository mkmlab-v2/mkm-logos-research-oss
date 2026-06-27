"use client";

import { useCallback, useEffect, useState } from "react";
import type { PersonadiaryLane, PersonadiaryMobileOpsV1 } from "@/lib/personadiaryMobileOpsV1";
import { createDefaultPersonadiaryMobileOps } from "@/lib/personadiaryMobileOpsV1";
import {
  loadPersonadiaryMobileOps,
  savePersonadiaryMobileOps,
  type PersonadiaryMobileOpsLoadSource,
} from "@/lib/personadiaryMobileOpsStore";

export function usePersonadiaryMobileOps() {
  const [ops, setOps] = useState<PersonadiaryMobileOpsV1 | null>(null);
  const [ready, setReady] = useState(false);
  const [saving, setSaving] = useState(false);
  const [loadSource, setLoadSource] = useState<PersonadiaryMobileOpsLoadSource | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const { doc, source } = await loadPersonadiaryMobileOps();
        if (!cancelled) {
          setOps(doc);
          setLoadSource(source);
          setReady(true);
        }
      } catch {
        if (!cancelled) {
          setOps(createDefaultPersonadiaryMobileOps());
          setLoadSource("default_fallback");
          setReady(true);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const persist = useCallback(async (next: PersonadiaryMobileOpsV1) => {
    setSaving(true);
    try {
      const saved = await savePersonadiaryMobileOps(next);
      setOps(saved);
      return saved;
    } finally {
      setSaving(false);
    }
  }, []);

  const patch = useCallback(
    async (partial: Partial<PersonadiaryMobileOpsV1>) => {
      if (!ops) return;
      await persist({ ...ops, ...partial });
    },
    [ops, persist]
  );

  const setActiveLane = useCallback(
    async (lane: PersonadiaryLane) => {
      await patch({ active_lane: lane });
    },
    [patch]
  );

  return { ops, ready, saving, loadSource, persist, patch, setActiveLane };
}
