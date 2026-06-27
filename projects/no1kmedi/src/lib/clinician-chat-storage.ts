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
    enoMultimodalIntake: null,
    lensMode: "neutral",
    includeScripture: false,
  };
}

const OPENING_TURN: ClinicianChatTurn = {
  role: "assistant",
  message:
    "한의 진료 보조 대화입니다. Paste Chart 탭에서 차트를 통째 붙여넣으면 SOAP·조언 초안을 돌려드립니다. 최종 진단·처방은 한의사가 확정합니다.",
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
    patientLabel: "",
    sessionDate: toSessionDateInput(now),
    titlePinned: false,
    createdAt: now,
    updatedAt: now,
    turns: [],
    context: defaultClinicianContext(),
  };
}

export function toSessionDateInput(ms: number): string {
  const d = new Date(ms);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

export function threadDisplayPrimary(t: ClinicianChatThread): string {
  const patient = t.patientLabel?.trim();
  if (patient) return patient;
  const title = t.title?.trim();
  if (title) return title;
  return "새 상담";
}

export function threadDisplaySecondary(t: ClinicianChatThread): string {
  if (t.sessionDate?.trim()) {
    try {
      return new Date(`${t.sessionDate.trim()}T12:00:00`).toLocaleDateString("ko-KR", {
        year: "numeric",
        month: "short",
        day: "numeric",
        weekday: "short",
      });
    } catch {
      /* fall through */
    }
  }
  return new Date(t.updatedAt).toLocaleString("ko-KR", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
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
      patientLabel: typeof t.patientLabel === "string" ? t.patientLabel : "",
      sessionDate:
        typeof t.sessionDate === "string" && t.sessionDate.trim()
          ? t.sessionDate.trim()
          : toSessionDateInput(t.updatedAt || Date.now()),
      titlePinned: Boolean(t.titlePinned),
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

export const CLINICIAN_THREADS_BACKUP_SCHEMA = "clinician_threads_backup_v1";

export type ClinicianThreadsBackupV1 = {
  schema: typeof CLINICIAN_THREADS_BACKUP_SCHEMA;
  exported_at_utc: string;
  v: number;
  threads: ClinicianChatThread[];
};

export function buildClinicianThreadsBackup(threads: ClinicianChatThread[]): ClinicianThreadsBackupV1 {
  return {
    schema: CLINICIAN_THREADS_BACKUP_SCHEMA,
    exported_at_utc: new Date().toISOString(),
    v: SCHEMA_VERSION,
    threads: threads.slice(0, MAX_THREADS).map((t) => ({
      ...t,
      turns: trimTurns(t.turns),
    })),
  };
}

export function parseClinicianThreadsBackup(
  raw: string,
): { ok: true; threads: ClinicianChatThread[] } | { ok: false; error: string } {
  try {
    const parsed = JSON.parse(raw) as ClinicianThreadsBackupV1 | StoredShape;
    if (
      parsed &&
      typeof parsed === "object" &&
      (parsed as ClinicianThreadsBackupV1).schema === CLINICIAN_THREADS_BACKUP_SCHEMA &&
      Array.isArray((parsed as ClinicianThreadsBackupV1).threads)
    ) {
      return {
        ok: true,
        threads: normalizeClinicianThreads({ v: SCHEMA_VERSION, threads: (parsed as ClinicianThreadsBackupV1).threads }),
      };
    }
    if (parsed && typeof parsed === "object" && (parsed as StoredShape).v === SCHEMA_VERSION) {
      return { ok: true, threads: normalizeClinicianThreads(parsed) };
    }
    return { ok: false, error: "unsupported_backup_schema" };
  } catch {
    return { ok: false, error: "invalid_json" };
  }
}

export function mergeImportedClinicianThreads(
  current: ClinicianChatThread[],
  imported: ClinicianChatThread[],
): ClinicianChatThread[] {
  const byId = new Map<string, ClinicianChatThread>();
  for (const t of imported) byId.set(t.id, t);
  for (const t of current) byId.set(t.id, t);
  return [...byId.values()]
    .sort((a, b) => b.updatedAt - a.updatedAt)
    .slice(0, MAX_THREADS);
}

export function downloadClinicianThreadsBackup(threads: ClinicianChatThread[]): void {
  if (typeof window === "undefined") return;
  const payload = buildClinicianThreadsBackup(threads);
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const stamp = new Date().toISOString().slice(0, 10);
  const a = document.createElement("a");
  a.href = url;
  a.download = `jema-clinician-threads-${stamp}.json`;
  a.click();
  URL.revokeObjectURL(url);
}

export function titleFromClinicianTurns(turns: ClinicianChatTurn[]): string {
  const firstUser = turns.find((x) => x.role === "user");
  if (!firstUser?.message?.trim()) return "새 상담";
  const line = firstUser.message.trim().split(/\r?\n/)[0] || "";
  return line.length > 28 ? `${line.slice(0, 28)}…` : line || "새 상담";
}
