"use client";

import {
  countPersonadiaryClinicAnswers,
  PERSONADIARY_CLINIC_CORE_IDS,
  PERSONADIARY_CLINIC_PACK,
  PERSONADIARY_CLINIC_SCALE_LABELS,
  PERSONADIARY_CLINIC_SCALE_MAX,
  type PersonadiaryClinicSurveyItem,
} from "@/lib/personadiaryClinicConstitutionSurveyV1";

type Props = {
  responses: Record<string, number | undefined>;
  onChange: (itemId: string, value: number) => void;
};

export function PersonadiaryConstitutionSurveyPanel({ responses, onChange }: Props) {
  const coreAnswered = countPersonadiaryClinicAnswers(responses, PERSONADIARY_CLINIC_CORE_IDS);
  const totalAnswered = countPersonadiaryClinicAnswers(responses);

  return (
    <div className="pd-ops-constitution-survey">
      <p className="pd-ops-muted">
        A-Code 프로필 자가체크 14문항 (0~4) · 핵심 {PERSONADIARY_CLINIC_CORE_IDS.length}문항 필수 · 비진단 ·
        로컬 저장
      </p>
      <p className="pd-ops-muted">
        완료: 핵심 {coreAnswered}/{PERSONADIARY_CLINIC_CORE_IDS.length} · 전체 {totalAnswered}/
        {PERSONADIARY_CLINIC_PACK.items.length}
      </p>
      <p className="pd-ops-muted">{PERSONADIARY_CLINIC_PACK.disclaimer_ko}</p>
      {PERSONADIARY_CLINIC_PACK.items.map((item: PersonadiaryClinicSurveyItem) => {
        const isCore = PERSONADIARY_CLINIC_CORE_IDS.includes(item.item_id);
        return (
          <fieldset key={item.item_id} className="pd-ops-fieldset">
            <legend className="pd-ops-muted">
              {item.item_id}
              {isCore ? " *" : ""} · {item.prompt_ko}
            </legend>
            <div className="pd-ops-likert-row" role="radiogroup">
              {PERSONADIARY_CLINIC_SCALE_LABELS.map((label, scaleValue) => (
                <label key={scaleValue} className="pd-ops-likert-option">
                  <input
                    type="radio"
                    name={`pd-clinic-${item.item_id}`}
                    value={scaleValue}
                    checked={responses[item.item_id] === scaleValue}
                    onChange={() => onChange(item.item_id, scaleValue)}
                  />
                  <span>
                    {scaleValue} · {label}
                  </span>
                </label>
              ))}
            </div>
          </fieldset>
        );
      })}
      <p className="pd-ops-muted" hidden>
        pd-constitution-scale-max-{PERSONADIARY_CLINIC_SCALE_MAX}
      </p>
    </div>
  );
}
