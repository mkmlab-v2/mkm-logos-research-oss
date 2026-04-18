"use client";

import { useMemo, useState } from "react";

type CdssCitation = {
  citation_id: string;
  source_title: string;
  source_excerpt: string;
  source_ref: string;
  evidence_level: "A" | "B" | "C";
};

type AdvancedConsultResponse = {
  success: boolean;
  error?: string;
  draft?: {
    request_id: string;
    clinical_summary: string;
    profile_summary: { sasang_candidate: string; saju_reference: string; saju_source: "live" | "fallback" };
    reasoning: { syndrome_hypothesis: string; care_direction: string; caution: string };
    citations: CdssCitation[];
    non_medical_notice: string;
  };
  guardrail?: {
    lane_separation: boolean;
    citation_enforced: boolean;
    physician_confirmation_required: boolean;
  };
};

type MemberAccessStatusResponse = {
  success: boolean;
  error?: string;
  email?: string;
  payment_status?: string;
  verification_status?: string;
  can_use_pro_clinical_assist?: boolean;
};

export function AdvancedConsultForm() {
  const [actorId, setActorId] = useState("hanui-demo-001");
  const [accessEmail, setAccessEmail] = useState("");
  const [accessBusy, setAccessBusy] = useState(false);
  const [accessStatus, setAccessStatus] = useState<MemberAccessStatusResponse | null>(null);
  /** ISO instant with explicit Z or offset + IANA zone (same contract as mkmlife saju resolver). */
  const [birthInstantUtc, setBirthInstantUtc] = useState("1990-01-01T00:00:00Z");
  const [ianaTz, setIanaTz] = useState("Asia/Seoul");
  const [chiefComplaint, setChiefComplaint] = useState("");
  const [onset, setOnset] = useState("");
  const [severity, setSeverity] = useState("");
  const [medication, setMedication] = useState("");
  const [digestionPattern, setDigestionPattern] = useState("");
  const [sleepPattern, setSleepPattern] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<AdvancedConsultResponse | null>(null);
  const [selectedCitationId, setSelectedCitationId] = useState<string | null>(null);

  const selectedCitation = useMemo(() => {
    if (!result?.draft?.citations || !selectedCitationId) return null;
    return result.draft.citations.find((c) => c.citation_id === selectedCitationId) ?? null;
  }, [result?.draft?.citations, selectedCitationId]);

  const canUseAdvancedConsult = accessStatus?.success === true && accessStatus?.can_use_pro_clinical_assist === true;
  const needsUpgradeCta = accessStatus?.success === true && !canUseAdvancedConsult;

  async function checkAccessStatus() {
    const email = accessEmail.trim().toLowerCase();
    if (!email) {
      setAccessStatus({ success: false, error: "email is required" });
      return;
    }
    setAccessBusy(true);
    try {
      const res = await fetch(`/api/member/access-status?email=${encodeURIComponent(email)}`);
      const json = (await res.json()) as MemberAccessStatusResponse;
      setAccessStatus(json);
    } catch {
      setAccessStatus({ success: false, error: "access_status_fetch_failed" });
    } finally {
      setAccessBusy(false);
    }
  }

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canUseAdvancedConsult) {
      setResult({ success: false, error: "member_access_required" });
      return;
    }
    setBusy(true);
    setResult(null);
    setSelectedCitationId(null);
    try {
      const res = await fetch("/api/cdss/advanced-consult", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          schema: "patient_consult_input_v1",
          request_id: `req_${Date.now()}`,
          actor_id: actorId,
          lane_a_profile: {
            birth_instant_utc: birthInstantUtc.trim(),
            iana_tz: ianaTz.trim(),
            constitution_survey: {
              digestion_pattern: digestionPattern,
              sleep_pattern: sleepPattern,
            },
          },
          lane_b_clinical: {
            chief_complaint: chiefComplaint,
            onset,
            severity,
            medication,
            health_survey: {
              sleep_quality: sleepPattern,
            },
          },
        }),
      });
      const json = (await res.json()) as AdvancedConsultResponse;
      setResult(json);
      if (json?.draft?.citations?.length) setSelectedCitationId(json.draft.citations[0].citation_id);
    } catch {
      setResult({ success: false, error: "advanced_consult_fetch_failed" });
    } finally {
      setBusy(false);
    }
  }

  return (
    <section id="advanced-consult" aria-labelledby="advanced-consult-title">
      <h2 id="advanced-consult-title">고급 진료 보조 리포트 (CDSS Draft)</h2>
      <p className="section-lead">생년월일시·체질 설문·건강 설문을 분리 입력하면, 근거(citation) 기반 초안을 생성합니다.</p>

      <div className="card consult-access-card">
        <h3>회원 권한 확인</h3>
        <div className="consult-access-row">
          <input value={accessEmail} onChange={(e) => setAccessEmail(e.target.value)} placeholder="회원 이메일" type="email" />
          <button type="button" className="btn btn-ghost" onClick={checkAccessStatus} disabled={accessBusy}>
            {accessBusy ? "확인 중..." : "권한 확인"}
          </button>
        </div>
        {accessStatus?.success ? (
          <>
            <p className="consult-access-ok">
              payment: {accessStatus.payment_status} / verification: {accessStatus.verification_status} / 사용가능: {canUseAdvancedConsult ? "YES" : "NO"}
            </p>
            {needsUpgradeCta ? (
              <div className="consult-access-cta">
                <a className="btn btn-primary" href="#contact">결제/심사 진행 문의</a>
                <span>승인 완료 후 고급 CDSS 기능이 열립니다.</span>
              </div>
            ) : null}
          </>
        ) : accessStatus ? (
          <p className="consult-error">권한 확인 오류: {accessStatus.error || "unknown_error"}</p>
        ) : null}
      </div>

      <form className="consult-form" onSubmit={onSubmit}>
        <label>한의사 계정 ID<input value={actorId} onChange={(e) => setActorId(e.target.value)} required /></label>
        <label>
          출생 시각 (UTC, ISO)
          <input
            value={birthInstantUtc}
            onChange={(e) => setBirthInstantUtc(e.target.value)}
            placeholder="1990-01-01T00:00:00Z"
            required
            autoComplete="bday-time"
          />
        </label>
        <label>
          시간대 (IANA)
          <input
            value={ianaTz}
            onChange={(e) => setIanaTz(e.target.value)}
            placeholder="Asia/Seoul"
            required
            spellCheck={false}
          />
        </label>
        <p className="section-lead" style={{ fontSize: "0.9rem", marginTop: "-0.5rem" }}>
          전 세계 출생은 절대시각(UTC)·Z 또는 ±오프셋과 IANA 구역을 함께 입력합니다. 레거시 로컬 문자열은 API에서 선택 지원합니다.
        </p>
        <label>주증상 (임상 레인)<input value={chiefComplaint} onChange={(e) => setChiefComplaint(e.target.value)} required /></label>
        <label>발현 시점<input value={onset} onChange={(e) => setOnset(e.target.value)} required /></label>
        <label>중증도<input value={severity} onChange={(e) => setSeverity(e.target.value)} required /></label>
        <label>복약 정보<input value={medication} onChange={(e) => setMedication(e.target.value)} /></label>
        <label>체질 설문 (소화 패턴)<input value={digestionPattern} onChange={(e) => setDigestionPattern(e.target.value)} /></label>
        <label>건강 설문 (수면 패턴)<input value={sleepPattern} onChange={(e) => setSleepPattern(e.target.value)} /></label>
        <button type="submit" className="btn btn-primary" disabled={busy || !canUseAdvancedConsult}>
          {busy ? "추론 중..." : "고급 진료 보조 리포트 생성"}
        </button>
      </form>

      {result ? (
        <div className="consult-result">
          {!result.success ? (
            <p className="consult-error">오류: {result.error || "unknown_error"}</p>
          ) : (
            <>
              <p className="consult-summary">{result.draft?.clinical_summary}</p>
              <div className="grid-3">
                <article className="card"><h3>체질 후보</h3><p>{result.draft?.profile_summary.sasang_candidate}</p></article>
                <article className="card">
                  <h3>만세력 참조</h3>
                  <p>{result.draft?.profile_summary.saju_reference}</p>
                  <p className="consult-source-chip">source: {result.draft?.profile_summary.saju_source === "live" ? "LIVE API" : "FALLBACK"}</p>
                </article>
                <article className="card">
                  <h3>가드레일</h3>
                  <p>분리해석: {result.guardrail?.lane_separation ? "ON" : "OFF"} / 근거강제: {result.guardrail?.citation_enforced ? "ON" : "OFF"}</p>
                </article>
              </div>

              <div className="consult-reasoning">
                <h3>추론 초안</h3>
                <p>{result.draft?.reasoning.syndrome_hypothesis}</p>
                <p>{result.draft?.reasoning.care_direction}</p>
                <p>{result.draft?.reasoning.caution}</p>
              </div>

              <div className="consult-citations">
                <h3>근거 데이터 (Citation)</h3>
                <div className="steps" role="list">
                  {result.draft?.citations.map((citation) => (
                    <button
                      key={citation.citation_id}
                      type="button"
                      className={`btn btn-ghost citation-btn${selectedCitationId === citation.citation_id ? " is-active" : ""}`}
                      onClick={() => setSelectedCitationId(citation.citation_id)}
                    >
                      {citation.citation_id}
                    </button>
                  ))}
                </div>
                {selectedCitation ? (
                  <article className="card citation-card">
                    <h4>{selectedCitation.source_title}</h4>
                    <p>{selectedCitation.source_excerpt}</p>
                    <p><strong>ref:</strong> {selectedCitation.source_ref}</p>
                  </article>
                ) : null}
              </div>

              <p className="consult-notice">{result.draft?.non_medical_notice}</p>
            </>
          )}
        </div>
      ) : null}
    </section>
  );
}
