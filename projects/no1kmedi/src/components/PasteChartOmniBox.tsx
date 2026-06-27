"use client";

import { useEffect, useId, useState, type ReactNode } from "react";

import {
  extractPasteChartDraftV1,
  formatPasteExtractChipLabel,
  mergePasteExtractDraft,
  type PasteExtractDraftV1,
} from "@/lib/clinician-chart-paste-extract-v1";
import {
  fetchPasteExtractDraftLlmV1,
  pasteExtractLlmClientEnabled,
} from "@/lib/clinician-paste-extract-client-v1";

const EXTRACT_DEBOUNCE_MS = 300;
const LLM_EXTRACT_DEBOUNCE_MS = 500;
const LLM_MIN_CHARS = 48;

type PasteChartOmniBoxProps = {
  chartText: string;
  onChartTextChange: (value: string) => void;
  draft: PasteExtractDraftV1;
  onDraftChange: (draft: PasteExtractDraftV1) => void;
  objectiveDraft: string;
  onObjectiveDraftChange: (value: string) => void;
  onAnalyze: () => void;
  analyzeBusy?: boolean;
  disabled?: boolean;
  error?: string | null;
  adviceWarning?: string | null;
  advancedSlot?: ReactNode;
  clinicianEmail?: string;
};

type ChipField = "display_name" | "birthdate" | "sex" | "chief_complaint";

export function PasteChartOmniBox({
  chartText,
  onChartTextChange,
  draft,
  onDraftChange,
  objectiveDraft,
  onObjectiveDraftChange,
  onAnalyze,
  analyzeBusy = false,
  disabled = false,
  error = null,
  adviceWarning = null,
  advancedSlot,
  clinicianEmail = "",
}: PasteChartOmniBoxProps) {
  const textareaId = useId();
  const [editingField, setEditingField] = useState<ChipField | null>(null);
  const [editValue, setEditValue] = useState("");
  const [llmAssist, setLlmAssist] = useState(false);
  const [llmBusy, setLlmBusy] = useState(false);

  useEffect(() => {
    const t = chartText.trim();
    if (!t) {
      onDraftChange({
        schema: "paste_extract_draft_v1",
        confidence: "low",
        sources: [],
      });
      setLlmAssist(false);
      return;
    }
    const handle = window.setTimeout(() => {
      onDraftChange(extractPasteChartDraftV1(t));
    }, EXTRACT_DEBOUNCE_MS);
    return () => window.clearTimeout(handle);
  }, [chartText, onDraftChange]);

  useEffect(() => {
    if (!pasteExtractLlmClientEnabled()) return;
    const t = chartText.trim();
    if (t.length < LLM_MIN_CHARS) {
      setLlmAssist(false);
      return;
    }

    const controller = new AbortController();
    const handle = window.setTimeout(() => {
      const baseline = extractPasteChartDraftV1(t);
      if (baseline.confidence === "high") {
        setLlmAssist(false);
        return;
      }
      void (async () => {
        setLlmBusy(true);
        const result = await fetchPasteExtractDraftLlmV1(t, clinicianEmail || undefined);
        if (controller.signal.aborted) return;
        setLlmBusy(false);
        if (result.ok) {
          onDraftChange(result.draft);
          setLlmAssist(true);
        }
      })();
    }, EXTRACT_DEBOUNCE_MS + LLM_EXTRACT_DEBOUNCE_MS);

    return () => {
      controller.abort();
      window.clearTimeout(handle);
    };
  }, [chartText, clinicianEmail, onDraftChange]);

  function openEdit(field: ChipField) {
    setEditingField(field);
    if (field === "display_name") setEditValue(draft.display_name || "");
    else if (field === "birthdate") setEditValue(draft.birthdate || "");
    else if (field === "sex") setEditValue(draft.sex === "M" ? "M" : draft.sex === "F" ? "F" : "");
    else setEditValue(draft.chief_complaint || "");
  }

  function saveEdit() {
    if (!editingField) return;
    const v = editValue.trim();
    if (editingField === "display_name") {
      onDraftChange(mergePasteExtractDraft(draft, { display_name: v || undefined }));
    } else if (editingField === "birthdate") {
      onDraftChange(mergePasteExtractDraft(draft, { birthdate: v || undefined }));
    } else if (editingField === "sex") {
      const sex = v === "M" || v === "F" ? v : "unknown";
      onDraftChange(mergePasteExtractDraft(draft, { sex }));
    } else {
      onDraftChange(mergePasteExtractDraft(draft, { chief_complaint: v || undefined }));
    }
    setEditingField(null);
  }

  function chipLabel(field: ChipField): string {
    if (field === "display_name") return draft.display_name?.trim() || "?";
    if (field === "birthdate") {
      if (draft.birthdate) return draft.birthdate;
      if (draft.age_years) return `만${draft.age_years}세`;
      return "?";
    }
    if (field === "sex") {
      if (draft.sex === "M") return "남";
      if (draft.sex === "F") return "여";
      return "?";
    }
    const cc = draft.chief_complaint?.trim();
    if (!cc) return "?";
    return cc.length > 22 ? `${cc.slice(0, 22)}…` : cc;
  }

  const chipSummary = formatPasteExtractChipLabel(draft);

  return (
    <section className="paste-chart-omni" aria-labelledby="paste-chart-omni-title">
      <p className="block-label" id="paste-chart-omni-title">
        차트 붙여넣기
      </p>
      <p className="pc-omni-lead">EMR·카톡·메모를 통째로 붙여넣으세요. 이름·생년·주증상은 아래 칩에서 확인·수정합니다.</p>

      <label htmlFor={textareaId} className="pc-paste-label sr-only">
        EMR 차트 붙여넣기
      </label>
      <textarea
        id={textareaId}
        className="pc-textarea pc-omni-textarea"
        rows={12}
        value={chartText}
        onChange={(e) => onChartTextChange(e.target.value)}
        placeholder="환자명, 생년, 주증상, 복용약, 맥진 메모… 두서없이 붙여넣어도 됩니다."
        disabled={disabled || analyzeBusy}
      />

      <div className="pc-draft-chip-row" aria-label="추출 메타데이터 확인">
        <span className={`pc-draft-confidence pc-draft-confidence--${draft.confidence}`}>
          {draft.confidence === "high" ? "추출 신뢰 높음" : "추출 확인 필요"}
          {llmBusy ? " · AI 보정 중…" : llmAssist ? " · AI 보정" : ""}
        </span>
        <span className="pc-draft-chip-summary" title={chipSummary}>
          {chipSummary}
        </span>
        <div className="pc-draft-chips">
          {(["display_name", "birthdate", "sex", "chief_complaint"] as ChipField[]).map((field) => (
            <button
              key={field}
              type="button"
              className={`pc-draft-chip${chipLabel(field) === "?" ? " is-uncertain" : ""}`}
              onClick={() => openEdit(field)}
              disabled={disabled || analyzeBusy}
              title="클릭하여 수정"
            >
              <span className="pc-draft-chip-key">
                {field === "display_name"
                  ? "이름"
                  : field === "birthdate"
                    ? "생년"
                    : field === "sex"
                      ? "성별"
                      : "주증상"}
              </span>
              <span className="pc-draft-chip-val">{chipLabel(field)}</span>
              <span className="pc-draft-chip-edit" aria-hidden>
                ✏️
              </span>
            </button>
          ))}
        </div>
      </div>

      {editingField ? (
        <div className="pc-draft-inline-edit" role="dialog" aria-label="칩 수정">
          <label>
            {editingField === "sex" ? "성별 (M / F)" : "값"}
            <input
              className="pc-input"
              value={editValue}
              onChange={(e) => setEditValue(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") saveEdit();
                if (e.key === "Escape") setEditingField(null);
              }}
              autoFocus
            />
          </label>
          <div className="pc-draft-inline-actions">
            <button type="button" className="btn-secondary" onClick={() => setEditingField(null)}>
              취소
            </button>
            <button type="button" className="btn-secondary" onClick={saveEdit}>
              적용
            </button>
          </div>
        </div>
      ) : null}

      <details className="obj-details">
        <summary>
          <span className="obj-arrow" aria-hidden>
            ▶
          </span>
          O · 객관 초안 (선택)
        </summary>
        <div className="obj-body">
          <label htmlFor="paste-chart-objective">맥·설진 스태프 메모</label>
          <textarea
            id="paste-chart-objective"
            className="pc-textarea pc-textarea--sm"
            rows={2}
            value={objectiveDraft}
            onChange={(e) => onObjectiveDraftChange(e.target.value)}
            placeholder="객관 소견 초안"
            disabled={disabled || analyzeBusy}
          />
        </div>
      </details>

      {advancedSlot ? (
        <details className="pc-advanced-details">
          <summary>
            <span className="obj-arrow" aria-hidden>
              ▶
            </span>
            고급 · Human Gold 환자 연결 (선택)
          </summary>
          <div className="pc-advanced-body">{advancedSlot}</div>
        </details>
      ) : null}

      {error ? (
        <div className="error-banner" role="alert">
          <span className="error-text">{error}</span>
        </div>
      ) : null}
      {adviceWarning ? <p className="paste-chart-advice-warning">{adviceWarning}</p> : null}

      {analyzeBusy ? (
        <div className="analyze-loading" aria-live="polite">
          <span className="spinner" aria-hidden />
          분석 중…
        </div>
      ) : (
        <button
          type="button"
          className="btn-analyze"
          onClick={onAnalyze}
          disabled={disabled || !chartText.trim()}
        >
          분석
        </button>
      )}
    </section>
  );
}
