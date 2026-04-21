"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import type { ConsumerChatThread, ConsumerChatTurn, ConsumerHealthSnapshot } from "@/lib/consumer-chat-types";
import { streamTextClient } from "@/lib/consumer-chat-stream";
import { titleFromTurns } from "@/lib/consumer-chat-storage";

type ChatResponse = {
  success: boolean;
  response?: string;
  error?: string;
};

type ConsumerPersistedChatProps = {
  thread: ConsumerChatThread;
  onCommit: (patch: Partial<ConsumerChatThread> & { id: string }) => void;
};

export function ConsumerPersistedChat({ thread, onCommit }: ConsumerPersistedChatProps) {
  const [turns, setTurns] = useState<ConsumerChatTurn[]>(thread.turns);
  const [health, setHealth] = useState<ConsumerHealthSnapshot>(thread.health);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  /** null = 스트리밍 없음, 문자열 = 타이핑 중(또는 완료 직전) 표시 */
  const [streamBuf, setStreamBuf] = useState<string | null>(null);
  const requestGen = useRef(0);

  useEffect(() => {
    setTurns(thread.turns);
    setHealth(thread.health);
    setStreamBuf(null);
    setError("");
    setMessage("");
    // 스레드 전환 시에만 초기화(동일 스레드의 commit 반영은 로컬 state가 선행)
  }, [thread.id]); // eslint-disable-line react-hooks/exhaustive-deps

  const canAsk = useMemo(() => message.trim().length > 1 && !busy, [message, busy]);

  const persistPatch = useCallback(
    (patch: Partial<ConsumerChatThread> & { id: string }) => {
      onCommit(patch);
    },
    [onCommit],
  );

  const askAssistant = useCallback(async () => {
    if (!canAsk) return;
    const gen = ++requestGen.current;
    const userMessage = message.trim();
    const healthPayload = {
      pain_area: health.painArea.trim() || "미입력",
      pain_scale_0_10: Number(health.painScale) || 0,
      digestion_pattern: health.digestiveNote.trim() || "미입력",
      sleep_pattern: health.sleepNote.trim() || "미입력",
      vector_4d: { S: 0.25, L: 0.25, K: 0.25, M: 0.25 },
    };

    const turnsWithUser: ConsumerChatTurn[] = [...turns, { role: "user", message: userMessage }];
    setMessage("");
    setBusy(true);
    setError("");
    setStreamBuf(null);
    setTurns(turnsWithUser);
    persistPatch({
      id: thread.id,
      turns: turnsWithUser,
      health,
      title: titleFromTurns(turnsWithUser),
    });

    try {
      const res = await fetch("/api/guardian/ai-guardian/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: userMessage,
          health_data: { survey: healthPayload },
          chat_history: turnsWithUser.slice(-14),
        }),
      });
      const json = (await res.json()) as ChatResponse;
      if (gen !== requestGen.current) return;
      if (!res.ok || !json.success || !json.response) {
        throw new Error(json.error || "chat_request_failed");
      }
      const full = json.response.trim();
      await streamTextClient(full, (partial) => {
        if (gen !== requestGen.current) return;
        setStreamBuf(partial);
      });
      if (gen !== requestGen.current) return;
      const turnsFinal: ConsumerChatTurn[] = [...turnsWithUser, { role: "assistant", message: full }];
      setTurns(turnsFinal);
      setStreamBuf(null);
      persistPatch({
        id: thread.id,
        turns: turnsFinal,
        health,
        title: titleFromTurns(turnsFinal),
      });
    } catch {
      if (gen !== requestGen.current) return;
      setError("AI 응답이 지연되고 있습니다. 사전문진·연결 단계로 진행해 주세요.");
    } finally {
      if (gen === requestGen.current) {
        setBusy(false);
        setStreamBuf(null);
      }
    }
  }, [canAsk, health, message, persistPatch, thread.id, turns]);

  return (
    <section id="basic-health-chat" aria-labelledby="basic-health-chat-title" className="workspace-chat-root">
      <h2 id="basic-health-chat-title" className="sr-only">
        AI 기본 건강상담 (사전 안내)
      </h2>

      <div className="chat-card chat-card--workspace">
        <div className="chat-profile-grid">
          <label>
            주요 불편 부위
            <input
              value={health.painArea}
              onChange={(e) => setHealth((h) => ({ ...h, painArea: e.target.value }))}
              placeholder="예: 목, 허리, 소화"
            />
          </label>
          <label>
            통증 강도 (0-10)
            <input
              value={health.painScale}
              onChange={(e) => setHealth((h) => ({ ...h, painScale: e.target.value }))}
              type="number"
              min={0}
              max={10}
            />
          </label>
          <label>
            소화 상태
            <input
              value={health.digestiveNote}
              onChange={(e) => setHealth((h) => ({ ...h, digestiveNote: e.target.value }))}
              placeholder="예: 더부룩함"
            />
          </label>
          <label>
            수면 상태
            <input
              value={health.sleepNote}
              onChange={(e) => setHealth((h) => ({ ...h, sleepNote: e.target.value }))}
              placeholder="예: 자주 깸"
            />
          </label>
        </div>

        <div className="chat-log" role="log" aria-live="polite">
          {turns.map((turn, idx) => (
            <p key={`${turn.role}-${idx}`} className={`chat-bubble chat-bubble-${turn.role}`}>
              <strong>{turn.role === "assistant" ? "AI" : "나"}</strong> {turn.message}
            </p>
          ))}
          {streamBuf !== null ? (
            <p className="chat-bubble chat-bubble-assistant chat-bubble-streaming">
              <strong>AI</strong> {streamBuf}
              <span className="chat-stream-caret" aria-hidden="true" />
            </p>
          ) : null}
          {busy && streamBuf === null ? (
            <p className="chat-bubble chat-bubble-assistant">
              <strong>AI</strong> 답변을 준비 중입니다...
            </p>
          ) : null}
        </div>

        <div className="chat-input-row">
          <input
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="예: 요즘 소화불량이 심한데 어떤 준비를 하면 좋을까요?"
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                void askAssistant();
              }
            }}
          />
          <button className="btn btn-primary" type="button" onClick={() => void askAssistant()} disabled={!canAsk}>
            {busy ? "전송 중..." : "질문하기"}
          </button>
        </div>
        {error ? <p className="consult-error">{error}</p> : null}

        <div className="section-cta">
          <Link className="btn btn-primary" href="/consumer?panel=survey#patient-intake">
            사전문진·연결 단계
          </Link>
          <Link className="btn btn-ghost" href="/#contact">
            문의
          </Link>
        </div>
      </div>
    </section>
  );
}
