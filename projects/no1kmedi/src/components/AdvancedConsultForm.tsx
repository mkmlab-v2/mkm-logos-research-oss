"use client";

import { useEffect, useMemo, useState } from "react";
import type { CdssGenerationReason } from "@/lib/cdss-contract";
import { getConfidenceThresholds } from "@/lib/confidence-thresholds";

function formatIntakePinInput(value: string): string {
  const normalized = value.replace(/[^A-Z0-9]/gi, "").toUpperCase().slice(0, 6);
  if (normalized.length <= 3) return normalized;
  return `${normalized.slice(0, 3)}-${normalized.slice(3)}`;
}

function triageBadgeClass(level: "routine" | "priority" | "emergency"): string {
  return `triage-badge triage-badge-${level}`;
}

function triageLabel(level: "routine" | "priority" | "emergency"): string {
  if (level === "routine") return "일반";
  if (level === "priority") return "우선";
  return "응급";
}

function normalizePatientNameInput(value: string): string {
  return value.replace(/\s+/g, " ").trimStart();
}

function normalizePhoneLast4Input(value: string): string {
  return value.replace(/\D/g, "").slice(0, 4);
}

function cdssTemplateHint(reason?: CdssGenerationReason): string {
  switch (reason) {
    case "disabled":
      return "서버에서 CDSS 생성형 추론이 꺼져 있습니다. 활성화하려면 CDSS_LLM_ENABLED=true.";
    case "no_credentials":
      return "API 베이스 URL·키가 없습니다. CDSS_LLM_API_* 또는 GEMINI_API_KEY(권장), 혹은 CDSS_LLM_USE_OPENROUTER=true + OPENROUTER_API_KEY 를 설정하세요.";
    case "no_models":
      return "모델명이 비어 있습니다. CDSS_LLM_PRIMARY_MODEL 또는 CDSS_GEMINI_MODEL/GEMINI_MODEL/OPENROUTER_MODEL 을 지정하세요.";
    case "llm_error":
      return "모델 호출은 시도했으나 응답이 없거나 JSON 형식이 맞지 않았습니다. 타임아웃·모델 호환(response_format)·네트워크를 확인하세요.";
    default:
      return "생성형 CDSS 추론이 이번 응답에 포함되지 않았습니다.";
  }
}

function confidenceTier(value: number): "high" | "medium" | "low" {
  const thresholds = getConfidenceThresholds();
  if (value >= thresholds.high_min) return "high";
  if (value >= thresholds.medium_min) return "medium";
  return "low";
}

function confidenceLevel(value: number): "A" | "B" | "C" {
  const tier = confidenceTier(value);
  if (tier === "high") return "A";
  if (tier === "medium") return "B";
  return "C";
}

const RECENT_PIN_STORAGE_KEY = "advanced_consult_recent_pins_v1";

type RecentPinItem = {
  pin: string;
  name: string;
  phoneLast4: string;
  savedAt: string;
};

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
    lens_mode: "neutral" | "integrated" | "compare";
    include_scripture: boolean;
    clinical_summary: string;
    profile_summary: { sasang_candidate: string; saju_reference: string; saju_source: "live" | "fallback" };
    reasoning: { syndrome_hypothesis: string; care_direction: string; caution: string };
    citations: CdssCitation[];
    collaboration?: {
      enabled: boolean;
      mode: "three_agent_mvp" | "four_agent_full";
      gate_status: "PASS" | "REVIEW" | "BLOCK";
      gate_reasons: string[];
      gate_scores: {
        quality: number;
        cost: number;
        safety: number;
      };
      agreement_points: string[];
      conflict_points: string[];
      final_consensus: string;
      priority_actions_top3: string[];
      do_not_do_top3: string[];
      plan_30d: string[];
      opinions: Array<{
        agent_id: "sasang_ai" | "myeongri_ai" | "scripture_ai" | "orchestrator_ai";
        stance: string;
        rationale: string[];
        confidence: number;
      }>;
    };
    fact_lock?: {
      evidence_path: string;
      validated_at: string;
      confidence_level: "A" | "B" | "C";
      note?: string;
    };
    non_medical_notice: string;
    generation?: { llm_used: boolean; reason?: CdssGenerationReason };
  };
  guardrail?: {
    lane_separation: boolean;
    citation_enforced: boolean;
    physician_confirmation_required: boolean;
  };
  evidence_meta?: {
    literature_count_rule_version?: string;
    citation_count: number;
    literature_injected_count: number;
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

type PatientPinLookupResponse = {
  success: boolean;
  error?: string;
  retry_after_seconds?: number;
  survey?: {
    survey_id: string;
    intake_pin: string;
    triage_level: "routine" | "priority" | "emergency";
    patient_name: string;
    symptoms: {
      pain_area: string;
      pain_scale_0_10: number;
      symptom_duration: string;
      consultation_goal: string;
    };
    constitution_survey: {
      sleep_pattern: string;
      digestion_pattern: string;
    };
  };
};

type AdvancedConsultFormProps = {
  activeView?: "assist" | "pin";
};

export function AdvancedConsultForm({ activeView = "assist" }: AdvancedConsultFormProps) {
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
  const [bodyHeatPreference, setBodyHeatPreference] = useState("");
  const [stressReactivity, setStressReactivity] = useState("");
  const [constitutionFreeText, setConstitutionFreeText] = useState("");
  /** PIN 불러오기 시 문진 통증 척도와 동기화 가능 */
  const [painScale0to10, setPainScale0to10] = useState("");
  const [redFlagNotes, setRedFlagNotes] = useState("");
  const [healthAppetite, setHealthAppetite] = useState("");
  const [healthBowelPattern, setHealthBowelPattern] = useState("");
  const [lensMode, setLensMode] = useState<"neutral" | "integrated" | "compare">("neutral");
  const [includeScripture, setIncludeScripture] = useState(false);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<AdvancedConsultResponse | null>(null);
  const [selectedCitationId, setSelectedCitationId] = useState<string | null>(null);
  const [lookupPin, setLookupPin] = useState("");
  const [lookupName, setLookupName] = useState("");
  const [lookupPhoneLast4, setLookupPhoneLast4] = useState("");
  const [lookupBusy, setLookupBusy] = useState(false);
  const [lookupStatus, setLookupStatus] = useState("");
  const [copyMode, setCopyMode] = useState<"pin_only" | "pin_with_name">("pin_with_name");
  const [loadedSurveyContext, setLoadedSurveyContext] = useState<{
    surveyId: string;
    intakePin: string;
    patientName: string;
    triageLevel: "routine" | "priority" | "emergency";
  } | null>(null);
  const [recentPins, setRecentPins] = useState<RecentPinItem[]>([]);

  async function copyLoadedContext(): Promise<void> {
    if (!loadedSurveyContext) return;
    const text =
      copyMode === "pin_only" ? loadedSurveyContext.intakePin : `${loadedSurveyContext.intakePin} / ${loadedSurveyContext.patientName}`;
    try {
      await navigator.clipboard.writeText(text);
      setLookupStatus(`복사 완료: ${text}`);
    } catch {
      setLookupStatus("복사에 실패했습니다. 브라우저 권한을 확인해 주세요.");
    }
  }

  function persistRecentPins(next: RecentPinItem[]) {
    setRecentPins(next);
    try {
      localStorage.setItem(RECENT_PIN_STORAGE_KEY, JSON.stringify(next));
    } catch {
      // ignore storage write errors
    }
  }

  function saveRecentPin(pin: string, name: string, phoneLast4: string) {
    const normalizedPin = formatIntakePinInput(pin);
    if (!normalizedPin) return;
    const next: RecentPinItem[] = [
      {
        pin: normalizedPin,
        name: name.trim(),
        phoneLast4: normalizePhoneLast4Input(phoneLast4),
        savedAt: new Date().toISOString(),
      },
      ...recentPins.filter((item) => item.pin !== normalizedPin),
    ].slice(0, 5);
    persistRecentPins(next);
  }

  useEffect(() => {
    try {
      const raw = localStorage.getItem(RECENT_PIN_STORAGE_KEY);
      if (!raw) return;
      const parsed = JSON.parse(raw) as RecentPinItem[];
      if (Array.isArray(parsed)) setRecentPins(parsed.slice(0, 5));
    } catch {
      // ignore storage parse errors
    }
  }, []);

  const selectedCitation = useMemo(() => {
    if (!result?.draft?.citations || !selectedCitationId) return null;
    return result.draft.citations.find((c) => c.citation_id === selectedCitationId) ?? null;
  }, [result?.draft?.citations, selectedCitationId]);

  const canUseAdvancedConsult = accessStatus?.success === true && accessStatus?.can_use_pro_clinical_assist === true;
  const needsUpgradeCta = accessStatus?.success === true && !canUseAdvancedConsult;

  async function checkAccessStatus() {
    const email = accessEmail.trim().toLowerCase();
    if (!email) {
      setAccessStatus({ success: false, error: "이메일을 입력해 주세요." });
      return;
    }
    setAccessBusy(true);
    try {
      const res = await fetch(`/api/member/access-status?email=${encodeURIComponent(email)}`);
      const json = (await res.json()) as MemberAccessStatusResponse;
      setAccessStatus(json);
    } catch {
      setAccessStatus({ success: false, error: "권한 정보를 가져오지 못했습니다." });
    } finally {
      setAccessBusy(false);
    }
  }

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canUseAdvancedConsult) {
      setResult({ success: false, error: "권한 확인 후 이용해 주세요." });
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
          lens_mode: lensMode,
          include_scripture: includeScripture,
          external_context: {
            business_goal: "high-value one-question consultation",
            budget_krw: 1000,
            kpi_targets: ["answer_depth", "actionability", "safety_guardrail_pass"],
            contract_constraints: ["no medical diagnosis", "no prescription replacement"],
          },
          lane_a_profile: {
            birth_instant_utc: birthInstantUtc.trim(),
            iana_tz: ianaTz.trim(),
            constitution_survey: {
              digestion_pattern: digestionPattern,
              sleep_pattern: sleepPattern,
              ...(bodyHeatPreference.trim() ? { body_heat_preference: bodyHeatPreference.trim() } : {}),
              ...(stressReactivity.trim() ? { stress_reactivity: stressReactivity.trim() } : {}),
              ...(constitutionFreeText.trim() ? { free_text: constitutionFreeText.trim() } : {}),
            },
          },
          lane_b_clinical: {
            chief_complaint: chiefComplaint,
            onset,
            severity,
            medication,
            patient_intake_context: loadedSurveyContext
              ? {
                  survey_id: loadedSurveyContext.surveyId,
                  intake_pin: loadedSurveyContext.intakePin,
                  patient_name: loadedSurveyContext.patientName,
                  triage_level: loadedSurveyContext.triageLevel,
                }
              : undefined,
            health_survey: {
              sleep_quality: sleepPattern,
              ...(redFlagNotes.trim() ? { red_flag_notes: redFlagNotes.trim() } : {}),
              ...(healthAppetite.trim() ? { appetite: healthAppetite.trim() } : {}),
              ...(healthBowelPattern.trim() ? { bowel_pattern: healthBowelPattern.trim() } : {}),
              ...(painScale0to10.trim() !== "" && !Number.isNaN(Number(painScale0to10))
                ? {
                    pain_scale_0_10: Math.min(
                      10,
                      Math.max(0, Math.round(Number(painScale0to10))),
                    ),
                  }
                : {}),
            },
          },
        }),
      });
      const json = (await res.json()) as AdvancedConsultResponse;
      setResult(json);
      if (json?.draft?.citations?.length) setSelectedCitationId(json.draft.citations[0].citation_id);
    } catch {
      setResult({ success: false, error: "진료 보조 초안 생성 중 오류가 발생했습니다." });
    } finally {
      setBusy(false);
    }
  }

  async function applyPatientPin() {
    if (!lookupPin.trim()) {
      setLookupStatus("문진 코드(PIN)를 입력해 주세요.");
      return;
    }
    if (!lookupName.trim() && lookupPhoneLast4.trim().length !== 4) {
      setLookupStatus("환자 확인용으로 이름 또는 연락처 뒤 4자리를 입력해 주세요.");
      return;
    }

    setLookupBusy(true);
    setLookupStatus("");
    try {
      const params = new URLSearchParams();
      params.set("pin", lookupPin.trim());
      if (lookupName.trim()) params.set("name", lookupName.trim());
      if (lookupPhoneLast4.trim()) params.set("phone_last4", lookupPhoneLast4.trim());

      const res = await fetch(`/api/intake/patient-presurvey?${params.toString()}`, { cache: "no-store" });
      const json = (await res.json()) as PatientPinLookupResponse;
      if (!res.ok || !json.success || !json.survey) {
        if (res.status === 429 && json.error === "too_many_lookup_attempts") {
          const retrySec = json.retry_after_seconds || 60;
          setLookupStatus(`조회 제한 중입니다. 약 ${retrySec}초 후 다시 시도해 주세요.`);
          return;
        }
        setLookupStatus(`문진 조회 실패: ${json.error || "확인되지 않은 오류"}`);
        return;
      }

      const painPart = json.survey.symptoms.pain_area;
      const goalPart = json.survey.symptoms.consultation_goal;
      const mergedComplaint = [painPart, goalPart].filter(Boolean).join(" / ");
      setChiefComplaint(mergedComplaint || painPart || "환자 문진 입력 기반");
      setOnset(json.survey.symptoms.symptom_duration || "");
      setSeverity(`${json.survey.symptoms.pain_scale_0_10}/10`);
      setDigestionPattern(json.survey.constitution_survey.digestion_pattern || "");
      setSleepPattern(json.survey.constitution_survey.sleep_pattern || "");
      setPainScale0to10(
        typeof json.survey.symptoms.pain_scale_0_10 === "number"
          ? String(json.survey.symptoms.pain_scale_0_10)
          : "",
      );
      setMedication("");
      setLoadedSurveyContext({
        surveyId: json.survey.survey_id,
        intakePin: json.survey.intake_pin,
        patientName: json.survey.patient_name,
        triageLevel: json.survey.triage_level,
      });
      setLookupStatus(
        `문진 조회 완료: ${json.survey.intake_pin} / ${json.survey.patient_name} (${triageLabel(json.survey.triage_level)}) 정보를 입력 폼에 반영했습니다.`,
      );
      saveRecentPin(json.survey.intake_pin, json.survey.patient_name, lookupPhoneLast4);
    } catch {
      setLookupStatus("문진 조회 중 네트워크 오류가 발생했습니다.");
    } finally {
      setLookupBusy(false);
    }
  }

  return (
    <section id="advanced-consult" aria-labelledby="advanced-consult-title">
      <h2 id="advanced-consult-title">진료 보조 초안 생성</h2>
      <p className="section-lead">문진 정보와 환자 PIN 정보를 바탕으로 근거 기반 진료보조 초안을 생성합니다.</p>

      <div className="card consult-access-card">
        <h3>회원 권한 확인</h3>
        <div className="consult-access-row">
          <input value={accessEmail} onChange={(e) => setAccessEmail(e.target.value)} placeholder="회원 이메일" type="email" />
          <button type="button" className="btn btn-ghost" onClick={checkAccessStatus} disabled={accessBusy}>
            {accessBusy ? "확인 중..." : "사용 권한 확인"}
          </button>
        </div>
        {accessStatus?.success ? (
          <>
            <p className="consult-access-ok">
              결제 상태: {accessStatus.payment_status} / 인증 상태: {accessStatus.verification_status} / 사용 가능:{" "}
              {canUseAdvancedConsult ? "예" : "아니오"}
            </p>
            {needsUpgradeCta ? (
              <div className="consult-access-cta">
                <a className="btn btn-primary" href="/#contact">결제/심사 진행 문의</a>
                <span>승인 완료 후 CDSS 초안 생성 기능을 사용할 수 있습니다.</span>
              </div>
            ) : null}
          </>
        ) : accessStatus ? (
          <p className="consult-error">권한 확인 오류: {accessStatus.error || "확인되지 않은 오류"}</p>
        ) : null}
      </div>

      <div className="card consult-access-card">
        <h3>환자 PIN 불러오기 (접수 코드)</h3>
        <div className="section-cta" style={{ marginTop: "0", marginBottom: "0.65rem" }}>
          <button
            type="button"
            className={`btn ${copyMode === "pin_with_name" ? "btn-primary" : "btn-ghost"}`}
            onClick={() => setCopyMode("pin_with_name")}
          >
            복사 형식: PIN+이름
          </button>
          <button
            type="button"
            className={`btn ${copyMode === "pin_only" ? "btn-primary" : "btn-ghost"}`}
            onClick={() => setCopyMode("pin_only")}
          >
            복사 형식: PIN만
          </button>
        </div>
        <div className="consult-access-row">
          <input
            value={lookupPin}
            onChange={(e) => setLookupPin(formatIntakePinInput(e.target.value))}
            onPaste={(e) => {
              const pasted = e.clipboardData.getData("text");
              if (!pasted) return;
              e.preventDefault();
              setLookupPin(formatIntakePinInput(pasted));
            }}
            placeholder="예: A7B-92K"
            autoCapitalize="characters"
            spellCheck={false}
          />
          <input
            value={lookupName}
            onChange={(e) => setLookupName(normalizePatientNameInput(e.target.value))}
            onBlur={(e) => setLookupName(e.target.value.trim())}
            placeholder="환자 이름 (선택)"
          />
          <input
            value={lookupPhoneLast4}
            onChange={(e) => setLookupPhoneLast4(normalizePhoneLast4Input(e.target.value))}
            placeholder="전화 뒤 4자리 (선택)"
            maxLength={4}
            inputMode="numeric"
          />
          <button type="button" className="btn btn-ghost" onClick={applyPatientPin} disabled={lookupBusy}>
            {lookupBusy ? "조회 중..." : "문진 불러오기"}
          </button>
        </div>
        <p className="workspace-muted">
          PIN 단독 조회를 막기 위해 이름 또는 연락처 뒤 4자리 확인값을 함께 받습니다.
        </p>
        {lookupStatus ? <p className="consult-access-ok">{lookupStatus}</p> : null}
        {recentPins.length > 0 ? (
          <div className="section-cta" style={{ marginTop: "0.5rem" }}>
            {recentPins.map((item) => (
              <button
                key={item.pin}
                type="button"
                className="btn btn-ghost"
                onClick={() => {
                  setLookupPin(item.pin);
                  setLookupName(item.name);
                  setLookupPhoneLast4(item.phoneLast4);
                  void applyPatientPin();
                }}
              >
                최근 {item.pin}
                {item.name ? ` / ${item.name}` : ""}
              </button>
            ))}
          </div>
        ) : null}
        {loadedSurveyContext ? (
          <div className="consult-source-chip">
            연결됨: {loadedSurveyContext.intakePin} / {loadedSurveyContext.patientName}{" "}
            <span className={triageBadgeClass(loadedSurveyContext.triageLevel)}>{triageLabel(loadedSurveyContext.triageLevel)}</span>
            <button type="button" className="btn btn-ghost" style={{ marginLeft: "0.5rem", padding: "0.2rem 0.45rem" }} onClick={copyLoadedContext}>
              PIN/이름 복사
            </button>
          </div>
        ) : null}
      </div>

      {activeView === "assist" ? (
      <form className="consult-form" onSubmit={onSubmit}>
        <label>의료진 계정 ID<input value={actorId} onChange={(e) => setActorId(e.target.value)} required /></label>
        <label>
          출생 시각 (UTC, ISO 형식)
          <input
            value={birthInstantUtc}
            onChange={(e) => setBirthInstantUtc(e.target.value)}
            placeholder="1990-01-01T00:00:00Z"
            required
            autoComplete="bday-time"
          />
        </label>
        <label>
          시간대 (IANA 표준)
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
        <label>주호소<input value={chiefComplaint} onChange={(e) => setChiefComplaint(e.target.value)} required /></label>
        <label>발현 시점/기간<input value={onset} onChange={(e) => setOnset(e.target.value)} required /></label>
        <label>중증도(주관 척도)<input value={severity} onChange={(e) => setSeverity(e.target.value)} required /></label>
        <label>현재 복약 정보<input value={medication} onChange={(e) => setMedication(e.target.value)} /></label>
        <label>소화 패턴 (레인 A 설문)<input value={digestionPattern} onChange={(e) => setDigestionPattern(e.target.value)} /></label>
        <label>수면 패턴 (레인 A 설문)<input value={sleepPattern} onChange={(e) => setSleepPattern(e.target.value)} /></label>
        <label>
          한열·체온 느낌 (선택)
          <input
            value={bodyHeatPreference}
            onChange={(e) => setBodyHeatPreference(e.target.value)}
            placeholder="예: 더위 탐, 추위 탐"
          />
        </label>
        <label>
          스트레스 반응 (선택)
          <input
            value={stressReactivity}
            onChange={(e) => setStressReactivity(e.target.value)}
            placeholder="예: 긴장 시 소화 불편"
          />
        </label>
        <label>
          설문 기타 메모 (선택)
          <textarea
            value={constitutionFreeText}
            onChange={(e) => setConstitutionFreeText(e.target.value)}
            placeholder="체질·생활 관련 추가 설명"
            rows={2}
          />
        </label>
        <label>
          통증 척도 0–10 (선택)
          <input
            value={painScale0to10}
            onChange={(e) => setPainScale0to10(e.target.value.replace(/\D/g, "").slice(0, 2))}
            placeholder="예: 7"
            inputMode="numeric"
          />
        </label>
        <label>
          레드플래그·주의 소견 (선택)
          <textarea
            value={redFlagNotes}
            onChange={(e) => setRedFlagNotes(e.target.value)}
            placeholder="응급·악화 신호, 복합 증상 등"
            rows={3}
          />
        </label>
        <label>
          식욕 (선택)
          <input value={healthAppetite} onChange={(e) => setHealthAppetite(e.target.value)} placeholder="예: 저하" />
        </label>
        <label>
          배변 (선택)
          <input value={healthBowelPattern} onChange={(e) => setHealthBowelPattern(e.target.value)} placeholder="예: 변비 경향" />
        </label>
        <label>
          분석 모드
          <select value={lensMode} onChange={(e) => setLensMode(e.target.value as "neutral" | "integrated" | "compare")}>
            <option value="neutral">기본(중립)</option>
            <option value="integrated">통합(사상+명리)</option>
            <option value="compare">비교(사상/명리)</option>
          </select>
        </label>
        <label style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <input type="checkbox" checked={includeScripture} onChange={(e) => setIncludeScripture(e.target.checked)} />
          Logos 보조 맥락 포함 (선택)
        </label>
        <button type="submit" className="btn btn-primary" disabled={busy || !canUseAdvancedConsult}>
          {busy ? "생성 중..." : "진료 보조 초안 생성"}
        </button>
      </form>
      ) : null}

      {activeView === "assist" && result ? (
        <div className="consult-result">
          {!result.success ? (
            <p className="consult-error">오류: {result.error || "확인되지 않은 오류"}</p>
          ) : (
            <>
              {result.draft?.generation?.llm_used === true ? (
                <p className="consult-source-chip" role="status" style={{ marginBottom: "0.75rem" }}>
                  생성형 CDSS 초안 적용 (이번 응답에 모델 추론 포함)
                </p>
              ) : null}
              {result.draft?.generation?.llm_used === false ? (
                <div className="notice-box" role="status">
                  <strong>규칙 기반 초안 표시 중</strong>
                  <span style={{ display: "block", marginTop: "0.35rem", fontWeight: 400 }}>
                    {cdssTemplateHint(result.draft.generation.reason)}{" "}
                    <span className="consult-source-chip" style={{ display: "inline", marginLeft: "0.35rem" }}>
                      사유: {result.draft.generation.reason ?? "unknown"}
                    </span>
                  </span>
                </div>
              ) : null}
              <p className="consult-summary">{result.draft?.clinical_summary}</p>
              <div className="grid-3">
                <article className="card"><h3>체질 후보군</h3><p>{result.draft?.profile_summary.sasang_candidate}</p></article>
                <article className="card">
                  <h3>만세력 참고 정보</h3>
                  <p>{result.draft?.profile_summary.saju_reference}</p>
                  <p className="consult-source-chip">출처: {result.draft?.profile_summary.saju_source === "live" ? "실시간 API" : "대체 경로"}</p>
                </article>
                <article className="card">
                  <h3>안전 가드</h3>
                  <p>분리 해석: {result.guardrail?.lane_separation ? "적용" : "미적용"} / 근거 강제: {result.guardrail?.citation_enforced ? "적용" : "미적용"}</p>
                  <p>분석 모드: {result.draft?.lens_mode || "neutral"} / Logos 보조 맥락: {result.draft?.include_scripture ? "적용" : "미적용"}</p>
                  <p>
                    근거 주입: 전체 {result.evidence_meta?.citation_count ?? result.draft?.citations?.length ?? 0}건 / 문헌 스냅샷{" "}
                    {result.evidence_meta?.literature_injected_count ?? 0}건
                  </p>
                </article>
              </div>

              <div className="consult-reasoning">
                <h3>진료보조 해석 초안</h3>
                <p>{result.draft?.reasoning.syndrome_hypothesis}</p>
                <p>{result.draft?.reasoning.care_direction}</p>
                <p>{result.draft?.reasoning.caution}</p>
              </div>

              <div className="consult-citations">
                <h3>근거 데이터</h3>
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
              {result.draft?.collaboration?.enabled ? (
                <div className="consult-reasoning">
                  <h3>4-AI 합의 결과</h3>
                  <p>{result.draft.collaboration.final_consensus}</p>
                  <p>
                    mode={result.draft.collaboration.mode} / gate_status={result.draft.collaboration.gate_status} /
                    quality={result.draft.collaboration.gate_scores.quality} /
                    cost={result.draft.collaboration.gate_scores.cost} /
                    safety={result.draft.collaboration.gate_scores.safety}
                  </p>
                  {result.draft.collaboration.gate_reasons.length ? (
                    <p>gate_reasons: {result.draft.collaboration.gate_reasons.join(", ")}</p>
                  ) : null}
                  {result.draft.collaboration.agreement_points.length ? (
                    <ul>
                      {result.draft.collaboration.agreement_points.map((point) => (
                        <li key={`agree-${point}`}>합의: {point}</li>
                      ))}
                    </ul>
                  ) : null}
                  {result.draft.collaboration.conflict_points.length ? (
                    <ul>
                      {result.draft.collaboration.conflict_points.map((point) => (
                        <li key={`conflict-${point}`}>충돌: {point}</li>
                      ))}
                    </ul>
                  ) : null}
                  {result.draft.collaboration.priority_actions_top3.length ? (
                    <>
                      <p><strong>실행 우선순위 TOP3</strong></p>
                      <ul>
                        {result.draft.collaboration.priority_actions_top3.map((point) => (
                          <li key={`priority-${point}`}>{point}</li>
                        ))}
                      </ul>
                    </>
                  ) : null}
                  {result.draft.collaboration.do_not_do_top3.length ? (
                    <>
                      <p><strong>금지 TOP3</strong></p>
                      <ul>
                        {result.draft.collaboration.do_not_do_top3.map((point) => (
                          <li key={`deny-${point}`}>{point}</li>
                        ))}
                      </ul>
                    </>
                  ) : null}
                  {result.draft.collaboration.plan_30d.length ? (
                    <>
                      <p><strong>30일 플랜</strong></p>
                      <ul>
                        {result.draft.collaboration.plan_30d.map((step) => (
                          <li key={`plan-${step}`}>{step}</li>
                        ))}
                      </ul>
                    </>
                  ) : null}
                  <div className="grid-3">
                    {result.draft.collaboration.opinions.map((op) => (
                      <article key={`op-${op.agent_id}`} className="card">
                        <h3>{op.agent_id}</h3>
                        <p>{op.stance}</p>
                        <p className="consult-source-chip">
                          <span className={`consult-confidence-badge is-${confidenceTier(op.confidence)}`}>
                            {confidenceTier(op.confidence).toUpperCase()}
                          </span>{" "}
                          confidence: {op.confidence} (level {confidenceLevel(op.confidence)})
                        </p>
                      </article>
                    ))}
                  </div>
                </div>
              ) : null}

              {result.draft?.fact_lock ? (
                <article className="card">
                  <h3>Fact-Lock</h3>
                  <p className="consult-source-chip">level: {result.draft.fact_lock.confidence_level}</p>
                  <p>evidence: {result.draft.fact_lock.evidence_path}</p>
                  <p>validated_at: {result.draft.fact_lock.validated_at}</p>
                  {result.draft.fact_lock.note ? <p>note: {result.draft.fact_lock.note}</p> : null}
                </article>
              ) : null}

              <p className="consult-notice">{result.draft?.non_medical_notice}</p>
            </>
          )}
        </div>
      ) : null}
    </section>
  );
}
