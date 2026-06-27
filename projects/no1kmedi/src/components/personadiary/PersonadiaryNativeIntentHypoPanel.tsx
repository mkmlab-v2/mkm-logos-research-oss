"use client";

import { useEffect, useRef, useState } from "react";
import type { PersonadiaryMobileOpsV1 } from "@/lib/personadiaryMobileOpsV1";
import {
  drainPendingIngestQueue,
  enqueueNativeIntent,
  registerNativeIntentListener,
} from "@/lib/personadiaryNativeIntentBridgeV1";
import { loadPersonadiaryIngestQueue } from "@/lib/personadiaryOfflineIngestQueueStore";
import { APP_FUNCTION_IDS } from "@/lib/personadiaryOfflineIngestQueueV1";
import { detectPersonadiaryRuntime } from "@/lib/personadiaryNativeBridgeHypoV1";

type Props = {
  ops: PersonadiaryMobileOpsV1;
  onPersist: (next: PersonadiaryMobileOpsV1) => Promise<PersonadiaryMobileOpsV1 | void>;
};

export function PersonadiaryNativeIntentHypoPanel({ ops, onPersist }: Props) {
  const runtime = detectPersonadiaryRuntime();
  const opsRef = useRef(ops);
  opsRef.current = ops;
  const [pendingCount, setPendingCount] = useState(0);
  const [lastApplied, setLastApplied] = useState(0);
  const [lastError, setLastError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function refreshCount() {
      const q = await loadPersonadiaryIngestQueue();
      if (!cancelled) {
        setPendingCount(q.items.filter((i) => i.status === "pending").length);
      }
    }
    void refreshCount();
    return () => {
      cancelled = true;
    };
  }, [ops.updated_at_utc, lastApplied]);

  useEffect(() => {
    const unregister = registerNativeIntentListener((detail) => {
      void (async () => {
        const source =
          detail.source ??
          (detail.kind === "share_text" ? "share_extension" : "deep_link");
        await enqueueNativeIntent(detail, source);
        const drained = await drainPendingIngestQueue(opsRef.current);
        if (drained.applied > 0) {
          await onPersist(drained.ops);
          setLastApplied(drained.applied);
          setLastError(null);
        }
        setPendingCount(drained.queue.items.filter((i) => i.status === "pending").length);
      })().catch(() => setLastError("intent_enqueue_failed"));
    });
    return unregister;
  }, [onPersist]);

  useEffect(() => {
    void (async () => {
      const drained = await drainPendingIngestQueue(ops);
      if (drained.applied > 0) {
        await onPersist(drained.ops);
        setLastApplied(drained.applied);
      }
      setPendingCount(drained.queue.items.filter((i) => i.status === "pending").length);
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- drain once on mount
  }, []);

  return (
    <section
      className="pd-ops-block pd-ops-native-intent-hypo"
      aria-labelledby="pd-native-intent-title"
      data-testid="pd-ops-native-intent-hypo"
      data-pd-intent-pending={pendingCount}
      data-pd-intent-last-applied={lastApplied}
    >
      <div className="pd-premium-section-inner pd-ios-group">
        <h3 id="pd-native-intent-title" className="pd-ios-group-title">
          Intent 미들웨어 <span className="pd-ops-hypo-tag">[HYPO]</span>
        </h3>
        <p className="pd-ios-group-hint">
          AppFunctions: {APP_FUNCTION_IDS.join(" · ")} · Pull-first 큐 · OS 제어 없음 · mkmlife 결제 합선 금지
        </p>
        <ul className="pd-ops-native-intent-meta">
          <li>runtime: {runtime}</li>
          <li>pending queue: {pendingCount}</li>
          {lastApplied > 0 ? <li>last applied: {lastApplied}</li> : null}
        </ul>
        {lastError ? <p className="pd-ops-error">{lastError}</p> : null}
      </div>
    </section>
  );
}
