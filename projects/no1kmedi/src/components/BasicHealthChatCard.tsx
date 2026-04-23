/**
 * @MKM12-METADATA
 * Type: UI
 * Vector: {S:0.72, L:0.58, K:0.84, M:0.44}
 * Balance: 90
 * Purpose: Provide patient-facing basic health Q&A linked to clinic guidance.
 * Keywords: React, chat, intake, clinical guidance, funnel
 */
"use client";

import { useMemo, useState } from "react";
import Link from "next/link";

type ChatTurn = {
  role: "user" | "assistant";
  message: string;
};

type ChatResponse = {
  success: boolean;
  response?: string;
  error?: string;
};

type BasicHealthChatCardProps = {
  /** marketing: 랜딩 섹션용 제목 포함 · workspace: 앱형 전체 높이 레이아웃용 심플 블록 */
  layout?: "marketing" | "workspace";
};

export function BasicHealthChatCard({ layout = "marketing" }: BasicHealthChatCardProps) {
  const [message, setMessage] = useState("");
  const [painArea, setPainArea] = useState("");
  const [painScale, setPainScale] = useState("5");
  const [digestiveNote, setDigestiveNote] = useState("");
  const [sleepNote, setSleepNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [history, setHistory] = useState<ChatTurn[]>([
    {
      role: "assistant",
      message:
        "기본 건강 정보를 바탕으로 상담 전 안내를 도와드립니다. 응급 증상은 즉시 119/응급실을 이용해 주세요.",
    },
  ]);

  const canAsk = useMemo(() => message.trim().length > 1 && !busy, [message, busy]);

  async function askAssistant() {
    if (!canAsk) return;
    const userMessage = message.trim();
    setBusy(true);
    setError("");
    const historyWithUser: ChatTurn[] = [...history, { role: "user", message: userMessage }];
    setHistory(historyWithUser);
    setMessage("");
    try {
      const res = await fetch("/api/guardian/ai-guardian/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: userMessage,
          health_data: {
            survey: {
              pain_area: painArea.trim() || "미입력",
              pain_scale_0_10: Number(painScale),
              digestion_pattern: digestiveNote.trim() || "미입력",
              sleep_pattern: sleepNote.trim() || "미입력",
              vector_4d: { S: 0.25, L: 0.25, K: 0.25, M: 0.25 },
            },
          },
          chat_history: historyWithUser.slice(-12),
        }),
      });
      const json = (await res.json()) as ChatResponse;
      if (!res.ok || !json.success || !json.response) {
        throw new Error(json.error || "chat_request_failed");
      }
      setHistory((prev) => [...prev, { role: "assistant", message: json.response || "" }]);
    } catch {
      setError("AI 응답이 지연되고 있습니다. 아래 문진 입력으로 바로 상담 연결을 진행해 주세요.");
    } finally {
      setBusy(false);
    }
  }

  const isWorkspace = layout === "workspace";

  return (
    <section
      id="basic-health-chat"
      aria-labelledby="basic-health-chat-title"
      className={isWorkspace ? "workspace-chat-root" : undefined}
    >
      <h2 id="basic-health-chat-title" className={isWorkspace ? "sr-only" : undefined}>
        AI 기본 건강상담 (사전 안내)
      </h2>
      {isWorkspace ? null : (
        <p className="section-lead">간단한 건강 질문에 답하고, 필요 시 바로 문진/예약 단계로 연결됩니다.</p>
      )}

      <div className={`chat-card${isWorkspace ? " chat-card--workspace" : ""}`}>
        <div className="chat-profile-grid">
          <label>
            주요 불편 부위
            <input value={painArea} onChange={(e) => setPainArea(e.target.value)} placeholder="예: 목, 허리, 소화" />
          </label>
          <label>
            통증 강도 (0-10)
            <input value={painScale} onChange={(e) => setPainScale(e.target.value)} type="number" min={0} max={10} />
          </label>
          <label>
            소화 상태
            <input value={digestiveNote} onChange={(e) => setDigestiveNote(e.target.value)} placeholder="예: 더부룩함" />
          </label>
          <label>
            수면 상태
            <input value={sleepNote} onChange={(e) => setSleepNote(e.target.value)} placeholder="예: 자주 깸" />
          </label>
        </div>

        <div className="chat-log" role="log" aria-live="polite">
          {history.map((turn, idx) => (
            <p key={`${turn.role}-${idx}`} className={`chat-bubble chat-bubble-${turn.role}`}>
              <strong>{turn.role === "assistant" ? "AI" : "나"}</strong> {turn.message}
            </p>
          ))}
          {busy ? <p className="chat-bubble chat-bubble-assistant"><strong>AI</strong> 답변을 준비 중입니다...</p> : null}
        </div>

        <div className="chat-input-row">
          <input
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="예: 요즘 소화불량이 심한데 어떤 준비를 하면 좋을까요?"
            onKeyDown={(e) => {
              if (e.key === "Enter") {
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
          {isWorkspace ? (
            <>
              <Link className="btn btn-primary" href="/consumer?panel=survey#patient-intake">
                사전문진·연결 단계
              </Link>
              <Link className="btn btn-ghost" href="/#contact">
                문의
              </Link>
            </>
          ) : (
            <>
              <a className="btn btn-primary" href="#patient-intake">
                사전문진으로 이어가기
              </a>
              <a className="btn btn-ghost" href="#contact">
                한의원 상담 연결 문의
              </a>
            </>
          )}
        </div>
      </div>
    </section>
  );
}
