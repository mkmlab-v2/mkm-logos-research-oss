/**
 * @MKM12-METADATA
 * Type: UI
 * Vector: {S:0.74, L:0.66, K:0.82, M:0.52}
 * Balance: 91
 * Purpose: Collect patient self-reported pre-consultation survey safely.
 * Keywords: React, intake, survey, triage, consent
 */
"use client";

import { useMemo, useState } from "react";
import {
  CONSTITUTION_QUESTIONS,
  CONSTITUTION_SURVEY_SCHEMA_VERSION,
  CORE_CONSTITUTION_QUESTION_IDS,
  DEFAULT_CONSTITUTION_ANSWERS,
  type ConstitutionQuestionId,
  type ConstitutionQuestionOption,
} from "@/lib/constitution-survey-schema";
import { buildClinicIntakePatientPinSmsBody } from "@/lib/clinic-intake-staff-link-v1";
import { ClinicIntakeMobileWizard } from "@/components/ClinicIntakeMobileWizard";

type PatientPreSurveyResponse = {
  success: boolean;
  survey_id?: string;
  intake_pin?: string;
  triage_level?: "routine" | "priority" | "emergency";
  recommended_partner_clinics?: {
    id: string;
    name: string;
    region: string;
    specialties: string[];
    available_times: string[];
  }[];
  emergency_notice?: string;
  reservation_request_id?: string;
  message?: string;
  error?: string;
  kakao_delivery?: {
    enabled: boolean;
    delivered: boolean;
    status?: number;
    error?: string;
  };
};

type PersonalSolutionReport = {
  surveyId: string;
  intakePin: string;
  triageLevel: "routine" | "priority" | "emergency";
  summaryTitle: string;
  summaryBody: string;
  nextAction: string;
  patientSnapshot: string;
  clinicPreference: string;
  patientName: string;
  patientPhone: string;
  recommendedClinics: {
    id: string;
    name: string;
    region: string;
    specialties: string[];
    available_times: string[];
  }[];
};

type PatientPreSurveyFormProps = {
  intakeMode?: "legacy" | "clinic_v1";
};

export function PatientPreSurveyForm({ intakeMode = "clinic_v1" }: PatientPreSurveyFormProps) {
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [birthdate, setBirthdate] = useState("");
  const [birthTime, setBirthTime] = useState("");
  const [birthTimeUnknown, setBirthTimeUnknown] = useState(false);
  const [ageBand, setAgeBand] = useState("");
  const [painArea, setPainArea] = useState("");
  const [painScale, setPainScale] = useState("5");
  const [duration, setDuration] = useState("");
  const [sleepPattern, setSleepPattern] = useState("");
  const [digestionPattern, setDigestionPattern] = useState("");
  const [clinicHeatColdSensitivity, setClinicHeatColdSensitivity] = useState("");
  const [clinicFatigueRecovery, setClinicFatigueRecovery] = useState("");
  const [constitutionAnswers, setConstitutionAnswers] =
    useState<Record<ConstitutionQuestionId, ConstitutionQuestionOption | "">>(DEFAULT_CONSTITUTION_ANSWERS);
  const [showAdvancedConstitutionSurvey, setShowAdvancedConstitutionSurvey] = useState(false);
  const [redFlags, setRedFlags] = useState({
    chestPain: false,
    breathingTrouble: false,
    paralysisOrSpeech: false,
    highFeverOrBleeding: false,
  });
  const [goal, setGoal] = useState("");
  const [preferredRegion, setPreferredRegion] = useState("");
  const [preferredSpecialty, setPreferredSpecialty] = useState("");
  const [preferredTime, setPreferredTime] = useState("");
  const [consentPrivacy, setConsentPrivacy] = useState(false);
  const [consentMedical, setConsentMedical] = useState(false);
  const [busy, setBusy] = useState(false);
  const [reservationBusyId, setReservationBusyId] = useState<string | null>(null);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [report, setReport] = useState<PersonalSolutionReport | null>(null);

  const hasRedFlag = useMemo(() => Object.values(redFlags).some(Boolean), [redFlags]);
  const answeredConstitutionCount = useMemo(
    () => Object.values(constitutionAnswers).filter((v) => v === "a" || v === "b").length,
    [constitutionAnswers],
  );
  const answeredCoreConstitutionCount = useMemo(
    () => CORE_CONSTITUTION_QUESTION_IDS.filter((id) => constitutionAnswers[id] === "a" || constitutionAnswers[id] === "b").length,
    [constitutionAnswers],
  );
  const isCoreConstitutionSurveyComplete = answeredCoreConstitutionCount === CORE_CONSTITUTION_QUESTION_IDS.length;
  const intakeShareMessage = useMemo(() => {
    if (!report) return "";
    if (intakeMode === "clinic_v1") {
      return buildClinicIntakePatientPinSmsBody({ intakePin: report.intakePin });
    }
    return `[NO1KMEDI 문진 코드]\n문진코드: ${report.intakePin}\n이름: ${report.patientName}\n진료 전에 원장님 화면에 이 코드를 입력해 주세요.`;
  }, [report, intakeMode]);

  function shareViaSms() {
    if (!report) return;
    const body = encodeURIComponent(intakeShareMessage);
    window.location.href = `sms:?&body=${body}`;
  }

  function shareViaKakao() {
    if (!report) return;
    const text = encodeURIComponent(intakeShareMessage);
    const fallback = encodeURIComponent(window.location.origin);
    window.open(`https://story.kakao.com/share?text=${text}&url=${fallback}`, "_blank", "noopener,noreferrer");
  }

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!consentPrivacy || !consentMedical) {
      setError("개인정보/의료정보 수집 동의를 모두 체크해 주세요.");
      return;
    }
    if (intakeMode === "legacy" && !isCoreConstitutionSurveyComplete) {
      setError("체질 핵심 설문 5문항을 모두 선택해 주세요.");
      return;
    }

    setBusy(true);
    setError("");
    setStatus("");
    try {
      const endpoint = intakeMode === "clinic_v1" ? "/api/intake/clinic-intake-v1" : "/api/intake/patient-presurvey";
      const requestBody =
        intakeMode === "clinic_v1"
          ? {
              schema_version: "clinic_intake_v1",
              patient: {
                name: name.trim(),
                phone: phone.trim(),
                birthdate: birthdate.trim() || ageBand.trim(),
                visit_type: "초진",
              },
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
                main_symptom: painArea.trim(),
                duration: duration.trim(),
                severity_nrs: Number(painScale),
                free_text: goal.trim(),
              },
              health_core: {
                sleep_quality: sleepPattern.trim() || "미입력",
                bowel_pattern: digestionPattern.trim() || "미입력",
                appetite: "미입력",
                stress_level: 5,
                medications: "",
              },
              constitution: {
                body_frame: "균형형",
                heat_cold_sensitivity: clinicHeatColdSensitivity || "비슷함",
                temperament: "상황에 따라 다름",
                digestion_pattern: digestionPattern.trim() || "불규칙함",
                fatigue_recovery: clinicFatigueRecovery || "중간",
              },
              clinic_preference: {
                region: preferredRegion.trim(),
                specialty: preferredSpecialty.trim(),
                preferred_time: preferredTime.trim(),
              },
              optional_profile: {
                birth_time: birthTimeUnknown ? undefined : birthTime.trim() || undefined,
                birth_time_known: !birthTimeUnknown && Boolean(birthTime.trim()),
              },
              submitted_at_utc: new Date().toISOString(),
            }
          : {
              name: name.trim(),
              phone: phone.trim(),
              age_band: ageBand,
              pain_area: painArea.trim(),
              pain_scale_0_10: Number(painScale),
              symptom_duration: duration.trim(),
              constitution_survey: {
                schema_version: CONSTITUTION_SURVEY_SCHEMA_VERSION,
                sleep_pattern: sleepPattern.trim(),
                digestion_pattern: digestionPattern.trim(),
                questionnaire_answers: constitutionAnswers,
              },
              red_flags: redFlags,
              consultation_goal: goal.trim(),
              partner_clinic_preference: {
                region: preferredRegion.trim(),
                specialty: preferredSpecialty.trim(),
                preferred_time: preferredTime.trim(),
              },
              consent: {
                privacy: consentPrivacy,
                medical: consentMedical,
              },
            };

      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestBody),
      });

      const json = (await res.json()) as PatientPreSurveyResponse;
      if (!res.ok || !json.success) {
        setError(json.error || "사전 문진 제출 중 오류가 발생했습니다.");
        return;
      }

      if (json.triage_level === "emergency") {
        setStatus(json.emergency_notice || "응급 신호가 감지되어 즉시 119/응급실 안내가 필요합니다.");
      } else {
        setStatus("사전 문진이 접수되었습니다. 의료진 검토 후 상담 순서를 안내드립니다.");
      }

      const triageLevel = json.triage_level || "routine";
      const severityScore = Number(painScale);
      const snapshot = `${painArea.trim()} / 통증 ${severityScore}점 / 지속 ${duration.trim()}`;
      const summaryTitle =
        triageLevel === "emergency"
          ? "응급 신호 우선 대응 필요"
          : triageLevel === "priority"
            ? "우선 상담 권장"
            : "일반 상담 순서 권장";
      const summaryBody =
        triageLevel === "emergency"
          ? "입력된 응급 신호를 기준으로 즉시 응급실 안내가 우선입니다. 안정 후 제휴 한의원 상담을 이어가세요."
          : triageLevel === "priority"
            ? "통증 강도와 증상 정보를 기준으로 빠른 시일 내 제휴 한의원 상담 예약을 권장합니다."
            : "현재 입력 기준으로는 일반 상담 순서로 검토가 가능합니다. 리포트를 지참해 상담 정확도를 높일 수 있습니다.";
      const nextAction =
        triageLevel === "emergency"
          ? "즉시 응급 대응 후 의료진 상담을 예약하세요."
          : "무료 리포트를 기반으로 제휴 한의원 예약을 진행하세요.";
      const clinicPreference = `지역 ${preferredRegion || "미지정"} / 분야 ${preferredSpecialty || "미지정"} / 시간 ${preferredTime || "미지정"}`;

      setReport({
        surveyId: json.survey_id || `presurvey_local_${Date.now()}`,
        intakePin: json.intake_pin || "PIN-ERROR",
        triageLevel,
        summaryTitle,
        summaryBody,
        nextAction,
        patientSnapshot: snapshot,
        clinicPreference,
        patientName: name.trim(),
        patientPhone: phone.trim(),
        recommendedClinics: json.recommended_partner_clinics || [],
      });

      setName("");
      setPhone("");
      setBirthdate("");
      setBirthTime("");
      setBirthTimeUnknown(false);
      setAgeBand("");
      setPainArea("");
      setPainScale("5");
      setDuration("");
      setSleepPattern("");
      setDigestionPattern("");
      setClinicHeatColdSensitivity("");
      setClinicFatigueRecovery("");
      setConstitutionAnswers(DEFAULT_CONSTITUTION_ANSWERS);
      setShowAdvancedConstitutionSurvey(false);
      setRedFlags({
        chestPain: false,
        breathingTrouble: false,
        paralysisOrSpeech: false,
        highFeverOrBleeding: false,
      });
      setGoal("");
      setPreferredRegion("");
      setPreferredSpecialty("");
      setPreferredTime("");
      setConsentPrivacy(false);
      setConsentMedical(false);
    } catch {
      setError("네트워크 오류로 제출에 실패했습니다.");
    } finally {
      setBusy(false);
    }
  }

  async function requestClinicReservation(clinic: {
    id: string;
    name: string;
  }) {
    if (!report) return;
    setReservationBusyId(clinic.id);
    setError("");
    try {
      const res = await fetch("/api/intake/patient-presurvey", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          reservation_request: {
            survey_id: report.surveyId,
            clinic_id: clinic.id,
            clinic_name: clinic.name,
            patient_name: report.patientName || "환자",
            patient_phone: report.patientPhone || "미입력",
          },
        }),
      });
      const json = (await res.json()) as PatientPreSurveyResponse;
      if (!res.ok || !json.success) {
        setError(json.error || "예약 요청 접수 중 오류가 발생했습니다.");
        return;
      }
      setStatus(json.message || "제휴 한의원 예약 요청이 접수되었습니다.");
    } catch {
      setError("네트워크 오류로 예약 요청에 실패했습니다.");
    } finally {
      setReservationBusyId(null);
    }
  }

  if (intakeMode === "clinic_v1") {
    return <ClinicIntakeMobileWizard />;
  }

  return (
    <section id="patient-intake" aria-labelledby="patient-intake-title">
      <h2 id="patient-intake-title">상세 문진 입력</h2>
      <p className="section-lead">한의원 상담 전 필요한 정보를 정리하는 단계입니다. 최종 진단·처방은 한의사가 수행합니다.</p>

      {hasRedFlag ? (
        <p className="patient-survey-emergency">
          응급 신호가 체크되었습니다. 즉시 119 또는 가까운 응급실을 우선 이용해 주세요.
        </p>
      ) : null}

      <form className="patient-survey-form" onSubmit={onSubmit}>
        <label>
          이름
          <input value={name} onChange={(e) => setName(e.target.value)} required />
        </label>
        <label>
          연락처
          <input value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="010-0000-0000" required />
        </label>
        <label>
          연령대
          <select value={ageBand} onChange={(e) => setAgeBand(e.target.value)} required>
            <option value="">선택</option>
            <option value="under20">20세 미만</option>
            <option value="20s">20대</option>
            <option value="30s">30대</option>
            <option value="40s">40대</option>
            <option value="50s">50대</option>
            <option value="60plus">60대 이상</option>
          </select>
        </label>
        <label>
          통증/불편 부위
          <input value={painArea} onChange={(e) => setPainArea(e.target.value)} required />
        </label>
        <label>
          통증 강도 (0~10)
          <input type="number" min={0} max={10} value={painScale} onChange={(e) => setPainScale(e.target.value)} required />
        </label>
        <label>
          증상 지속 기간
          <input value={duration} onChange={(e) => setDuration(e.target.value)} placeholder="예: 2주" required />
        </label>
        <label>
          수면 패턴
          <input value={sleepPattern} onChange={(e) => setSleepPattern(e.target.value)} placeholder="예: 입면 지연" />
        </label>
        <label>
          소화 패턴
          <input value={digestionPattern} onChange={(e) => setDigestionPattern(e.target.value)} placeholder="예: 식후 더부룩함" />
        </label>
        <fieldset className="patient-survey-full patient-survey-flags">
          <legend>체질 추정 설문 (핵심 5문항 필수)</legend>
            <p className="section-lead">
              핵심 설문 완료: {answeredCoreConstitutionCount}/{CORE_CONSTITUTION_QUESTION_IDS.length}
            </p>
            {CONSTITUTION_QUESTIONS.filter((item) => CORE_CONSTITUTION_QUESTION_IDS.includes(item.id)).map((item) => (
              <div key={item.id}>
                <p>{item.id}. {item.prompt}</p>
                <label>
                  <input
                    type="radio"
                    name={`constitution-${item.id}`}
                    value="a"
                    checked={constitutionAnswers[item.id] === "a"}
                    onChange={() => setConstitutionAnswers((prev) => ({ ...prev, [item.id]: "a" }))}
                  />
                  A. {item.optionA}
                </label>
                <label>
                  <input
                    type="radio"
                    name={`constitution-${item.id}`}
                    value="b"
                    checked={constitutionAnswers[item.id] === "b"}
                    onChange={() => setConstitutionAnswers((prev) => ({ ...prev, [item.id]: "b" }))}
                  />
                  B. {item.optionB}
                </label>
              </div>
            ))}
            <button type="button" className="btn btn-ghost" onClick={() => setShowAdvancedConstitutionSurvey((prev) => !prev)}>
              {showAdvancedConstitutionSurvey ? "정밀 15문항 닫기" : "정밀 15문항(선택) 열기"}
            </button>
            {showAdvancedConstitutionSurvey ? (
              <div>
                <p className="section-lead">정밀 설문 완료: {answeredConstitutionCount}/{CONSTITUTION_QUESTIONS.length}</p>
                {CONSTITUTION_QUESTIONS.filter((item) => !CORE_CONSTITUTION_QUESTION_IDS.includes(item.id)).map((item) => (
                  <div key={item.id}>
                    <p>{item.id}. {item.prompt}</p>
                    <label>
                      <input
                        type="radio"
                        name={`constitution-${item.id}`}
                        value="a"
                        checked={constitutionAnswers[item.id] === "a"}
                        onChange={() => setConstitutionAnswers((prev) => ({ ...prev, [item.id]: "a" }))}
                      />
                      A. {item.optionA}
                    </label>
                    <label>
                      <input
                        type="radio"
                        name={`constitution-${item.id}`}
                        value="b"
                        checked={constitutionAnswers[item.id] === "b"}
                        onChange={() => setConstitutionAnswers((prev) => ({ ...prev, [item.id]: "b" }))}
                      />
                      B. {item.optionB}
                    </label>
                  </div>
                ))}
              </div>
            ) : null}
          </fieldset>
        <label className="patient-survey-full">
          이번 상담에서 가장 해결하고 싶은 점
          <textarea value={goal} onChange={(e) => setGoal(e.target.value)} rows={3} placeholder="원하는 상담 방향을 적어 주세요." />
        </label>
        <label>
          희망 지역
          <input value={preferredRegion} onChange={(e) => setPreferredRegion(e.target.value)} placeholder="예: 광명, 강남" />
        </label>
        <label>
          희망 상담 분야
          <select value={preferredSpecialty} onChange={(e) => setPreferredSpecialty(e.target.value)}>
            <option value="">선택</option>
            <option value="pain">통증/근골격</option>
            <option value="digestive">소화/위장</option>
            <option value="sleep">수면/피로</option>
            <option value="women">여성건강</option>
            <option value="other">기타</option>
          </select>
        </label>
        <label>
          희망 상담 시간대
          <select value={preferredTime} onChange={(e) => setPreferredTime(e.target.value)}>
            <option value="">선택</option>
            <option value="weekday_morning">평일 오전</option>
            <option value="weekday_afternoon">평일 오후</option>
            <option value="weekday_evening">평일 저녁</option>
            <option value="weekend">주말</option>
          </select>
        </label>

        <fieldset className="patient-survey-full patient-survey-flags">
          <legend>응급/고위험 신호 체크 (해당 시 즉시 응급실 권고)</legend>
          <label>
            <input
              type="checkbox"
              checked={redFlags.chestPain}
              onChange={(e) => setRedFlags((prev) => ({ ...prev, chestPain: e.target.checked }))}
            />
            갑작스러운 흉통/압박감
          </label>
          <label>
            <input
              type="checkbox"
              checked={redFlags.breathingTrouble}
              onChange={(e) => setRedFlags((prev) => ({ ...prev, breathingTrouble: e.target.checked }))}
            />
            호흡곤란/의식저하
          </label>
          <label>
            <input
              type="checkbox"
              checked={redFlags.paralysisOrSpeech}
              onChange={(e) => setRedFlags((prev) => ({ ...prev, paralysisOrSpeech: e.target.checked }))}
            />
            편측 마비/말이 어눌함
          </label>
          <label>
            <input
              type="checkbox"
              checked={redFlags.highFeverOrBleeding}
              onChange={(e) => setRedFlags((prev) => ({ ...prev, highFeverOrBleeding: e.target.checked }))}
            />
            고열 지속/출혈/흑색변
          </label>
        </fieldset>

        <div className="patient-survey-full patient-survey-consent">
          <label>
            <input type="checkbox" checked={consentPrivacy} onChange={(e) => setConsentPrivacy(e.target.checked)} />
            개인정보 수집·이용에 동의합니다.
          </label>
          <label>
            <input type="checkbox" checked={consentMedical} onChange={(e) => setConsentMedical(e.target.checked)} />
            의료정보(문진) 수집·이용에 동의합니다.
          </label>
        </div>

        <button type="submit" className="btn btn-primary" disabled={busy}>
          {busy ? "제출 중..." : "사전 문진 제출"}
        </button>
      </form>
      <div className="consult-notice">
        <p>본 문진 결과는 상담 준비를 위한 참고 정보입니다.</p>
        <p>의학적 진단·처방·의무기록 확정은 한의사가 직접 수행합니다.</p>
        <p>응급 증상이 의심되면 즉시 119 또는 응급실을 이용해 주세요.</p>
      </div>

      {status ? <p className="lead-success">{status}</p> : null}
      {report ? (
        <article className="patient-report-card" aria-live="polite">
          <h3>상담 전 참고 리포트</h3>
          <p className="patient-report-pin">
            접수용 문진 코드: <strong>{report.intakePin}</strong>
          </p>
          <div className="section-cta" style={{ marginTop: "0", marginBottom: "0.75rem" }}>
            <button type="button" className="btn btn-ghost" onClick={shareViaKakao}>
              카카오로 코드 보내기
            </button>
            <button type="button" className="btn btn-ghost" onClick={shareViaSms}>
              문자로 코드 보내기
            </button>
          </div>
          <p className={`patient-report-badge is-${report.triageLevel}`}>분류: {report.summaryTitle}</p>
          <p>{report.summaryBody}</p>
          <p className="patient-report-meta">입력 요약: {report.patientSnapshot}</p>
          <p className="patient-report-meta">예약 선호: {report.clinicPreference}</p>
          <p className="patient-report-meta">리포트 ID: {report.surveyId}</p>
          {report.recommendedClinics.length > 0 ? (
            <div className="patient-report-clinics">
              <h4>추천 제휴 한의원 Top 3</h4>
              {report.recommendedClinics.map((clinic) => (
                <article key={clinic.id} className="patient-report-clinic-item">
                  <strong>{clinic.name}</strong>
                  <p>
                    {clinic.region} · 분야 {clinic.specialties.join(", ")} · 시간 {clinic.available_times.join(", ")}
                  </p>
                  <button
                    type="button"
                    className="btn btn-primary patient-clinic-request-btn"
                    disabled={reservationBusyId === clinic.id}
                    onClick={() => requestClinicReservation({ id: clinic.id, name: clinic.name })}
                  >
                    {reservationBusyId === clinic.id ? "요청 중..." : "이 병원으로 예약 요청"}
                  </button>
                </article>
              ))}
            </div>
          ) : null}
          <p className="patient-report-next">{report.nextAction}</p>
          <div className="patient-report-cta">
            <a className="btn btn-ghost" href="/consumer">
              대화 화면으로 돌아가기
            </a>
            <a className="btn btn-primary" href="#contact">
              제휴 한의원 예약 문의
            </a>
            <a className="btn btn-ghost" href="#advanced-consult">
              의료진 보조 화면 안내 보기
            </a>
          </div>
        </article>
      ) : null}
      {error ? <p className="consult-error">{error}</p> : null}
    </section>
  );
}
