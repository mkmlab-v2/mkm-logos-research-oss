import type { ConsumerChatThread, ConsumerChatTurn, ConsumerHealthSnapshot } from "@/lib/consumer-chat-types";

const STORAGE_KEY = "jema_ai_consumer_threads_v1";
const SCHEMA_VERSION = 1;
const MAX_THREADS = 36;
const MAX_TURNS = 64;

type StoredShape = {
  v: number;
  threads: ConsumerChatThread[];
};

const DEFAULT_HEALTH: ConsumerHealthSnapshot = {
  painArea: "",
  painScale: "5",
  digestiveNote: "",
  sleepNote: "",
};

const OPENING_TURN: ConsumerChatTurn = {
  role: "assistant",
  message:
    "기본 건강 정보를 바탕으로 상담 전 안내를 도와드립니다. 응급 증상은 즉시 119/응급실을 이용해 주세요.",
};

export function defaultOpeningTurns(): ConsumerChatTurn[] {
  return [OPENING_TURN];
}

export function newThreadId(): string {
  return `th_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;
}

export function createEmptyThread(): ConsumerChatThread {
  const now = Date.now();
  return {
    id: newThreadId(),
    title: "새 대화",
    createdAt: now,
    updatedAt: now,
    turns: defaultOpeningTurns(),
    health: { ...DEFAULT_HEALTH },
  };
}

function trimTurns(turns: ConsumerChatTurn[]): ConsumerChatTurn[] {
  if (turns.length <= MAX_TURNS) return turns;
  return turns.slice(turns.length - MAX_TURNS);
}

export function normalizeThreads(raw: unknown): ConsumerChatThread[] {
  if (!raw || typeof raw !== "object") return [];
  const o = raw as StoredShape;
  if (o.v !== SCHEMA_VERSION || !Array.isArray(o.threads)) return [];
  return o.threads
    .filter((t) => t && typeof t.id === "string" && Array.isArray(t.turns))
    .map((t) => ({
      ...t,
      turns: trimTurns(t.turns),
      health: { ...DEFAULT_HEALTH, ...t.health },
    }))
    .slice(0, MAX_THREADS);
}

export function loadConsumerThreads(): ConsumerChatThread[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    return normalizeThreads(JSON.parse(raw) as unknown);
  } catch {
    return [];
  }
}

export function saveConsumerThreads(threads: ConsumerChatThread[]): void {
  if (typeof window === "undefined") return;
  try {
    const trimmed = threads.slice(0, MAX_THREADS).map((t) => ({
      ...t,
      turns: trimTurns(t.turns),
    }));
    const payload: StoredShape = { v: SCHEMA_VERSION, threads: trimmed };
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
  } catch {
    /* quota or private mode */
  }
}

export function titleFromTurns(turns: ConsumerChatTurn[]): string {
  const firstUser = turns.find((x) => x.role === "user");
  if (!firstUser?.message?.trim()) return "새 대화";
  const line = firstUser.message.trim().split(/\r?\n/)[0] || "";
  return line.length > 32 ? `${line.slice(0, 32)}…` : line || "새 대화";
}
