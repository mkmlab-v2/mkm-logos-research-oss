import type { PersonadiaryMobileOpsV1 } from "./personadiaryMobileOpsV1";

export const PERSONADIARY_BTRACK_EXPORT_SCHEMA = "personadiary_btrack_export_v1" as const;

export const PERSONADIARY_BTRACK_EXPORT_HUMAN_GATE_TEXT_KO =
  "연구용 비식별 패키지입니다. 자동 업로드 없음. Track A·mkmlife·실매매 합선 없음.";

export const PERSONADIARY_BTRACK_INBOX_PATH =
  "reports/constitution/btrack_pilot/personadiary_export_inbox/";

const EMAIL_RE = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g;
const PHONE_RE = /\b\d{2,4}[-.\s]?\d{3,4}[-.\s]?\d{4}\b/g;

export type PersonadiaryBtrackExportV1 = {
  schema: typeof PERSONADIARY_BTRACK_EXPORT_SCHEMA;
  generated_at_utc: string;
  hypothesis_tier: "B";
  research_only: true;
  send_gate: "HOLD";
  auto_upload: false;
  human_gate_ack: {
    acknowledged: true;
    ack_text_ko: string;
    ack_at_utc: string;
  };
  redaction: {
    pii_redact_applied: boolean;
    fields_removed: string[];
    diary_mode: "lane_stats_only" | "text_redacted" | "full_text";
  };
  pseudonym_id: string;
  source: {
    mobile_ops_schema: "personadiary_mobile_ops_v1";
    mobile_ops_version: number;
    week_label: string;
  };
  payload: Record<string, unknown>;
  inbox_pointer: {
    manual_drop_only: true;
    repo_relative_path: string;
    pack0_b_lora_hint: string;
  };
  boundary_ack: string;
};

function stripObviousPii(text: string): string {
  return text.replace(EMAIL_RE, "[redacted-email]").replace(PHONE_RE, "[redacted-phone]");
}

async function sha256Prefix(input: string): Promise<string> {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(input));
  const hex = Array.from(new Uint8Array(buf))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
  return `pdexp_${hex.slice(0, 16)}`;
}

export async function buildPersonadiaryBtrackExport(
  ops: PersonadiaryMobileOpsV1,
  options: {
    piiRedact: boolean;
    humanGateAck: boolean;
    salt?: string;
  }
): Promise<PersonadiaryBtrackExportV1> {
  if (!options.humanGateAck) {
    throw new Error("human_gate_ack required for btrack export");
  }

  const generated_at_utc = new Date().toISOString();
  const week_label = ops.week_label || "unknown";
  const fields_removed: string[] = [];
  let diary_mode: PersonadiaryBtrackExportV1["redaction"]["diary_mode"] = "full_text";

  const weekly_top5 = ops.weekly_top5.map((item) => ({
    ...item,
    text: (options.piiRedact ? stripObviousPii(item.text) : item.text).slice(0, 200),
  }));

  const next_one_action = {
    text: (
      options.piiRedact ? stripObviousPii(ops.next_one_action.text) : ops.next_one_action.text
    ).slice(0, 200),
    lane: ops.next_one_action.lane,
    ...(ops.next_one_action.due_local ? { due_local: ops.next_one_action.due_local } : {}),
  };

  const payload: Record<string, unknown> = {
    active_lane: ops.active_lane,
    weekly_top5,
    next_one_action,
  };

  if (ops.north_star_by_lane_hypo_v1) {
    payload.north_star_by_lane_hypo_v1 = ops.north_star_by_lane_hypo_v1;
  }

  if (options.piiRedact) {
    fields_removed.push(
      "local_birth_profile_v1",
      "local_birth_profile_v1.nickname",
      "local_birth_profile_v1.birth_instant_utc"
    );
    diary_mode = "lane_stats_only";
    const stats = { body: 0, mind: 0, work: 0, rest: 0, total_entries: 0 };
    for (const entry of ops.diary_entries_local) {
      if (entry.lane === "body") stats.body += 1;
      else if (entry.lane === "mind") stats.mind += 1;
      else if (entry.lane === "work") stats.work += 1;
      else if (entry.lane === "rest") stats.rest += 1;
      stats.total_entries += 1;
    }
    payload.diary_lane_stats = stats;
    payload.checkpoint_count = ops.checkpoints.length;
  } else {
    diary_mode = "text_redacted";
    payload.diary_entries_redacted = ops.diary_entries_local.map((entry) => ({
      date_local: entry.date_local,
      body: stripObviousPii(entry.body).slice(0, 2000),
      lane: entry.lane,
    }));
    payload.checkpoint_count = ops.checkpoints.length;
  }

  const pseudonym_id = await sha256Prefix(
    `${week_label}|${generated_at_utc}|${options.salt || "browser"}`
  );

  return {
    schema: PERSONADIARY_BTRACK_EXPORT_SCHEMA,
    generated_at_utc,
    hypothesis_tier: "B",
    research_only: true,
    send_gate: "HOLD",
    auto_upload: false,
    human_gate_ack: {
      acknowledged: true,
      ack_text_ko: PERSONADIARY_BTRACK_EXPORT_HUMAN_GATE_TEXT_KO,
      ack_at_utc: generated_at_utc,
    },
    redaction: {
      pii_redact_applied: options.piiRedact,
      fields_removed,
      diary_mode,
    },
    pseudonym_id,
    source: {
      mobile_ops_schema: "personadiary_mobile_ops_v1",
      mobile_ops_version: ops.version,
      week_label: week_label.slice(0, 16),
    },
    payload,
    inbox_pointer: {
      manual_drop_only: true,
      repo_relative_path: PERSONADIARY_BTRACK_INBOX_PATH,
      pack0_b_lora_hint:
        "research_only · Pack0-B LoRA sandbox · prep_myeongri_deterministic_lora_golden_v1.py · no Track A merge",
    },
    boundary_ack:
      "research_only · manual inbox drop · no server upload · no Track A or mkmlife auto merge",
  };
}

export function exportPersonadiaryBtrackExportJson(doc: PersonadiaryBtrackExportV1): string {
  return JSON.stringify(doc, null, 2);
}

export async function downloadPersonadiaryBtrackExport(
  ops: PersonadiaryMobileOpsV1,
  options: { piiRedact: boolean; humanGateAck: boolean }
): Promise<void> {
  const doc = await buildPersonadiaryBtrackExport(ops, options);
  const blob = new Blob([exportPersonadiaryBtrackExportJson(doc)], {
    type: "application/json;charset=utf-8",
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `personadiary_btrack_export_${doc.pseudonym_id}.json`;
  a.click();
  URL.revokeObjectURL(url);
}
