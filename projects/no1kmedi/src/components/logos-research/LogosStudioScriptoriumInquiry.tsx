"use client";

import type { ReactNode } from "react";

type TopicPill = { id: string; label: string; active?: boolean };

type Props = {
  title: string;
  topicPills: TopicPill[];
  query: string;
  onQueryChange: (value: string) => void;
  onRun: () => void;
  runLabel: string;
  running: boolean;
  runDisabled: boolean;
  presetSelect: ReactNode;
  summaryBlock: ReactNode;
  verseChips: ReactNode;
  footer?: ReactNode;
};

export function LogosStudioScriptoriumInquiry({
  title,
  topicPills,
  query,
  onQueryChange,
  onRun,
  runLabel,
  running,
  runDisabled,
  presetSelect,
  summaryBlock,
  verseChips,
  footer,
}: Props) {
  return (
    <div className="lr-scriptorium-inquiry" data-logos-scriptorium-inquiry="1">
      <h2 id="lr-studio-run-title" className="lr-scriptorium-inquiry-title">
        {title}
      </h2>

      <div className="lr-scriptorium-search" role="search">
        <span className="lr-scriptorium-search-icon" aria-hidden="true">
          ⌕
        </span>
        <textarea
          id="lr-query"
          className="lr-studio-textarea lr-scriptorium-search-input"
          rows={3}
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          placeholder="질문을 입력하세요…"
          aria-label="연구 질문"
        />
        <button
          type="button"
          className="lr-btn lr-btn-primary lr-scriptorium-search-run"
          onClick={onRun}
          disabled={runDisabled}
        >
          {running ? "…" : runLabel}
        </button>
      </div>

      {topicPills.length ? (
        <div className="lr-scriptorium-preset-block">
          <p className="lr-scriptorium-preset-heading">프리셋</p>
          <div className="lr-scriptorium-topic-pills" role="list" aria-label="프리셋 분류">
            {topicPills.map((pill) => (
              <span
                key={pill.id}
                role="listitem"
                className={`lr-scriptorium-topic-pill${pill.active ? " lr-scriptorium-topic-pill--active" : ""}`}
              >
                {pill.label}
              </span>
            ))}
          </div>
        </div>
      ) : null}

      <div className="lr-scriptorium-preset-native">
        <details className="lr-scriptorium-preset-drawer">
          <summary className="lr-scriptorium-preset-drawer-summary">프리셋 목록</summary>
          {presetSelect}
        </details>
      </div>

      {summaryBlock}

      {verseChips ? (
        <div className="lr-scriptorium-inquiry-refs" aria-label="구절 참조">
          {verseChips}
        </div>
      ) : null}

      {footer}
    </div>
  );
}

export function dispatchScriptoriumVerseSelect(ref: string) {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new CustomEvent("logos-studio-scriptorium-verse-select", { detail: { ref } }));
}
