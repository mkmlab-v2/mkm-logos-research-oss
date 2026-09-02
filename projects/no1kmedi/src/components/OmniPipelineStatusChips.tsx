"use client";

export type OmniPipelineChipStatus =
  | "pending"
  | "active"
  | "ok"
  | "warn"
  | "fail"
  | "skipped";

export type OmniPipelineChipV1 = {
  id: string;
  label_ko: string;
  status: OmniPipelineChipStatus;
};

type OmniPipelineStatusChipsProps = {
  stages: OmniPipelineChipV1[];
  variant?: "paste-chart" | "logos-studio";
  className?: string;
};

export function OmniPipelineStatusChips({
  stages,
  variant = "paste-chart",
  className = "",
}: OmniPipelineStatusChipsProps) {
  if (!stages.length) return null;

  const active = stages.find((s) => s.status === "active");

  return (
    <div
      className={`omni-pipeline-chips omni-pipeline-chips--${variant}${className ? ` ${className}` : ""}`}
      role="status"
      aria-live="polite"
      aria-label="실행 단계"
    >
      <ol className="omni-pipeline-chip-list">
        {stages.map((stage, index) => (
          <li
            key={stage.id}
            className={`omni-pipeline-chip omni-pipeline-chip--${stage.status}`}
            aria-current={stage.status === "active" ? "step" : undefined}
          >
            <span className="omni-pipeline-chip-index" aria-hidden>
              {index + 1}
            </span>
            <span className="omni-pipeline-chip-label">{stage.label_ko}</span>
          </li>
        ))}
      </ol>
      {active ? (
        <p className="omni-pipeline-active-hint">
          {active.label_ko}
          …
        </p>
      ) : null}
    </div>
  );
}
