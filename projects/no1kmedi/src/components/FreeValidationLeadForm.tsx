/**
 * @MKM12-METADATA
 * Type: UI
 * Vector: {S:0.72, L:0.62, K:0.78, M:0.44}
 * Balance: 90
 * Purpose: Capture free validation leads and emit funnel events.
 * Keywords: React, lead, form, analytics, conversion
 */
"use client";

import { useState } from "react";

type LeadPayload = {
  name: string;
  email: string;
  company: string;
  use_case: string;
};

type LeadApiResponse = {
  success: boolean;
  lead_id?: string;
  error?: string;
};

function trackEvent(event: string, payload?: Record<string, unknown>) {
  if (typeof window === "undefined") return;
  const w = window as Window & { dataLayer?: Array<Record<string, unknown>> };
  if (Array.isArray(w.dataLayer)) {
    w.dataLayer.push({ event, ...payload });
  }
}

export function FreeValidationLeadForm() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [company, setCompany] = useState("");
  const [useCase, setUseCase] = useState("");
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState<string>("");
  const [error, setError] = useState<string>("");

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!name.trim() || !email.trim() || !company.trim()) {
      setError("이름/이메일/회사명을 입력해 주세요.");
      return;
    }

    setBusy(true);
    setError("");
    setStatus("");

    const payload: LeadPayload = {
      name: name.trim(),
      email: email.trim().toLowerCase(),
      company: company.trim(),
      use_case: useCase.trim(),
    };

    try {
      const res = await fetch("/api/leads/free-validation", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const json = (await res.json()) as LeadApiResponse;
      if (!res.ok || !json.success) {
        setError(json.error || "리드 저장 중 오류가 발생했습니다.");
        return;
      }

      trackEvent("submit_lead", { lead_channel: "free_validation_form" });
      setStatus("접수 완료: 1영업일 내에 무료 검증 안내를 드립니다.");
      setName("");
      setEmail("");
      setCompany("");
      setUseCase("");
    } catch {
      setError("네트워크 오류로 접수에 실패했습니다.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card lead-form-card">
      <h3>무료 검증 신청</h3>
      <p className="section-lead">월 30회 샘플 검증으로 먼저 확인하고, 필요 시 90일 파일럿으로 전환합니다.</p>
      <form className="lead-form" onSubmit={onSubmit}>
        <label>
          이름
          <input value={name} onChange={(e) => setName(e.target.value)} required />
        </label>
        <label>
          이메일
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </label>
        <label>
          회사명
          <input value={company} onChange={(e) => setCompany(e.target.value)} required />
        </label>
        <label>
          주요 사용 시나리오 (선택)
          <input value={useCase} onChange={(e) => setUseCase(e.target.value)} placeholder="예: 재무 리스크 조기 경보" />
        </label>
        <button
          type="submit"
          className="btn btn-primary"
          disabled={busy}
          onClick={() => trackEvent("click_free_validation", { location: "home_contact" })}
        >
          {busy ? "제출 중..." : "무료 검증 신청하기"}
        </button>
      </form>
      {status ? <p className="lead-success">{status}</p> : null}
      {error ? <p className="consult-error">{error}</p> : null}
    </div>
  );
}
