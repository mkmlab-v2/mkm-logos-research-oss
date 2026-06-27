import { normalizeHygienePrefs } from "./personadiaryHygieneHypoV1";
import type { PersonadiaryHygienePrefsHypoV1 } from "./personadiaryHygieneHypoV1";
import {
  normalizePersonadiaryConsumerConstitution,
  type PersonadiaryConsumerConstitutionV1,
} from "./personadiaryClinicConstitutionSurveyV1";
import type {
  PersonadiarySttAuditLocalRowHypoV1,
  PersonadiaryVoiceMetaHypoV1,
} from "./personadiarySttAuditHypoV1";

export const PERSONADIARY_MOBILE_OPS_SCHEMA = "personadiary_mobile_ops_v1" as const;
export const PERSONADIARY_MOBILE_OPS_VERSION = 1;
export const PERSONADIARY_MOBILE_OPS_IDB_KEY = "personadiary_mobile_ops_v1";

export type PersonadiaryLane = "body" | "mind" | "work" | "rest";

export type PersonadiaryWeeklyItem = {
  id: string;
  text: string;
  status: "pending" | "done";
  lane: PersonadiaryLane;
};

export type PersonadiaryNorthStarLaneHypo = {
  one_line: string;
  updated_at_utc: string;
};

export type PersonadiaryNorthStarByLaneHypoV1 = {
  hypothesis_tier: "B";
  boundary_ack: string;
  lanes: Record<PersonadiaryLane, PersonadiaryNorthStarLaneHypo>;
};

export type PersonadiaryLocalBirthProfileV1 = {
  schema: "local_birth_profile_v1";
  preview_only: true;
  nickname?: string;
  birth_instant_utc?: string;
  iana_tz?: string;
  self_note_ko?: string;
  onboarding_skipped?: boolean;
  updated_at_utc?: string;
};

export type { PersonadiaryConsumerConstitutionV1 };

export const NORTH_STAR_BOUNDARY_ACK =
  "research_only · user self-narrative · no surveillance · no mkmlife/Track A join";

export const PERSONADIARY_LANES: PersonadiaryLane[] = ["body", "mind", "work", "rest"];

export const NORTH_STAR_LANE_PLACEHOLDERS: Record<PersonadiaryLane, string> = {
  body: "예: 가볍고 규칙적인 몸",
  mind: "예: 소음 없이 마음 정리",
  work: "예: 한 번에 하나만 끝내기",
  rest: "예: 의도적인 쉼",
};

export type PersonadiaryMobileOpsV1 = {
  schema: typeof PERSONADIARY_MOBILE_OPS_SCHEMA;
  version: number;
  preview_only: true;
  send_gate_default: "HOLD";
  week_label?: string;
  active_lane: PersonadiaryLane;
  lanes: PersonadiaryLane[];
  weekly_top5: PersonadiaryWeeklyItem[];
  next_one_action: {
    text: string;
    lane: PersonadiaryLane;
    due_local?: string;
  };
  checkpoints: { ts_utc: string; one_line: string }[];
  diary_entries_local: {
    date_local: string;
    body: string;
    lane: PersonadiaryLane;
    synced?: boolean;
    voice_meta_hypo_v1?: PersonadiaryVoiceMetaHypoV1;
  }[];
  notification_policy: {
    push_enabled: false;
    pull_reminder_local?: string;
  };
  disclaimer_ko?: string;
  updated_at_utc?: string;
  north_star_by_lane_hypo_v1?: PersonadiaryNorthStarByLaneHypoV1;
  local_birth_profile_v1?: PersonadiaryLocalBirthProfileV1;
  mkm_consumer_constitution_v1?: PersonadiaryConsumerConstitutionV1;
  /** Stable local user id aligned with mkm_consumer_profile_v1.user_id */
  consumer_user_id?: string;
  hygiene_prefs_hypo_v1?: PersonadiaryHygienePrefsHypoV1;
  stt_audit_local_hypo_v1?: PersonadiarySttAuditLocalRowHypoV1[];
};

export const PERSONADIARY_LANE_LABELS: Record<PersonadiaryLane, string> = {
  body: "몸",
  mind: "마음",
  work: "일",
  rest: "쉼",
};

export function createEmptyNorthStarByLane(): PersonadiaryNorthStarByLaneHypoV1 {
  const now = new Date().toISOString();
  const laneEntry = (one_line: string): PersonadiaryNorthStarLaneHypo => ({
    one_line,
    updated_at_utc: now,
  });
  return {
    hypothesis_tier: "B",
    boundary_ack: NORTH_STAR_BOUNDARY_ACK,
    lanes: {
      body: laneEntry(""),
      mind: laneEntry(""),
      work: laneEntry(""),
      rest: laneEntry(""),
    },
  };
}

/** Legacy ms/oracle/infra/design → body/mind/work/rest (best-effort). */
function migrateNorthStarLanes(raw: unknown): PersonadiaryNorthStarByLaneHypoV1 | undefined {
  if (!raw || typeof raw !== "object") return undefined;
  const doc = raw as PersonadiaryNorthStarByLaneHypoV1 & {
    lanes?: Record<string, PersonadiaryNorthStarLaneHypo>;
  };
  if (doc.hypothesis_tier !== "B" || !doc.lanes) return undefined;
  const lanes = doc.lanes;
  if (lanes.body && lanes.mind && lanes.work && lanes.rest) {
    return {
      hypothesis_tier: "B",
      boundary_ack: String(doc.boundary_ack || NORTH_STAR_BOUNDARY_ACK).slice(0, 512),
      lanes: {
        body: { ...lanes.body, one_line: String(lanes.body.one_line || "").slice(0, 280) },
        mind: { ...lanes.mind, one_line: String(lanes.mind.one_line || "").slice(0, 280) },
        work: { ...lanes.work, one_line: String(lanes.work.one_line || "").slice(0, 280) },
        rest: { ...lanes.rest, one_line: String(lanes.rest.one_line || "").slice(0, 280) },
      },
    };
  }
  const legacyMap: [PersonadiaryLane, string][] = [
    ["body", "ms"],
    ["mind", "oracle"],
    ["work", "infra"],
    ["rest", "design"],
  ];
  const now = new Date().toISOString();
  const migrated = createEmptyNorthStarByLane();
  for (const [target, legacyKey] of legacyMap) {
    const src = lanes[legacyKey];
    if (src?.one_line) {
      migrated.lanes[target] = {
        one_line: String(src.one_line).slice(0, 280),
        updated_at_utc: src.updated_at_utc || now,
      };
    }
  }
  return migrated;
}

export function getNorthStarLine(
  ops: PersonadiaryMobileOpsV1,
  lane: PersonadiaryLane
): string | null {
  const line = ops.north_star_by_lane_hypo_v1?.lanes?.[lane]?.one_line?.trim();
  return line || null;
}

export function needsPersonadiaryOnboarding(ops: PersonadiaryMobileOpsV1): boolean {
  if (ops.local_birth_profile_v1?.onboarding_skipped) return false;
  const birthDone = Boolean(ops.local_birth_profile_v1?.updated_at_utc);
  const constitutionDone = Boolean(ops.mkm_consumer_constitution_v1?.onboarding_complete);
  return !birthDone || !constitutionDone;
}

export function normalizeLocalBirthProfile(
  raw: PersonadiaryLocalBirthProfileV1 | undefined
): PersonadiaryLocalBirthProfileV1 | undefined {
  if (!raw || raw.schema !== "local_birth_profile_v1") return undefined;
  return {
    schema: "local_birth_profile_v1",
    preview_only: true,
    nickname: raw.nickname ? String(raw.nickname).slice(0, 32) : undefined,
    birth_instant_utc: raw.birth_instant_utc
      ? String(raw.birth_instant_utc).slice(0, 32)
      : undefined,
    iana_tz: raw.iana_tz ? String(raw.iana_tz).slice(0, 64) : undefined,
    self_note_ko: raw.self_note_ko ? String(raw.self_note_ko).slice(0, 280) : undefined,
    onboarding_skipped: raw.onboarding_skipped === true,
    updated_at_utc: raw.updated_at_utc,
  };
}

export function isoWeekLabelLocal(d = new Date()): string {
  const date = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
  const day = date.getUTCDay() || 7;
  date.setUTCDate(date.getUTCDate() + 4 - day);
  const yearStart = new Date(Date.UTC(date.getUTCFullYear(), 0, 1));
  const week = Math.ceil(((date.getTime() - yearStart.getTime()) / 86400000 + 1) / 7);
  return `${date.getUTCFullYear()}-W${String(week).padStart(2, "0")}`;
}

export function localDateString(d = new Date()): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

export function createDefaultPersonadiaryMobileOps(): PersonadiaryMobileOpsV1 {
  const now = new Date();
  return {
    schema: PERSONADIARY_MOBILE_OPS_SCHEMA,
    version: PERSONADIARY_MOBILE_OPS_VERSION,
    preview_only: true,
    send_gate_default: "HOLD",
    week_label: isoWeekLabelLocal(now),
    active_lane: "rest",
    lanes: ["body", "mind", "work", "rest"],
    weekly_top5: [],
    next_one_action: { text: "", lane: "rest", due_local: localDateString(now) },
    checkpoints: [],
    diary_entries_local: [],
    notification_policy: { push_enabled: false, pull_reminder_local: "21:00" },
    disclaimer_ko:
      "preview_only · Pull-first 개인 기지 · 예언·적중 아님 · 일기는 이 기기(IndexedDB)만 · 서버 업로드 없음 · 진단·처방·투자 단정 없음",
    updated_at_utc: now.toISOString(),
  };
}

export function normalizePersonadiaryMobileOps(
  raw: PersonadiaryMobileOpsV1
): PersonadiaryMobileOpsV1 {
  const base = createDefaultPersonadiaryMobileOps();
  const weekly: PersonadiaryWeeklyItem[] = (raw.weekly_top5 || []).slice(0, 5).map((item, i) => ({
    id: item.id || `w${i + 1}`,
    text: String(item.text || "").slice(0, 200),
    status: item.status === "done" ? ("done" as const) : ("pending" as const),
    lane: item.lane || base.active_lane,
  }));
  return {
    ...base,
    ...raw,
    schema: PERSONADIARY_MOBILE_OPS_SCHEMA,
    version: PERSONADIARY_MOBILE_OPS_VERSION,
    preview_only: true,
    send_gate_default: "HOLD",
    lanes: ["body", "mind", "work", "rest"],
    weekly_top5: weekly,
    next_one_action: {
      text: String(raw.next_one_action?.text || "").slice(0, 200),
      lane: raw.next_one_action?.lane || raw.active_lane || "rest",
      due_local: raw.next_one_action?.due_local || localDateString(),
    },
    checkpoints: (raw.checkpoints || []).slice(-64),
    diary_entries_local: (raw.diary_entries_local || []).slice(-366).map((e) => ({
      date_local: e.date_local,
      body: String(e.body || "").slice(0, 2000),
      lane: e.lane || "mind",
      synced: false,
    })),
    notification_policy: {
      push_enabled: false,
      pull_reminder_local:
        raw.notification_policy?.pull_reminder_local ||
        raw.hygiene_prefs_hypo_v1?.pull_window_local ||
        "21:00",
    },
    updated_at_utc: new Date().toISOString(),
    ...(migrateNorthStarLanes(raw.north_star_by_lane_hypo_v1)
      ? { north_star_by_lane_hypo_v1: migrateNorthStarLanes(raw.north_star_by_lane_hypo_v1) }
      : {}),
    ...(normalizeLocalBirthProfile(raw.local_birth_profile_v1)
      ? { local_birth_profile_v1: normalizeLocalBirthProfile(raw.local_birth_profile_v1) }
      : {}),
    ...(normalizePersonadiaryConsumerConstitution(raw.mkm_consumer_constitution_v1)
      ? {
          mkm_consumer_constitution_v1: normalizePersonadiaryConsumerConstitution(
            raw.mkm_consumer_constitution_v1,
          ),
        }
      : {}),
    ...(raw.consumer_user_id
      ? { consumer_user_id: String(raw.consumer_user_id).slice(0, 64) }
      : {}),
    ...(normalizeHygienePrefs(raw.hygiene_prefs_hypo_v1)
      ? { hygiene_prefs_hypo_v1: normalizeHygienePrefs(raw.hygiene_prefs_hypo_v1) }
      : {}),
  };
}

const PERSONADIARY_APEX_HOSTS = new Set([
  "personadiary.com",
  "www.personadiary.com",
  "preview.personadiary.com",
]);

function personadiaryApexBuildFlag(): boolean {
  const v = process.env.NEXT_PUBLIC_PERSONADIARY_IS_APEX_HOST?.trim().toLowerCase();
  return v === "1" || v === "true" || v === "yes" || v === "on";
}

/** personadiary.com host uses /ops; hub preview uses /personadiary/ops */
export function personadiaryPublicPath(subpath: string): string {
  const s = subpath ? (subpath.startsWith("/") ? subpath : `/${subpath}`) : "";
  if (personadiaryApexBuildFlag()) {
    return s || "/";
  }
  if (typeof window !== "undefined") {
    const host = window.location.hostname.toLowerCase();
    if (PERSONADIARY_APEX_HOSTS.has(host)) {
      return s || "/";
    }
  }
  return `/personadiary${s}`;
}
