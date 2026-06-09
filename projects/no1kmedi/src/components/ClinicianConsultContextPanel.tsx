"use client";

import { useEffect, useState } from "react";
import type { ClinicianThreadContext } from "@/lib/clinician-chat-types";
import {
  formatIntakePinInput,
  formatPatientPinLookupError,
  normalizePatientNameInput,
  normalizePhoneLast4Input,
  triageBadgeClass,
  triageLabel,
} from "@/lib/clinician-intake-utils";
import type { ClinicianSurveySsotPayload } from "@/lib/clinician-survey-ssot-v1";
import {
  applyPatientPinSurveyToClinicianState,
  type PatientPinLookupResponse,
} from "@/lib/patient-intake-pin-lookup-v1";
import { EnoMultimodalIntakePreviewCard } from "@/components/EnoMultimodalIntakePreviewCard";

const RECENT_PIN_STORAGE_KEY = "advanced_consult_recent_pins_v1";

type RecentPinItem = { pin: string; name: string; phoneLast4: string; savedAt: string };

type ClinicianConsultContextPanelProps = {
  compact?: boolean;
  context: ClinicianThreadContext;
  onContextChange: (patch: Partial<ClinicianThreadContext>) => void;
  accessEmail: string;
  onAccessEmailChange: (v: string) => void;
  accessBusy: boolean;
  accessStatus: { success: boolean; error?: string; can_use_pro_clinical_assist?: boolean; payment_status?: string; verification_status?: string } | null;
  onCheckAccess: () => void;
};

export function ClinicianConsultContextPanel({
  compact = false,
  context,
  onContextChange,
  accessEmail,
  onAccessEmailChange,
  accessBusy,
  accessStatus,
  onCheckAccess,
}: ClinicianConsultContextPanelProps) {
  const [lookupPin, setLookupPin] = useState("");
  const [lookupName, setLookupName] = useState("");
  const [lookupPhoneLast4, setLookupPhoneLast4] = useState("");
  const [lookupBusy, setLookupBusy] = useState(false);
  const [lookupStatus, setLookupStatus] = useState("");
  const [recentPins, setRecentPins] = useState<RecentPinItem[]>([]);
  const [surveySsot, setSurveySsot] = useState<ClinicianSurveySsotPayload | null>(null);
  const [lifestylePrint, setLifestylePrint] = useState<{
    print_form_path: string;
    print_form_label_ko: string;
  } | null>(null);

  const canUseAdvancedConsult = accessStatus?.success === true && accessStatus?.can_use_pro_clinical_assist === true;

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const res = await fetch("/api/clinician/constitution-survey-ssot", { cache: "no-store" });
        const json = (await res.json()) as ClinicianSurveySsotPayload;
        if (!cancelled && json.success) setSurveySsot(json);
      } catch {
        /* optional metadata */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const res = await fetch("/api/clinician/lifestyle-management-ssot", { cache: "no-store" });
        const json = (await res.json()) as {
          success?: boolean;
          physician_lane?: { print_form_path?: string; print_form_label_ko?: string };
        };
        if (
          !cancelled &&
          json.success &&
          json.physician_lane?.print_form_path &&
          json.physician_lane?.print_form_label_ko
        ) {
          setLifestylePrint({
            print_form_path: json.physician_lane.print_form_path,
            print_form_label_ko: json.physician_lane.print_form_label_ko,
          });
        }
      } catch {
        /* optional metadata */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(RECENT_PIN_STORAGE_KEY);
      if (!raw) return;
      const parsed = JSON.parse(raw) as RecentPinItem[];
      if (Array.isArray(parsed)) setRecentPins(parsed.slice(0, 5));
    } catch {
      // ignore
    }
  }, []);

  function patch(p: Partial<ClinicianThreadContext>) {
    onContextChange(p);
  }

  async function applyPatientPin() {
    if (!lookupPin.trim()) {
      setLookupStatus("PIN을 입력해 주세요.");
      return;
    }
    if (!lookupName.trim() && lookupPhoneLast4.trim().length !== 4) {
      setLookupStatus(formatPatientPinLookupError("second_factor_required"));
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
        setLookupStatus(formatPatientPinLookupError(json.error));
        return;
      }
      const s = json.survey;
      patch(applyPatientPinSurveyToClinicianState(s, context));
      const sajuHint = s.lane_a_profile?.saju_label ? ` · 사주 ${s.lane_a_profile.saju_label}` : "";
      setLookupStatus(`반영: ${s.intake_pin} / ${s.patient_name}${sajuHint}`);
    } catch {
      setLookupStatus("네트워크 오류");
    } finally {
      setLookupBusy(false);
    }
  }

  return (
    <div className="workspace-panel workspace-scroll-inner">
      <h2 className="workspace-panel-title">환자·설정</h2>
      <p className="workspace-muted">출생·문진·렌즈는 여기서만 편집합니다. 일상 사용은 「대화」 화면 중심입니다.</p>

      <div className="card consult-access-card">
        <h3>회원 권한</h3>
        <div className="consult-access-row">
          <input value={accessEmail} onChange={(e) => onAccessEmailChange(e.target.value)} placeholder="회원 이메일" type="email" />
          <button type="button" className="btn btn-ghost" onClick={onCheckAccess} disabled={accessBusy}>
            {accessBusy ? "확인 중…" : "권한 확인"}
          </button>
        </div>
        {accessStatus?.success ? (
          <p className="consult-access-ok">
            사용 가능: {canUseAdvancedConsult ? "예" : "아니오"} · {accessStatus.payment_status} / {accessStatus.verification_status}
          </p>
        ) : accessStatus ? (
          <p className="consult-error">{accessStatus.error}</p>
        ) : null}
      </div>

      {surveySsot ? (
        <div className="card consult-access-card">
          <h3>설문 레인 (SSOT)</h3>
          <p className="workspace-muted">{surveySsot.disclaimer}</p>
          <p className="consult-access-ok">
            <strong>원내 우선:</strong>{" "}
            <a href={surveySsot.physician_lane.print_form_path} target="_blank" rel="noopener noreferrer">
              {surveySsot.physician_lane.print_form_label_ko}
            </a>
            {" · "}
            대기실 인쇄 → 환자 작성 → 차트 보관 → 한의사 확정 체질 기록
          </p>
          <p className="workspace-muted">
            보조: 문진 PIN + 앱 내 {surveySsot.physician_lane.constitution_questions_in_app}문항 · pack{" "}
            {surveySsot.pack_id ?? "—"}
            {surveySsot.item_count != null ? ` (${surveySsot.item_count} bank items)` : ""}
          </p>
          <p className="workspace-muted">
            소비자 레인(별도):{" "}
            <a href={surveySsot.consumer_lane.survey_url} target="_blank" rel="noopener noreferrer">
              {surveySsot.consumer_lane.label}
            </a>
            {" — "}
            {surveySsot.consumer_lane.sublabel}
          </p>
        </div>
      ) : null}

      {lifestylePrint ? (
        <div className="card consult-access-card">
          <h3>생활관리 · 임신 준비</h3>
          <p className="workspace-muted">
            유산·회복·소음인 등 — 식이·운동·퍼스널컬러·<strong>[HYPO] 임신 시기(에너지)</strong> 원내 교부.
            산부인과·Lab가 SSOT.
          </p>
          <p className="consult-access-ok">
            <a href={lifestylePrint.print_form_path} target="_blank" rel="noopener noreferrer">
              {lifestylePrint.print_form_label_ko}
            </a>
          </p>
        </div>
      ) : null}

      <EnoMultimodalIntakePreviewCard context={context} onContextChange={patch} />

      <div className="card consult-access-card">
        <h3>문진 PIN</h3>
        <p className="workspace-muted">PIN과 함께 <strong>환자 이름</strong> 또는 <strong>휴대폰 뒤 4자리</strong>가 필요합니다.</p>
        <div className="consult-access-row">
          <input
            value={lookupPin}
            onChange={(e) => setLookupPin(formatIntakePinInput(e.target.value))}
            placeholder="예: H5N-8RL"
            autoCapitalize="characters"
            spellCheck={false}
          />
          <input
            value={lookupName}
            onChange={(e) => setLookupName(normalizePatientNameInput(e.target.value))}
            onBlur={(e) => setLookupName(e.target.value.trim())}
            placeholder="환자 이름"
          />
          <input
            value={lookupPhoneLast4}
            onChange={(e) => setLookupPhoneLast4(normalizePhoneLast4Input(e.target.value))}
            placeholder="전화 뒤 4자리"
            maxLength={4}
            inputMode="numeric"
          />
          <button type="button" className="btn btn-ghost" onClick={() => void applyPatientPin()} disabled={lookupBusy}>
            {lookupBusy ? "조회 중…" : "불러오기"}
          </button>
        </div>
        {lookupStatus ? (
          <p className={lookupStatus.startsWith("반영:") ? "consult-access-ok" : "consult-error"}>{lookupStatus}</p>
        ) : null}
        {context.loadedSurveyContext ? (
          <p className="consult-source-chip">
            {context.loadedSurveyContext.intakePin} / {context.loadedSurveyContext.patientName}{" "}
            <span className={triageBadgeClass(context.loadedSurveyContext.triageLevel)}>
              {triageLabel(context.loadedSurveyContext.triageLevel)}
            </span>
          </p>
        ) : null}
      </div>

      <form
        className={`consult-form${compact ? " consult-form--compact" : ""}`}
        onSubmit={(e) => e.preventDefault()}
      >
        <label>
          출생 UTC
          <input value={context.birthInstantUtc} onChange={(e) => patch({ birthInstantUtc: e.target.value })} />
        </label>
        <label>
          IANA TZ
          <input value={context.ianaTz} onChange={(e) => patch({ ianaTz: e.target.value })} />
        </label>
        <label>
          주호소
          <input value={context.chiefComplaint} onChange={(e) => patch({ chiefComplaint: e.target.value })} />
        </label>
        <label>
          발현
          <input value={context.onset} onChange={(e) => patch({ onset: e.target.value })} />
        </label>
        <label>
          중증도
          <input value={context.severity} onChange={(e) => patch({ severity: e.target.value })} />
        </label>
        <label>
          분석 모드
          <select
            value={context.lensMode}
            onChange={(e) => patch({ lensMode: e.target.value as ClinicianThreadContext["lensMode"] })}
          >
            <option value="neutral">중립</option>
            <option value="integrated">통합</option>
            <option value="compare">비교</option>
          </select>
        </label>
        <label style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <input
            type="checkbox"
            checked={context.includeScripture}
            onChange={(e) => patch({ includeScripture: e.target.checked })}
          />
          Logos 보조
        </label>
      </form>
    </div>
  );
}
