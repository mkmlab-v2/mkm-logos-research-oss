"use client";

import { useState } from "react";

export type ChartPasteSection = {
  id: string;
  title: string;
  hint?: string;
  text: string;
};

type ClinicianChartPastePanelProps = {
  sections: ChartPasteSection[];
  disabled?: boolean;
  /** Paste Chart v1 — compact SOAP slot grid (Antigravity mockup) */
  variant?: "default" | "paste-chart";
};

function soapSlotKey(section: ChartPasteSection): string {
  const t = section.title.trim();
  const head = t.charAt(0).toUpperCase();
  if (head === "S" || head === "O" || head === "A" || head === "P") return head;
  if (section.id === "subjective" || section.id.includes("subjective")) return "S";
  if (section.id === "objective" || section.id.includes("objective")) return "O";
  if (section.id === "assessment" || section.id.includes("assessment")) return "A";
  if (section.id === "plan" || section.id.includes("plan")) return "P";
  return t.slice(0, 1).toUpperCase() || "?";
}

export function ClinicianChartPastePanel({
  sections,
  disabled,
  variant = "default",
}: ClinicianChartPastePanelProps) {
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [copyError, setCopyError] = useState<string | null>(null);

  async function copySection(section: ChartPasteSection) {
    if (disabled || !section.text.trim()) return;
    setCopyError(null);
    try {
      await navigator.clipboard.writeText(section.text);
      setCopiedId(section.id);
      window.setTimeout(() => {
        setCopiedId((prev) => (prev === section.id ? null : prev));
      }, 2000);
    } catch {
      setCopyError("슬롯 복사에 실패했습니다. 브라우저 클립보드 권한을 확인해 주세요.");
    }
  }

  const visible = sections.filter((s) => s.text.trim());
  if (visible.length === 0) return null;

  if (variant === "paste-chart") {
    return (
      <div className="soap-panel" aria-labelledby="paste-chart-soap-title">
        <div className="soap-panel-head">
          <h4 id="paste-chart-soap-title" className="soap-panel-title">
            SOAP · EMR 슬롯 복사
          </h4>
          <p className="soap-panel-subtitle">복사 후 한의사랑·EMR 해당 칸에 붙여넣기 (초안)</p>
        </div>
        {copyError ? <p className="consult-error paste-chart-soap-error">{copyError}</p> : null}
        {visible.map((section) => {
          const key = soapSlotKey(section);
          return (
            <div key={section.id} className="soap-slot">
              <span className="soap-slot-key" aria-hidden>
                {key}
              </span>
              <div className="soap-slot-content">
                <div className="soap-slot-label">{section.title}</div>
                <div className="soap-slot-text">{section.text}</div>
              </div>
              <button
                type="button"
                className={`soap-slot-copy${copiedId === section.id ? " copied" : ""}`}
                disabled={disabled}
                onClick={() => copySection(section)}
              >
                {copiedId === section.id ? "복사됨 ✓" : "복사"}
              </button>
            </div>
          );
        })}
      </div>
    );
  }

  return (
    <div className="chart-paste-panel" aria-labelledby="chart-paste-panel-title">
      <h4 id="chart-paste-panel-title">한의사랑 차트 · 슬롯별 복사</h4>
      <p className="workspace-muted chart-paste-lead">
        EMR 연동 없이 <strong>복사 → 한의사랑 해당 칸 붙여넣기</strong>만 수행합니다. 최종 확정은
        원장(한의사)만 합니다.
      </p>
      <ol className="chart-paste-workflow">
        <li>「진료 보조 초안 생성」으로 CDSS 봉투 준비</li>
        <li>아래 블록별 「복사」 → 한의사랑 SOAP·메모 칸에 붙여넣기</li>
        <li>환자 안내 번들 생성 후 슬롯별 복사(선택)</li>
      </ol>
      {copyError ? <p className="consult-error">{copyError}</p> : null}
      <div className="chart-paste-sections">
        {visible.map((section) => (
          <section key={section.id} className="chart-paste-section" aria-labelledby={`paste-${section.id}`}>
            <h5 id={`paste-${section.id}`}>{section.title}</h5>
            {section.hint ? <p className="workspace-muted chart-paste-hint">{section.hint}</p> : null}
            <pre className="chart-paste-pre">{section.text}</pre>
            <button
              type="button"
              className="btn btn-ghost btn-sm chart-paste-copy"
              disabled={disabled}
              onClick={() => copySection(section)}
            >
              {copiedId === section.id ? "복사됨 ✓" : "복사"}
            </button>
          </section>
        ))}
      </div>
    </div>
  );
}
