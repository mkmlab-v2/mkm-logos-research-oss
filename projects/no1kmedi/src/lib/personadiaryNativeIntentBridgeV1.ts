import { localDateString, type PersonadiaryLane, type PersonadiaryMobileOpsV1 } from "./personadiaryMobileOpsV1";
import {
  newIngestItemId,
  type PersonadiaryIngestKind,
  type PersonadiaryIngestQueueItemV1,
  type PersonadiaryIngestSource,
  type PersonadiaryOfflineIngestQueueV1,
} from "./personadiaryOfflineIngestQueueV1";
import { loadPersonadiaryIngestQueue, savePersonadiaryIngestQueue } from "./personadiaryOfflineIngestQueueStore";
import { scrubShareTextHypoV1 } from "./personadiaryShareScrubHypoV1";

export type NativeIntentDetailV1 = {
  kind?: string;
  text?: string;
  lane?: PersonadiaryLane;
  due_local?: string;
  source?: PersonadiaryIngestSource;
};

export const NATIVE_INTENT_EVENT = "personadiary-native-intent";
export const PD_INTENT_E2E_LOG_PREFIX = "[pd-intent-e2e-v1]";

function mapKind(raw: string | undefined): PersonadiaryIngestKind | null {
  if (raw === "save_moment_note" || raw === "add_reminder" || raw === "share_text") return raw;
  if (raw === "share") return "share_text";
  return null;
}

export function buildIngestItemFromIntent(
  detail: NativeIntentDetailV1,
  source: PersonadiaryIngestSource
): PersonadiaryIngestQueueItemV1 | null {
  const kind = mapKind(detail.kind);
  const rawText = (detail.text ?? "").trim();
  if (!kind || !rawText) return null;
  const { text, scrubbed } = scrubShareTextHypoV1(rawText);
  if (!text) return null;
  return {
    id: newIngestItemId(),
    kind,
    payload: {
      text,
      lane: detail.lane,
      due_local: detail.due_local?.slice(0, 10),
    },
    status: "pending",
    scrubbed,
    source,
    created_at_utc: new Date().toISOString(),
  };
}

export async function enqueueNativeIntent(
  detail: NativeIntentDetailV1,
  source: PersonadiaryIngestSource = "deep_link"
): Promise<PersonadiaryOfflineIngestQueueV1> {
  const item = buildIngestItemFromIntent(detail, source);
  if (!item) return loadPersonadiaryIngestQueue();
  const queue = await loadPersonadiaryIngestQueue();
  return savePersonadiaryIngestQueue({
    ...queue,
    items: [...queue.items, item],
  });
}

export function applyIngestItemToOps(
  ops: PersonadiaryMobileOpsV1,
  item: PersonadiaryIngestQueueItemV1
): PersonadiaryMobileOpsV1 {
  const now = new Date().toISOString();
  const lane = item.payload.lane ?? ops.active_lane;
  const oneLine = item.payload.text.slice(0, 280);
  const date_local = item.payload.due_local || localDateString();

  if (item.kind === "add_reminder") {
    return {
      ...ops,
      next_one_action: {
        text: item.payload.text.slice(0, 200),
        lane,
        due_local: date_local,
      },
      checkpoints: [{ ts_utc: now, one_line: `리마인더: ${oneLine}` }, ...ops.checkpoints].slice(0, 64),
      updated_at_utc: now,
    };
  }

  const diary_entries_local = [
    {
      date_local,
      body: item.payload.text,
      lane,
      synced: false,
    },
    ...ops.diary_entries_local,
  ].slice(0, 366);

  return {
    ...ops,
    diary_entries_local,
    checkpoints: [{ ts_utc: now, one_line: `찰나: ${oneLine}` }, ...ops.checkpoints].slice(0, 64),
    updated_at_utc: now,
  };
}

export type DrainIngestResult = {
  queue: PersonadiaryOfflineIngestQueueV1;
  ops: PersonadiaryMobileOpsV1;
  applied: number;
};

export async function drainPendingIngestQueue(
  ops: PersonadiaryMobileOpsV1
): Promise<DrainIngestResult> {
  const queue = await loadPersonadiaryIngestQueue();
  let nextOps = ops;
  let applied = 0;
  const items = queue.items.map((item) => {
    if (item.status !== "pending") return item;
    try {
      nextOps = applyIngestItemToOps(nextOps, item);
      applied += 1;
      return {
        ...item,
        status: "applied" as const,
        applied_at_utc: new Date().toISOString(),
      };
    } catch {
      return { ...item, status: "failed" as const, error_code: "apply_failed" };
    }
  });
  const saved = await savePersonadiaryIngestQueue({ ...queue, items });
  if (applied > 0 && typeof console !== "undefined") {
    console.info(`${PD_INTENT_E2E_LOG_PREFIX} applied`, { applied });
  }
  return { queue: saved, ops: nextOps, applied };
}

export function registerNativeIntentListener(
  onIntent: (detail: NativeIntentDetailV1) => void
): () => void {
  if (typeof window === "undefined") return () => {};
  const handler = (ev: Event) => {
    const detail = (ev as CustomEvent<NativeIntentDetailV1>).detail;
    if (!detail) return;
    if (typeof console !== "undefined") {
      console.info(`${PD_INTENT_E2E_LOG_PREFIX} received`, { kind: detail.kind });
    }
    onIntent(detail);
  };
  window.addEventListener(NATIVE_INTENT_EVENT, handler);
  return () => window.removeEventListener(NATIVE_INTENT_EVENT, handler);
}
