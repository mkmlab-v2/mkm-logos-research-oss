"use client";

export type MkmThinkingStep = {
  id: string;
  label: string;
};

type MkmPathThinkingTimelineProps = {
  steps: MkmThinkingStep[];
  loading?: boolean;
  title?: string;
  emptyHint?: string;
  /** scriptorium mockup: horizontal pill rail, highlight mid-path step when idle */
  variant?: "default" | "scriptorium";
};

export function MkmPathThinkingTimeline({
  steps,
  loading = false,
  title = "경로 조립",
  emptyHint = "질의 실행 후 GraphRAG 경로 단계가 표시됩니다.",
  variant = "default",
}: MkmPathThinkingTimelineProps) {
  const visible = steps.length > 0 || loading;
  const scriptorium = variant === "scriptorium";

  if (!visible) {
    return (
      <div
        className={`mkm-thinking-timeline mkm-thinking-timeline--empty${scriptorium ? " mkm-thinking-timeline--scriptorium" : ""}`}
        data-mkm-thinking-timeline="1"
      >
        <p className="mkm-thinking-timeline-hint">{emptyHint}</p>
      </div>
    );
  }

  const activeIndex = loading
    ? Math.max(0, steps.length - 1)
    : steps.length >= 3
      ? 1
      : steps.length >= 1
        ? 0
        : -1;

  return (
    <div
      className={`mkm-thinking-timeline${scriptorium ? " mkm-thinking-timeline--scriptorium" : ""}`}
      data-mkm-thinking-timeline="1"
      aria-busy={loading}
    >
      <div className="mkm-thinking-timeline-head">
        <span className="mkm-thinking-timeline-title">{title}</span>
        {loading ? (
          <span className="mkm-thinking-timeline-status" role="status">
            조립 중…
          </span>
        ) : scriptorium ? null : (
          <span className="mkm-thinking-timeline-count">{steps.length}단계</span>
        )}
      </div>
      <ol className="mkm-thinking-timeline-steps">
        {steps.map((step, index) => (
          <li
            key={step.id}
            className={`mkm-thinking-timeline-step${
              (scriptorium && index === activeIndex) || (!scriptorium && loading && index === steps.length - 1)
                ? " mkm-thinking-timeline-step--active"
                : ""
            }`}
          >
            <span className="mkm-thinking-timeline-step-index" aria-hidden="true">
              {index + 1}
            </span>
            <span className="mkm-thinking-timeline-step-label">{step.label}</span>
          </li>
        ))}
        {loading && steps.length === 0 ? (
          <li className="mkm-thinking-timeline-step mkm-thinking-timeline-step--active">
            <span className="mkm-thinking-timeline-step-index" aria-hidden="true">
              …
            </span>
            <span className="mkm-thinking-timeline-step-label">프리셋 · 슬라이스 로드</span>
          </li>
        ) : null}
      </ol>
    </div>
  );
}

export function buildThinkingStepsFromPathLabels(
  steps: string[] | undefined,
  opts: { prefix?: string } = {},
): MkmThinkingStep[] {
  const prefix = opts.prefix ?? "step";
  if (!steps?.length) return [];
  return steps.map((label, index) => ({
    id: `${prefix}-${index}`,
    label: label.trim() || `단계 ${index + 1}`,
  }));
}
