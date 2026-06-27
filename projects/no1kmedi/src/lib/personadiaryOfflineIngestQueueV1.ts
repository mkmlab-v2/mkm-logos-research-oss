export const PERSONADIARY_OFFLINE_INGEST_QUEUE_SCHEMA =
  "personadiary_offline_ingest_queue_v1" as const;
export const PERSONADIARY_OFFLINE_INGEST_QUEUE_VERSION = 1;
export const PERSONADIARY_OFFLINE_INGEST_QUEUE_IDB_KEY =
  "personadiary_offline_ingest_queue_v1";

export type PersonadiaryIngestKind =
  | "save_moment_note"
  | "add_reminder"
  | "share_text";

export type PersonadiaryIngestSource =
  | "app_function"
  | "share_extension"
  | "deep_link"
  | "manual_replay";

export type PersonadiaryIngestLane = "body" | "mind" | "work" | "rest";

export type PersonadiaryIngestPayloadV1 = {
  text: string;
  lane?: PersonadiaryIngestLane;
  due_local?: string;
};

export type PersonadiaryIngestQueueItemV1 = {
  id: string;
  kind: PersonadiaryIngestKind;
  payload: PersonadiaryIngestPayloadV1;
  status: "pending" | "applied" | "failed";
  scrubbed: boolean;
  source: PersonadiaryIngestSource;
  error_code?: string;
  created_at_utc: string;
  applied_at_utc?: string;
};

export type PersonadiaryOfflineIngestQueueV1 = {
  schema: typeof PERSONADIARY_OFFLINE_INGEST_QUEUE_SCHEMA;
  version: number;
  preview_only: true;
  send_gate_default: "HOLD";
  items: PersonadiaryIngestQueueItemV1[];
  updated_at_utc?: string;
};

export const APP_FUNCTION_IDS = ["save_moment_note", "add_reminder"] as const;

export function createEmptyIngestQueue(): PersonadiaryOfflineIngestQueueV1 {
  return {
    schema: PERSONADIARY_OFFLINE_INGEST_QUEUE_SCHEMA,
    version: PERSONADIARY_OFFLINE_INGEST_QUEUE_VERSION,
    preview_only: true,
    send_gate_default: "HOLD",
    items: [],
    updated_at_utc: new Date().toISOString(),
  };
}

function coerceLane(raw: unknown): PersonadiaryIngestLane | undefined {
  if (raw === "body" || raw === "mind" || raw === "work" || raw === "rest") return raw;
  return undefined;
}

function coerceKind(raw: unknown): PersonadiaryIngestKind | null {
  if (raw === "save_moment_note" || raw === "add_reminder" || raw === "share_text") return raw;
  if (raw === "share_text" || raw === "share") return "share_text";
  return null;
}

export function normalizeIngestQueue(
  raw: PersonadiaryOfflineIngestQueueV1
): PersonadiaryOfflineIngestQueueV1 {
  const items: PersonadiaryIngestQueueItemV1[] = [];
  for (const item of raw.items ?? []) {
    const kind = coerceKind(item.kind);
    if (!kind || !item.id || !item.payload?.text) continue;
    items.push({
      id: String(item.id).slice(0, 64),
      kind,
      payload: {
        text: String(item.payload.text).slice(0, 2000),
        lane: coerceLane(item.payload.lane),
        due_local: item.payload.due_local?.slice(0, 10),
      },
      status: item.status === "applied" || item.status === "failed" ? item.status : "pending",
      scrubbed: Boolean(item.scrubbed),
      source:
        item.source === "app_function" ||
        item.source === "share_extension" ||
        item.source === "deep_link" ||
        item.source === "manual_replay"
          ? item.source
          : "manual_replay",
      error_code: item.error_code?.slice(0, 64),
      created_at_utc: item.created_at_utc || new Date().toISOString(),
      applied_at_utc: item.applied_at_utc,
    });
    if (items.length >= 128) break;
  }
  return {
    schema: PERSONADIARY_OFFLINE_INGEST_QUEUE_SCHEMA,
    version: PERSONADIARY_OFFLINE_INGEST_QUEUE_VERSION,
    preview_only: true,
    send_gate_default: "HOLD",
    items,
    updated_at_utc: new Date().toISOString(),
  };
}

export function newIngestItemId(): string {
  return `q_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;
}
