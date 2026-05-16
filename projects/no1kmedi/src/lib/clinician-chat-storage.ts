import type { ClinicianChatThread, ClinicianChatTurn, ClinicianThreadContext } from "@/lib/clinician-chat-types";

const STORAGE_KEY = "jema_ai_clinician_threads_v1";
const SCHEMA_VERSION = 1;
const MAX_THREADS = 24;
const MAX_TURNS = 48;

type StoredShape = {
  v: number;
  threads: ClinicianChatThread[];
};

export function defaultClinicianContext(): ClinicianThreadContext {
  return {
    actorId: "hanui-demo-001",
    birthInstantUtc: "1990-01-01T00:00:00Z",
    ianaTz: "Asia/Seoul",
    chiefComplaint: "",
    onset: "",
    severity: "",
    medication: "",
    digestionPattern: "",
    sleepPattern: "",
    bodyHeatPreference: "",
    stressReactivity: "",
    constitutionFreeText: "",
    painScale0to10: "",
    redFlagNotes: "",
    healthAppetite: "",
    healthBowelPattern: "",
    loadedSurveyContext: null,
    lensMode: "neutral",
    includeScripture: false,
  };
}

const OPENING_TURN: ClinicianChatTurn = {
  role: "assistant",
  message:
    "한의 진료 보조 대화입니다. 주증상을 입력하면 CDSS 초안·근거 요약을 돌려드립니다. 최종 진단·처방은 한의사가 확정합니다. 출생·문진은 왼쪽 메뉴 「환자·설정」에서 맞춰 주세요.",
};

export function defaultOpeningTurns(): ClinicianChatTurn[] {
  return [OPENING_TURN];
}

export function newClinicianThreadId(): string {
  return `cl_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;
}

export function createEmptyClinicianThread(): ClinicianChatThread {
  const now = Date.now();
  return {
    id: newClinicianThreadId(),
    title: "새 상담",
    createdAt: now,
    updatedAt: now,
    turns: defaultOpeningTurns(),
    context: defaultClinicianContext(),
  };
}

function trimTurns(turns: ClinicianChatTurn[]): ClinicianChatTurn[] {
  if (turns.length <= MAX_TURNS) return turns;
  return turns.slice(turns.length - MAX_TURNS);
}

export function normalizeClinicianThreads(raw: unknown): ClinicianChatThread[] {
  if (!raw || typeof raw !== "object") return [];
  const o = raw as StoredShape;
  if (o.v !== SCHEMA_VERSION || !Array.isArray(o.threads)) return [];
  return o.threads
    .filter((t) => t && typeof t.id === "string" && Array.isArray(t.turns))
    .map((t) => ({
      ...t,
      turns: trimTurns(t.turns),
      context: { ...defaultClinicianContext(), ...t.context },
    }))
    .slice(0, MAX_THREADS);
}

export function loadClinicianThreads(): ClinicianChatThread[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    return normalizeClinicianThreads(JSON.parse(raw) as unknown);
  } catch {
    return [];
  }
}

export function saveClinicianThreads(threads: ClinicianChatThread[]): void {
  if (typeof window === "undefined") return;
  try {
    const trimmed = threads.slice(0, MAX_THREADS).map((t) => ({
      ...t,
      turns: trimTurns(t.turns),
    }));
    const payload: StoredShape = { v: SCHEMA_VERSION, threads: trimmed };
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
  } catch {
    /* quota */
  }
}

export function titleFromClinicianTurns(turns: ClinicianChatTurn[]): string {
  const firstUser = turns.find((x) => x.role === "user");
  if (!firstUser?.message?.trim()) return "새 상담";
  const line = firstUser.message.trim().split(/\r?\n/)[0] || "";
  return line.length > 28 ? `${line.slice(0, 28)}…` : line || "새 상담";
}
