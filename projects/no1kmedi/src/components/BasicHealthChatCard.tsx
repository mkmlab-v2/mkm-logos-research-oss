/**
 * @MKM12-METADATA
 * Type: UI
 * Vector: {S:0.72, L:0.58, K:0.84, M:0.44}
 * Balance: 90
 * Purpose: Homepage funnel — optional brief Q&A; presurvey SSOT is /intake only.
 * Keywords: React, chat, intake, clinical guidance, funnel
 */
"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { siteCopy } from "@/content/siteCopy";

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
  const copy = siteCopy.basic_health_chat;
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [history, setHistory] = useState<ChatTurn[]>(() => [
    { role: "assistant", message: copy.assistant_greeting },
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
          audience: "consumer",
          message: userMessage,
          health_data: {
            survey: {
              pain_area: copy.survey_defaults.pain_area_empty,
              pain_scale_0_10: 0,
              digestion_pattern: copy.survey_defaults.digestion_empty,
              sleep_pattern: copy.survey_defaults.sleep_empty,
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
      setError(copy.chat.error_message);
    } finally {
      setBusy(false);
    }
  }

  const isWorkspace = layout === "workspace";
  const ctas = isWorkspace ? copy.ctas.workspace : copy.ctas.marketing;

  const intakeCta = isWorkspace ? (
    <Link className="btn btn-primary" href={ctas.primary.href}>
      {ctas.primary.label}
    </Link>
  ) : (
    <a className="btn btn-primary" href={ctas.primary.href}>
      {ctas.primary.label}
    </a>
  );

  const secondaryCta = isWorkspace ? (
    <Link className="btn btn-ghost" href={ctas.secondary.href}>
      {ctas.secondary.label}
    </Link>
  ) : (
    <a className="btn btn-ghost" href={ctas.secondary.href}>
      {ctas.secondary.label}
    </a>
  );

  return (
    <section
      id="basic-health-chat"
      aria-labelledby="basic-health-chat-title"
      className={isWorkspace ? "workspace-chat-root" : undefined}
    >
      <h2 id="basic-health-chat-title" className={isWorkspace ? "sr-only" : undefined}>
        {copy.title}
      </h2>
      {isWorkspace ? null : <p className="section-lead">{copy.section_lead}</p>}

      <div className={`chat-card${isWorkspace ? " chat-card--workspace" : ""}`}>
        <div className="section-cta clinic-intake-home-cta">
          {intakeCta}
          {secondaryCta}
        </div>
        <p className="clinic-intake-hint">{copy.intake_hint}</p>

        <div className="chat-log" role="log" aria-live="polite">
          {history.map((turn, idx) => (
            <p key={`${turn.role}-${idx}`} className={`chat-bubble chat-bubble-${turn.role}`}>
              <strong>{turn.role === "assistant" ? copy.chat.assistant_role : copy.chat.user_role}</strong>{" "}
              {turn.message}
            </p>
          ))}
          {busy ? (
            <p className="chat-bubble chat-bubble-assistant">
              <strong>{copy.chat.assistant_role}</strong> {copy.chat.busy_message}
            </p>
          ) : null}
        </div>

        <div className="chat-input-row">
          <input
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder={copy.placeholders.message}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                void askAssistant();
              }
            }}
          />
          <button className="btn btn-primary" type="button" onClick={() => void askAssistant()} disabled={!canAsk}>
            {busy ? copy.chat.send_busy : copy.chat.send_idle}
          </button>
        </div>
        {error ? <p className="consult-error">{error}</p> : null}
      </div>
    </section>
  );
}
