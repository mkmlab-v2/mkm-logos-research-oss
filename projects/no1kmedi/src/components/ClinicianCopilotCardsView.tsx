"use client";

import { useState } from "react";

import {
  buildPatientEducationCopy,
  type SimpleCopilotCardsV1,
  type SimpleCopilotMedicalCalcV1,
  type SimpleCopilotSajuCalcV1,
} from "@/lib/clinician-simple-copilot-v1";

type CopilotCardProps = {
  title: string;
  badge?: string;
  variant?: "primary" | "muted";
  children: React.ReactNode;
};

function CopilotCard({ title, badge, variant = "muted", children }: CopilotCardProps) {
  return (
    <section className={`copilot-card copilot-card--${variant}`}>
      <header className="copilot-card-head">
        <h3 className="copilot-card-title">{title}</h3>
        {badge ? <span className="copilot-card-badge">{badge}</span> : null}
      </header>
      <div className="copilot-card-body">{children}</div>
    </section>
  );
}

export type ClinicianCopilotCardsViewProps = {
  cards: SimpleCopilotCardsV1;
  medicalCalc?: SimpleCopilotMedicalCalcV1 | null;
  sajuCalc?: SimpleCopilotSajuCalcV1 | null;
  chiefComplaint?: string;
  patientEducationCopy?: string;
  compact?: boolean;
};

export function ClinicianCopilotCardsView({
  cards,
  medicalCalc,
  sajuCalc,
  chiefComplaint = "",
  patientEducationCopy,
  compact,
}: ClinicianCopilotCardsViewProps) {
  const [copyOk, setCopyOk] = useState<string | null>(null);

  async function copyText(key: string, text: string) {
    if (!text.trim()) return;
    try {
      await navigator.clipboard.writeText(text);
      setCopyOk(key);
      window.setTimeout(() => setCopyOk((c) => (c === key ? null : c)), 2000);
    } catch {
      /* clipboard denied */
    }
  }

  const education =
    patientEducationCopy?.trim() ||
    (chiefComplaint.trim()
      ? buildPatientEducationCopy({
          chief_complaint: chiefComplaint,
          cards,
          medical: medicalCalc || undefined,
          saju: sajuCalc || undefined,
        })
      : "");

  return (
    <div className={`paste-chart-advice${compact ? " paste-chart-advice--compact" : ""}`}>
      {medicalCalc ? (
        <div className="copilot-meta-strip">
          <span className="copilot-meta-chip">{medicalCalc.triage_label_ko}</span>
          <span className="copilot-meta-chip">통증 {medicalCalc.pain_scale_0_10}/10</span>
        </div>
      ) : null}
      {sajuCalc ? (
        <div className="copilot-meta-strip">
          <span className="copilot-meta-chip">{sajuCalc.saju_label || "사주 보조"}</span>
        </div>
      ) : null}

      <div className="copilot-action-row">
        {education ? (
          <button
            type="button"
            className="copilot-action-btn copilot-action-btn--primary"
            onClick={() => void copyText("edu", education)}
          >
            {copyOk === "edu" ? "환자 안내문 복사됨 ✓" : "환자 안내문 복사"}
          </button>
        ) : null}
      </div>

      <CopilotCard title={cards.tcm_primary.title} variant="primary">
        {cards.tcm_primary.items.length ? (
          <ul className="copilot-item-list">
            {cards.tcm_primary.items.map((item, i) => (
              <li key={`tcm-${i}`}>
                <strong>{item.title}</strong>
                <p>{item.body}</p>
              </li>
            ))}
          </ul>
        ) : (
          <p className="copilot-empty">해당 항목이 없습니다.</p>
        )}
      </CopilotCard>

      <CopilotCard title={cards.modern_explain.title} badge="비결정">
        {cards.modern_explain.items.length ? (
          <ul className="copilot-item-list">
            {cards.modern_explain.items.map((item, i) => (
              <li key={`mod-${i}`}>
                <strong>{item.title}</strong>
                <p>{item.body}</p>
              </li>
            ))}
          </ul>
        ) : (
          <p className="copilot-empty">근거 설명 슬롯이 비어 있습니다.</p>
        )}
      </CopilotCard>

      {!compact ? (
        <CopilotCard title={cards.saju_aux.title} badge="보조/비결정">
          {cards.saju_aux.items.length ? (
            <ul className="copilot-item-list">
              {cards.saju_aux.items.map((item, i) => (
                <li key={`saju-${i}`}>
                  <strong>{item.title}</strong>
                  <p>{item.body}</p>
                </li>
              ))}
            </ul>
          ) : (
            <p className="copilot-empty">사주·시간축 보조 항목이 없습니다.</p>
          )}
        </CopilotCard>
      ) : null}

      <CopilotCard title={cards.physician_checklist.title}>
        <ul className="copilot-checklist">
          {cards.physician_checklist.items.map((line, i) => (
            <li key={`chk-${i}`}>{line}</li>
          ))}
        </ul>
      </CopilotCard>

      <p className="copilot-disclaimer">{cards.disclaimer}</p>
    </div>
  );
}
