"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { CLINIC_NO1KMEDI_ORIGIN } from "@/lib/no1kmedi-portal-host";
import {
  NATIONAL_KM_ASK_DISCLAIMER_KEY,
  NATIONAL_KM_ASK_STORAGE_KEY,
  NATIONAL_KM_ASK_V1,
  NATIONAL_KM_STARTER_PROMPTS,
} from "@/lib/national-km-ask-v1";
import { KmAskProvenanceStrip } from "@/components/KmAskProvenanceStrip";
import { streamTextClient } from "@/lib/consumer-chat-stream";

type Turn = { role: "user" | "assistant"; message: string };

type ChatResponse = {
  success: boolean;
  response?: string;
  error?: string;
};

function loadTurns(): Turn[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(NATIONAL_KM_ASK_STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as Turn[];
    return Array.isArray(parsed) ? parsed.slice(-40) : [];
  } catch {
    return [];
  }
}

export function NationalKmAskClient() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [streamBuf, setStreamBuf] = useState<string | null>(null);
  const [disclaimerOk, setDisclaimerOk] = useState(false);
  const requestGen = useRef(0);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    setTurns(loadTurns());
    try {
      setDisclaimerOk(window.localStorage.getItem(NATIONAL_KM_ASK_DISCLAIMER_KEY) === "1");
    } catch {
      setDisclaimerOk(false);
    }
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [turns, streamBuf, busy]);

  const persistTurns = useCallback((next: Turn[]) => {
    setTurns(next);
    try {
      window.localStorage.setItem(NATIONAL_KM_ASK_STORAGE_KEY, JSON.stringify(next.slice(-40)));
    } catch {
      /* ignore */
    }
  }, []);

  const acceptDisclaimer = useCallback(() => {
    setDisclaimerOk(true);
    try {
      window.localStorage.setItem(NATIONAL_KM_ASK_DISCLAIMER_KEY, "1");
    } catch {
      /* ignore */
    }
  }, []);

  const userTurnCount = useMemo(() => turns.filter((t) => t.role === "user").length, [turns]);
  const showSessionHint = userTurnCount >= 5;
  const canAsk = useMemo(() => disclaimerOk && message.trim().length > 1 && !busy, [busy, disclaimerOk, message]);

  const sendMessage = useCallback(
    async (text: string) => {
      const userMessage = text.trim();
      if (!userMessage || busy || !disclaimerOk) return;

      const gen = ++requestGen.current;
      const turnsWithUser: Turn[] = [...turns, { role: "user", message: userMessage }];
      setMessage("");
      setBusy(true);
      setError("");
      setStreamBuf(null);
      persistTurns(turnsWithUser);

      try {
        const res = await fetch("/api/guardian/ai-guardian/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            audience: "km_national",
            message: userMessage,
            health_data: {},
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
        persistTurns([...turnsWithUser, { role: "assistant", message: full }]);
        setStreamBuf(null);
      } catch {
        if (gen !== requestGen.current) return;
        setError("답변 준비가 지연되고 있습니다. 잠시 후 다시 시도해 주세요.");
      } finally {
        if (gen === requestGen.current) {
          setBusy(false);
          setStreamBuf(null);
        }
      }
    },
    [busy, disclaimerOk, persistTurns, turns],
  );

  const clearChat = useCallback(() => {
    persistTurns([]);
    setError("");
    setStreamBuf(null);
  }, [persistTurns]);

  return (
    <div className="km-ask-app">
      <header className="km-ask-header">
        <div className="km-ask-brand">
          <span className="km-ask-logo" aria-hidden="true">
            韓
          </span>
          <div>
            <h1 className="km-ask-title">{NATIONAL_KM_ASK_V1.product_name_ko}</h1>
            <p className="km-ask-subtitle">JEMA AI · 대국민 참고 Q&A (진료·처방 대체 아님)</p>
          </div>
        </div>
        <nav className="km-ask-nav" aria-label="보조 링크">
          <Link href={`${CLINIC_NO1KMEDI_ORIGIN}/clinician`} className="km-ask-nav-link km-ask-nav-link--primary">
            한의사 모드
          </Link>
          <button type="button" className="km-ask-nav-link" onClick={clearChat}>
            대화 지우기
          </button>
        </nav>
      </header>

      <div className="km-ask-layer-strip" role="status">
        <span className="km-ask-layer-badge">L0 · 참고용 · 진단·처방 대체 아님</span>
        <span className="km-ask-layer-hint">Time-to-Trust — 교육·참고 맥락만 제공합니다</span>
      </div>

      <main className="km-ask-main">
        {!disclaimerOk ? (
          <div className="km-ask-disclaimer-gate" role="dialog" aria-labelledby="km-ask-disclaimer-title">
            <h2 id="km-ask-disclaimer-title">이용 전 안내</h2>
            <p>{NATIONAL_KM_ASK_V1.disclaimer_ko}</p>
            <button type="button" className="km-ask-disclaimer-btn" onClick={acceptDisclaimer}>
              이해했습니다 · 질문 시작
            </button>
          </div>
        ) : (
          <>
            <div className="km-ask-thread" role="log" aria-live="polite" aria-relevant="additions">
              {turns.length === 0 && !streamBuf ? (
                <div className="km-ask-empty">
                  <p className="km-ask-empty-lead">한의학에 대해 무엇이든 물어보세요.</p>
                  <p className="km-ask-empty-hint">아래 예시를 눌러 시작할 수 있습니다.</p>
                  <div className="km-ask-starters">
                    {NATIONAL_KM_STARTER_PROMPTS.map((prompt) => (
                      <button
                        key={prompt}
                        type="button"
                        className="km-ask-starter"
                        disabled={busy}
                        onClick={() => void sendMessage(prompt)}
                      >
                        {prompt}
                      </button>
                    ))}
                  </div>
                </div>
              ) : null}

              {turns.map((turn, i) => (
                <div key={`${turn.role}-${i}`} className="km-ask-turn">
                  <div
                    className={`km-ask-bubble km-ask-bubble--${turn.role === "user" ? "user" : "assistant"}`}
                  >
                    <span className="km-ask-bubble-role">{turn.role === "user" ? "나" : "한의학 AI"}</span>
                    <div className="km-ask-bubble-body">{turn.message}</div>
                  </div>
                  {turn.role === "assistant" ? <KmAskProvenanceStrip /> : null}
                </div>
              ))}

              {streamBuf ? (
                <div className="km-ask-turn">
                  <div className="km-ask-bubble km-ask-bubble--assistant">
                    <span className="km-ask-bubble-role">한의학 AI</span>
                    <div className="km-ask-bubble-body">{streamBuf}</div>
                  </div>
                  <KmAskProvenanceStrip />
                </div>
              ) : null}

              {busy && !streamBuf ? (
                <p className="km-ask-typing" role="status">
                  답변을 준비하는 중…
                </p>
              ) : null}

              <div ref={bottomRef} />
            </div>

            {showSessionHint ? (
              <div className="km-ask-session-hint" role="status">
                <span>주제를 정리할까요?</span>
                <button type="button" className="km-ask-session-hint-btn" onClick={clearChat}>
                  새 대화
                </button>
              </div>
            ) : null}

            {error ? (
              <p className="km-ask-error" role="alert">
                {error}
              </p>
            ) : null}

            <form
              className="km-ask-composer"
              onSubmit={(e) => {
                e.preventDefault();
                void sendMessage(message);
              }}
            >
              <textarea
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder="예: 요즘 손발이 차고 소화가 안 좋은데 한의학적으로 어떻게 이해하면 좋을까요?"
                rows={2}
                disabled={busy}
                aria-label="질문 입력"
              />
              <button type="submit" className="km-ask-send" disabled={!canAsk}>
                {busy ? "전송 중…" : "질문하기"}
              </button>
            </form>
          </>
        )}
      </main>

      <footer className="km-ask-footer">
        <p>{NATIONAL_KM_ASK_V1.disclaimer_ko}</p>
        <p>
          한의사·원장이신가요?{" "}
          <Link href={`${CLINIC_NO1KMEDI_ORIGIN}/clinician`}>인증 한의사 모드</Link>에서 SOAP·진료 분석을 이용하세요.
        </p>
      </footer>
    </div>
  );
}
