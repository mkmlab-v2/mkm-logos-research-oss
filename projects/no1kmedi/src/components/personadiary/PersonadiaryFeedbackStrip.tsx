"use client";

import { useState } from "react";

type Props = {
  profileId?: string;
  calendarKst?: string;
  surface?: "daily_guide" | "monthly_guide" | "reflect";
};

export function PersonadiaryFeedbackStrip({
  profileId,
  calendarKst,
  surface = "daily_guide",
}: Props) {
  const [sent, setSent] = useState<"idle" | "yes" | "no">("idle");
  const [busy, setBusy] = useState(false);

  async function submit(helpful: boolean) {
    if (busy || sent !== "idle") return;
    setBusy(true);
    try {
      const res = await fetch("/api/personadiary/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          helpful,
          surface,
          profile_id: profileId,
          calendar_kst: calendarKst,
          consent_feedback_use: true,
        }),
      });
      if (res.ok) setSent(helpful ? "yes" : "no");
    } finally {
      setBusy(false);
    }
  }

  if (sent !== "idle") {
    return (
      <p className="pd-guide-muted pd-feedback-thanks">
        피드백 감사합니다 · B-track 학습용(의료·투자 조언 아님)
      </p>
    );
  }

  return (
    <div className="pd-feedback-strip">
      <span className="pd-reflect-label">오늘 가이드가 도움이 됐나요?</span>
      <div className="pd-feedback-actions">
        <button
          type="button"
          className="btn btn-secondary"
          disabled={busy}
          onClick={() => void submit(true)}
        >
          도움됨
        </button>
        <button type="button" className="btn btn-ghost" disabled={busy} onClick={() => void submit(false)}>
          아쉬움
        </button>
      </div>
    </div>
  );
}