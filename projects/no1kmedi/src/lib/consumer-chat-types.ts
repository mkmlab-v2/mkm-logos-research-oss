export type ConsumerChatRole = "user" | "assistant";

export type ConsumerChatTurn = {
  role: ConsumerChatRole;
  message: string;
};

/** 빠른 문진 스냅샷 — 스레드마다 저장되어 맥락에 포함 */
export type ConsumerHealthSnapshot = {
  painArea: string;
  painScale: string;
  digestiveNote: string;
  sleepNote: string;
};

export type ConsumerChatThread = {
  id: string;
  title: string;
  createdAt: number;
  updatedAt: number;
  turns: ConsumerChatTurn[];
  health: ConsumerHealthSnapshot;
};
