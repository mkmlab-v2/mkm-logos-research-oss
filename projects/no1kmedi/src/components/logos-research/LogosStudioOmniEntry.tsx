"use client";

import type { PresetRow } from "@/lib/logosStudioOmniEntryTypes";
import {
  OmniPipelineStatusChips,
  type OmniPipelineChipV1,
} from "@/components/OmniPipelineStatusChips";

type Props = {
  title: string;
  lead: string;
  placeholder: string;
  governanceNote: string;
  query: string;
  onQueryChange: (value: string) => void;
  onRun: () => void;
  runLabel: string;
  running: boolean;
  runDisabled: boolean;
  quickPresets: PresetRow[];
  onQuickPreset: (presetId: string) => void;
  error?: string | null;
  quotaRemaining?: number | null;
  quotaTotal?: number;
  showQuota?: boolean;
  pipelineStages?: OmniPipelineChipV1[];
};

export function LogosStudioOmniEntry({
  title,
  lead,
  placeholder,
  governanceNote,
  query,
  onQueryChange,
  onRun,
  runLabel,
  running,
  runDisabled,
  quickPresets,
  onQuickPreset,
  error,
  quotaRemaining,
  quotaTotal,
  showQuota = true,
  pipelineStages = [],
}: Props) {
  return (
    <section
      className="lr-studio-omni-entry"
      data-logos-studio-omni-entry="1"
      aria-labelledby="lr-studio-omni-title"
    >
      <div className="lr-studio-omni-entry-inner">
        <p className="lr-studio-omni-eyebrow">{governanceNote}</p>
        <h2 id="lr-studio-omni-title" className="lr-studio-omni-title">
          {title}
        </h2>
        <p className="lr-studio-omni-lead">{lead}</p>

        <div className="lr-studio-omni-box" role="search">
          <textarea
            id="lr-query"
            className="lr-studio-omni-textarea"
            rows={4}
            value={query}
            onChange={(e) => onQueryChange(e.target.value)}
            placeholder={placeholder}
            aria-label="연구 질문"
            onKeyDown={(e) => {
              if (e.key === "Enter" && (e.metaKey || e.ctrlKey) && !runDisabled) {
                e.preventDefault();
                onRun();
              }
            }}
          />
          <div className="lr-studio-omni-actions">
            <button
              type="button"
              className="lr-btn lr-btn-primary lr-studio-omni-run"
              onClick={onRun}
              disabled={runDisabled}
            >
              {running ? "경로 엔진 실행 중…" : runLabel}
            </button>
            {showQuota && quotaRemaining != null && quotaTotal != null ? (
              <span className="lr-studio-omni-quota" role="status">
                오늘 남은 무료 쿼터 <strong>{quotaRemaining}</strong> / {quotaTotal}
              </span>
            ) : null}
          </div>
        </div>

        {pipelineStages.length ? (
          <OmniPipelineStatusChips stages={pipelineStages} variant="logos-studio" />
        ) : null}

        {quickPresets.length ? (
          <div className="lr-studio-omni-chips" role="group" aria-label="빠른 시작 주제">
            {quickPresets.map((row) => (
              <button
                key={row.id}
                type="button"
                className="lr-studio-omni-chip"
                onClick={() => onQuickPreset(row.id)}
              >
                {row.slot_label_ko ? (
                  <span className="lr-studio-omni-chip-slot">{row.slot_label_ko}</span>
                ) : null}
                <span className="lr-studio-omni-chip-label">{row.prompt_ko.slice(0, 48)}</span>
              </button>
            ))}
          </div>
        ) : null}

        {error ? (
          <p className="lr-studio-error lr-studio-omni-error" role="alert">
            {error}
          </p>
        ) : null}
      </div>
    </section>
  );
}
