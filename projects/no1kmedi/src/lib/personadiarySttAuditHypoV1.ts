/**
 * PersonaDiary STT routing audit local rows v1 [HYPO].
 * Mirrors stt_routing_audit_log_v1 + build_personadiary_stt_audit_row_hypo_v1.py
 */

export const STT_AUDIT_SCHEMA_VERSION = "stt_routing_audit_log_v1" as const;
export const STT_HYPOTHESIS_TAG = "[HYPO] personadiary_voice_paste_v1";
export const STT_WEB_SPEECH_HYPOTHESIS_TAG = "[HYPO] personadiary_voice_webspeech_v1";

export type SttHypothesisTag = typeof STT_HYPOTHESIS_TAG | typeof STT_WEB_SPEECH_HYPOTHESIS_TAG;
export const STT_SESSION_STORAGE_KEY = "personadiary_stt_session_hypo_v1";

export type SttRoute = "local" | "vendor" | "rejected";

export type PersonadiarySttAuditLocalRowHypoV1 = {
  schema_version: typeof STT_AUDIT_SCHEMA_VERSION;
  event_id: string;
  occurred_at_utc: string;
  route: SttRoute;
  audio_duration_ms: number;
  pii_redaction: "redacted_full";
  hypothesis_tag: SttHypothesisTag;
  chars_out: number;
  session_id?: string;
};

export type PersonadiaryVoiceMetaHypoV1 = {
  hypothesis_tier: "B";
  stt_event_id: string;
  segments: number;
  human_gate_approved: boolean;
  mind_red_flag_tier: string;
  stt_route: SttRoute;
};

const SESSION_FALLBACK = "personadiary-web-anon";

export function getOrCreateSttSessionId(): string {
  if (typeof window === "undefined") return SESSION_FALLBACK;
  try {
    const existing = window.localStorage.getItem(STT_SESSION_STORAGE_KEY);
    if (existing?.trim()) return existing.trim();
    const created = `pd-${crypto.randomUUID()}`;
    window.localStorage.setItem(STT_SESSION_STORAGE_KEY, created);
    return created;
  } catch {
    return SESSION_FALLBACK;
  }
}

function buildLocalSttAuditRow(
  transcript: string,
  eventId: string,
  hypothesisTag: SttHypothesisTag,
  audioDurationMs: number,
  sessionId?: string
): PersonadiarySttAuditLocalRowHypoV1 {
  return {
    schema_version: STT_AUDIT_SCHEMA_VERSION,
    event_id: eventId,
    occurred_at_utc: new Date().toISOString().replace(/\.\d{3}Z$/, "Z"),
    route: "local",
    audio_duration_ms: Math.max(0, Math.round(audioDurationMs)),
    pii_redaction: "redacted_full",
    hypothesis_tag: hypothesisTag,
    chars_out: transcript.length,
    session_id: sessionId || getOrCreateSttSessionId(),
  };
}

export function buildPasteSttAuditRow(
  transcript: string,
  eventId: string,
  sessionId?: string
): PersonadiarySttAuditLocalRowHypoV1 {
  return buildLocalSttAuditRow(transcript, eventId, STT_HYPOTHESIS_TAG, 0, sessionId);
}

export function buildWebSpeechSttAuditRow(
  transcript: string,
  eventId: string,
  audioDurationMs: number,
  sessionId?: string
): PersonadiarySttAuditLocalRowHypoV1 {
  return buildLocalSttAuditRow(
    transcript,
    eventId,
    STT_WEB_SPEECH_HYPOTHESIS_TAG,
    audioDurationMs,
    sessionId
  );
}

export function appendLocalSttAuditRow(
  rows: PersonadiarySttAuditLocalRowHypoV1[] | undefined,
  row: PersonadiarySttAuditLocalRowHypoV1,
  maxRows = 128
): PersonadiarySttAuditLocalRowHypoV1[] {
  const next = [...(rows ?? []), row];
  return next.slice(-maxRows);
}

export function sttAuditRowsToJsonl(rows: PersonadiarySttAuditLocalRowHypoV1[]): string {
  return rows.map((r) => JSON.stringify(r)).join("\n") + (rows.length ? "\n" : "");
}
