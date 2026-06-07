"use client";

import { useMemo, useState } from "react";
import {
  CLINIC_INTAKE_DIGESTION_CHIPS,
  CLINIC_INTAKE_DURATION_CHIPS,
  CLINIC_INTAKE_FATIGUE_CHIPS,
  CLINIC_INTAKE_HEAT_COLD_CHIPS,
  CLINIC_INTAKE_SLEEP_CHIPS,
  CLINIC_INTAKE_SYMPTOM_CHIPS,
  CLINIC_INTAKE_WIZARD_STEPS,
  painScaleLabel,
} from "@/lib/clinic-intake-mobile-copy-v1";
import { buildClinicIntakePatientPinSmsBody } from "@/lib/clinic-intake-staff-link-v1";

type SubmitResponse = {
  success: boolean;
  survey_id?: string;
  intake_pin?: string;
  triage_level?: "routine" | "priority" | "emergency";
  error?: string;
  emergency_notice?: string;
};

function ChipGrid({
  options,
  value,
  onChange,
}: {
  options: { id: string; label: string; value: string }[];
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="clinic-intake-chip-grid" role="group">
      {options.map((opt) => (
        <button
          key={opt.id}
          type="button"
          className={`clinic-intake-chip${value === opt.value ? " is-selected" : ""}`}
          aria-pressed={value === opt.value}
          onClick={() => onChange(opt.value)}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}

export function ClinicIntakeMobileWizard() {
  const [step, setStep] = useState(0);
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [birthdate, setBirthdate] = useState("");
  const [birthTimeUnknown, setBirthTimeUnknown] = useState(true);
  const [birthTime, setBirthTime] = useState("");
  const [symptomChip, setSymptomChip] = useState("");
  const [symptomCustom, setSymptomCustom] = useState("");
  const [duration, setDuration] = useState("");
  const [painScale, setPainScale] = useState(5);
  const [sleepPattern, setSleepPattern] = useState("");
  const [digestionPattern, setDigestionPattern] = useState("");
  const [heatCold, setHeatCold] = useState("비슷함");
  const [fatigue, setFatigue] = useState("중간");
  const [goal, setGoal] = useState("");
  const [showOptional, setShowOptional] = useState(false);
  const [redFlags, setRedFlags] = useState({
    chestPain: false,
    paralysisOrSpeech: false,
    highFeverOrBleeding: false,
  });
  const [consentPrivacy, setConsentPrivacy] = useState(false);
  const [consentMedical, setConsentMedical] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [donePin, setDonePin] = useState("");
  const [doneTriage, setDoneTriage] = useState<"routine" | "priority" | "emergency">("routine");

  const stepMeta = CLINIC_INTAKE_WIZARD_STEPS[step];
  const progressPct = Math.round(((step + 1) / CLINIC_INTAKE_WIZARD_STEPS.length) * 100);

  const mainSymptom = useMemo(() => {
    if (symptomChip === "__custom__") return symptomCustom.trim();
    return symptomChip.trim();
  }, [symptomChip, symptomCustom]);

  const hasRedFlag = Object.values(redFlags).some(Boolean);

  function validateStep(): string | null {
    if (step === 0) {
      if (!name.trim()) return "이름을 입력해 주세요.";
      if (!phone.trim()) return "연락처를 입력해 주세요.";
      if (!birthdate.trim()) return "생년월일을 선택해 주세요.";
      return null;
    }
    if (step === 1) {
      if (!mainSymptom) return "불편한 부위를 선택하거나 입력해 주세요.";
      if (!duration) return "증상 기간을 선택해 주세요.";
      return null;
    }
    if (step === 2) {
      if (!sleepPattern) return "수면 상태를 선택해 주세요.";
      if (!digestionPattern) return "소화 상태를 선택해 주세요.";
      return null;
    }
    if (step === 3) {
      if (!consentPrivacy || !consentMedical) return "동의 항목을 모두 체크해 주세요.";
      return null;
    }
    return null;
  }

  async function submitIntake() {
    const stepErr = validateStep();
    if (stepErr) {
      setError(stepErr);
      return;
    }
    setBusy(true);
    setError("");
    try {
      const res = await fetch("/api/intake/clinic-intake-v1", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          schema_version: "clinic_intake_v1",
          patient: { name: name.trim(), phone: phone.trim(), birthdate: birthdate.trim(), visit_type: "초진" },
          consent: {
            sensitive_collection: consentPrivacy,
            kakao_transfer: consentMedical,
            non_diagnostic_notice: true,
          },
          red_flags: {
            chestPain: redFlags.chestPain,
            neuroDeficit: redFlags.paralysisOrSpeech,
            highFever: redFlags.highFeverOrBleeding,
            pregnancyOrMajorCondition: false,
          },
          symptom: {
            main_symptom: mainSymptom,
            duration,
            severity_nrs: painScale,
            free_text: goal.trim(),
          },
          health_core: {
            sleep_quality: sleepPattern,
            bowel_pattern: digestionPattern,
            appetite: "미입력",
            stress_level: 5,
            medications: "",
          },
          constitution: {
            body_frame: "균형형",
            heat_cold_sensitivity: heatCold,
            temperament: "상황에 따라 다름",
            digestion_pattern: digestionPattern,
            fatigue_recovery: fatigue,
          },
          clinic_preference: {},
          optional_profile: {
            birth_time: birthTimeUnknown ? undefined : birthTime.trim() || undefined,
            birth_time_known: !birthTimeUnknown && Boolean(birthTime.trim()),
          },
          submitted_at_utc: new Date().toISOString(),
        }),
      });
      const json = (await res.json()) as SubmitResponse;
      if (!res.ok || !json.success) {
        setError(json.error || "제출에 실패했습니다.");
        return;
      }
      setDonePin(json.intake_pin || "");
      setDoneTriage(json.triage_level || "routine");
      setStep(CLINIC_INTAKE_WIZARD_STEPS.length);
    } catch {
      setError("네트워크 오류입니다. 잠시 후 다시 시도해 주세요.");
    } finally {
      setBusy(false);
    }
  }

  function goNext() {
    const stepErr = validateStep();
    if (stepErr) {
      setError(stepErr);
      return;
    }
    setError("");
    if (step === 3) {
      void submitIntake();
      return;
    }
    setStep((s) => Math.min(s + 1, CLINIC_INTAKE_WIZARD_STEPS.length - 1));
  }

  function goBack() {
    setError("");
    setStep((s) => Math.max(0, s - 1));
  }

  function sharePinSms() {
    if (!donePin) return;
    const body = encodeURIComponent(buildClinicIntakePatientPinSmsBody({ intakePin: donePin }));
    window.location.href = `sms:?&body=${body}`;
  }

  if (step >= CLINIC_INTAKE_WIZARD_STEPS.length) {
    return (
      <section className="clinic-intake-mobile" aria-live="polite">
        <div className="clinic-intake-done">
          <p className="clinic-intake-done-kicker">접수 완료</p>
          <h2>문진 코드</h2>
          <p className="clinic-intake-pin-display">{donePin}</p>
          <p className="clinic-intake-done-hint">
            {doneTriage === "emergency"
              ? "응급 신호가 있습니다. 119·응급실을 우선 이용해 주세요."
              : "접수 데스크나 진료실에 이 코드를 알려 주세요."}
          </p>
          <div className="clinic-intake-sticky-actions is-static">
            <button type="button" className="btn btn-primary clinic-intake-btn-wide" onClick={sharePinSms}>
              문자로 코드 보내기
            </button>
          </div>
          <p className="clinic-intake-disclaimer">진단·처방이 아닌 접수 보조입니다. 최종 판단은 한의사가 합니다.</p>
        </div>
      </section>
    );
  }

  return (
    <section className="clinic-intake-mobile">
      <header className="clinic-intake-header">
        <p className="clinic-intake-kicker">사전 문진 · 약 2분</p>
        <h2 id="clinic-intake-step-title">{stepMeta.title}</h2>
        <p className="clinic-intake-hint">{stepMeta.hint}</p>
        <div className="clinic-intake-progress" aria-hidden="true">
          <div className="clinic-intake-progress-bar" style={{ width: `${progressPct}%` }} />
        </div>
        <p className="clinic-intake-step-count">
          {step + 1} / {CLINIC_INTAKE_WIZARD_STEPS.length}
        </p>
      </header>

      {hasRedFlag ? (
        <p className="patient-survey-emergency">응급 신호가 선택되었습니다. 119·응급실을 우선 이용해 주세요.</p>
      ) : null}

      <div className="clinic-intake-body">
        {step === 0 ? (
          <div className="clinic-intake-fields">
            <label className="clinic-intake-field">
              <span>이름</span>
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                autoComplete="name"
                enterKeyHint="next"
                required
              />
            </label>
            <label className="clinic-intake-field">
              <span>휴대폰 번호</span>
              <input
                type="tel"
                inputMode="tel"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="010-1234-5678"
                autoComplete="tel"
                required
              />
            </label>
            <label className="clinic-intake-field">
              <span>생년월일</span>
              <input type="date" value={birthdate} onChange={(e) => setBirthdate(e.target.value)} required />
            </label>
            <details className="clinic-intake-details">
              <summary>출생 시간 (선택 · 몰라도 됩니다)</summary>
              <label className="clinic-intake-check">
                <input
                  type="checkbox"
                  checked={birthTimeUnknown}
                  onChange={(e) => {
                    setBirthTimeUnknown(e.target.checked);
                    if (e.target.checked) setBirthTime("");
                  }}
                />
                출생 시간을 모릅니다
              </label>
              {!birthTimeUnknown ? (
                <label className="clinic-intake-field">
                  <span>출생 시간</span>
                  <input type="time" value={birthTime} onChange={(e) => setBirthTime(e.target.value)} />
                </label>
              ) : null}
            </details>
          </div>
        ) : null}

        {step === 1 ? (
          <div className="clinic-intake-fields">
            <p className="clinic-intake-q">어디가 가장 불편한가요?</p>
            <ChipGrid options={CLINIC_INTAKE_SYMPTOM_CHIPS} value={symptomChip} onChange={setSymptomChip} />
            {symptomChip === "__custom__" ? (
              <label className="clinic-intake-field">
                <span>직접 입력</span>
                <input
                  value={symptomCustom}
                  onChange={(e) => setSymptomCustom(e.target.value)}
                  placeholder="예: 오른쪽 무릎 통증"
                />
              </label>
            ) : null}
            <p className="clinic-intake-q">얼마나 불편한가요?</p>
            <div className="clinic-intake-slider-wrap">
              <input
                type="range"
                min={0}
                max={10}
                value={painScale}
                onChange={(e) => setPainScale(Number(e.target.value))}
                className="clinic-intake-slider"
                aria-valuetext={`${painScale}점 ${painScaleLabel(painScale)}`}
              />
              <p className="clinic-intake-slider-label">
                <strong>{painScale}점</strong> · {painScaleLabel(painScale)}
              </p>
            </div>
            <p className="clinic-intake-q">언제부터 그랬나요?</p>
            <ChipGrid options={CLINIC_INTAKE_DURATION_CHIPS} value={duration} onChange={setDuration} />
          </div>
        ) : null}

        {step === 2 ? (
          <div className="clinic-intake-fields">
            <p className="clinic-intake-q">요즘 잠은 어떤가요?</p>
            <ChipGrid options={CLINIC_INTAKE_SLEEP_CHIPS} value={sleepPattern} onChange={setSleepPattern} />
            <p className="clinic-intake-q">식사·소화는 어떤가요?</p>
            <ChipGrid options={CLINIC_INTAKE_DIGESTION_CHIPS} value={digestionPattern} onChange={setDigestionPattern} />
            <p className="clinic-intake-q">더위·추위 중 어떤 쪽이 더 힘든가요?</p>
            <ChipGrid options={CLINIC_INTAKE_HEAT_COLD_CHIPS} value={heatCold} onChange={setHeatCold} />
            <p className="clinic-intake-q">쉬면 피로가 금방 풀리나요?</p>
            <ChipGrid options={CLINIC_INTAKE_FATIGUE_CHIPS} value={fatigue} onChange={setFatigue} />
            <button type="button" className="clinic-intake-link-btn" onClick={() => setShowOptional((v) => !v)}>
              {showOptional ? "추가 입력 닫기" : "하고 싶은 말 더 적기 (선택)"}
            </button>
            {showOptional ? (
              <label className="clinic-intake-field">
                <span>한의사에게 전하고 싶은 말</span>
                <textarea
                  value={goal}
                  onChange={(e) => setGoal(e.target.value)}
                  rows={3}
                  placeholder="예: 야간에 통증이 심해져요"
                />
              </label>
            ) : null}
          </div>
        ) : null}

        {step === 3 ? (
          <div className="clinic-intake-fields">
            <fieldset className="clinic-intake-redflags">
              <legend>아래에 해당하면 체크해 주세요</legend>
              <label className="clinic-intake-check">
                <input
                  type="checkbox"
                  checked={redFlags.chestPain}
                  onChange={(e) => setRedFlags((p) => ({ ...p, chestPain: e.target.checked }))}
                />
                갑작스러운 흉통
              </label>
              <label className="clinic-intake-check">
                <input
                  type="checkbox"
                  checked={redFlags.paralysisOrSpeech}
                  onChange={(e) => setRedFlags((p) => ({ ...p, paralysisOrSpeech: e.target.checked }))}
                />
                한쪽 마비·말이 어눌함
              </label>
              <label className="clinic-intake-check">
                <input
                  type="checkbox"
                  checked={redFlags.highFeverOrBleeding}
                  onChange={(e) => setRedFlags((p) => ({ ...p, highFeverOrBleeding: e.target.checked }))}
                />
                고열·출혈
              </label>
            </fieldset>
            <div className="clinic-intake-consent">
              <label className="clinic-intake-check">
                <input type="checkbox" checked={consentPrivacy} onChange={(e) => setConsentPrivacy(e.target.checked)} />
                개인정보 수집·이용에 동의합니다
              </label>
              <label className="clinic-intake-check">
                <input type="checkbox" checked={consentMedical} onChange={(e) => setConsentMedical(e.target.checked)} />
                문진(의료) 정보 수집·이용에 동의합니다
              </label>
            </div>
            <p className="clinic-intake-disclaimer">본 문진은 진단·처방이 아니며, 한의사가 최종 판단합니다.</p>
          </div>
        ) : null}
      </div>

      {error ? <p className="consult-error clinic-intake-error">{error}</p> : null}

      <div className="clinic-intake-sticky-actions">
        {step > 0 ? (
          <button type="button" className="btn btn-ghost clinic-intake-btn-back" onClick={goBack} disabled={busy}>
            이전
          </button>
        ) : (
          <span />
        )}
        <button type="button" className="btn btn-primary clinic-intake-btn-next" onClick={goNext} disabled={busy}>
          {busy ? "제출 중…" : step === 3 ? "제출하기" : "다음"}
        </button>
      </div>
    </section>
  );
}
