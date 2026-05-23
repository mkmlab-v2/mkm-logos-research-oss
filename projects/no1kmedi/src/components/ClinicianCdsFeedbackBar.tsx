"use client";

import { useState } from "react";

type Props = {
  requestId?: string;
  disabled?: boolean;
};

export function ClinicianCdsFeedbackBar({ requestId, disabled }: Props) {
  const [sent, setSent] = useState(false);
  const [busy, setBusy] = useState(false);

  async function send(helpful: boolean, physicianAction: "accept" | "edit" | "reject" | "defer") {
    if (busy || sent || disabled || !requestId) return;
    setBusy(true);
    try {
      const res = await fetch("/api/cdss/physician-feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          helpful,
          physician_action: physicianAction,
          request_id: requestId,
          surface: "cds_draft",
          consent_feedback_use: true,
        }),
      });
      if (res.ok) setSent(true);
    } finally {
      setBusy(false);
    }
  }

  if (!requestId) return null;
  if (sent) {
    return <p className="consult-muted">초안 피드백이 기록되었습니다 · 최종 판단은 한의사 확인</p>;
  }

  return (
    <div className="clinician-cds-feedback">
      <span className="consult-label">CDSS 초안 피드백 (B-track, 비처방)</span>
      <div className="clinician-cds-feedback-actions">
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          disabled={busy}
          onClick={() => void send(true, "accept")}
        >
          수용
        </button>
        <button
          type="button"
          className="btn btn-ghost btn-sm"
          disabled={busy}
          onClick={() => void send(false, "edit")}
        >
          수정 필요
        </button>
        <button
          type="button"
          className="btn btn-ghost btn-sm"
          disabled={busy}
          onClick={() => void send(false, "reject")}
        >
          기각
        </button>
      </div>
    </div>
  );
}
