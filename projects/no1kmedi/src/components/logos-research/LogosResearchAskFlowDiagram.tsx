/**
 * Static product-flow diagram — Question → Citation lock → School paths → Report.
 * Honest SVG/CSS only; no KPI / pass-rate numbers.
 */
export function LogosResearchAskFlowDiagram() {
  const steps = [
    { id: "q", label: "질문", sub: "구절·주제·고민" },
    { id: "c", label: "인용 고정", sub: "본문 앵커" },
    { id: "s", label: "학파 비교", sub: "해석 분기" },
    { id: "r", label: "경로·리포트", sub: "한 화면 정리" },
  ] as const;

  return (
    <figure
      className="lr-flow-diagram"
      data-logos-ask-flow-diagram="1"
      aria-labelledby="lr-flow-caption"
    >
      <figcaption id="lr-flow-caption" className="lr-flow-diagram-caption">
        연구 Ask 흐름
      </figcaption>
      <ol className="lr-flow-diagram-track" aria-label="질문에서 리포트까지">
        {steps.map((step, i) => (
          <li key={step.id} className="lr-flow-diagram-step">
            <span className="lr-flow-diagram-index" aria-hidden="true">
              {i + 1}
            </span>
            <strong className="lr-flow-diagram-label">{step.label}</strong>
            <span className="lr-flow-diagram-sub">{step.sub}</span>
            {i < steps.length - 1 ? (
              <span className="lr-flow-diagram-arrow" aria-hidden="true">
                →
              </span>
            ) : null}
          </li>
        ))}
      </ol>
      <svg
        className="lr-flow-diagram-svg"
        viewBox="0 0 640 72"
        xmlns="http://www.w3.org/2000/svg"
        role="presentation"
        aria-hidden="true"
      >
        <defs>
          <marker
            id="lrFlowArrow"
            markerWidth="8"
            markerHeight="8"
            refX="6"
            refY="3"
            orient="auto"
          >
            <path d="M0,0 L6,3 L0,6 Z" fill="var(--lr-accent, #c05621)" />
          </marker>
        </defs>
        {[80, 240, 400, 560].map((x, i) => (
          <g key={x}>
            <circle
              cx={x}
              cy="36"
              r="18"
              fill="color-mix(in srgb, var(--lr-accent, #c05621) 12%, #fff)"
              stroke="var(--lr-accent, #c05621)"
              strokeWidth="2"
            />
            <text
              x={x}
              y="40"
              textAnchor="middle"
              fontSize="12"
              fontWeight="700"
              fill="var(--lr-navy, #1a202c)"
            >
              {i + 1}
            </text>
            {i < 3 ? (
              <line
                x1={x + 22}
                y1="36"
                x2={x + 138}
                y2="36"
                stroke="var(--lr-accent, #c05621)"
                strokeWidth="2"
                strokeDasharray="4 4"
                markerEnd="url(#lrFlowArrow)"
              />
            ) : null}
          </g>
        ))}
      </svg>
      <p className="lr-flow-diagram-note">
        구조만 표시 · 수치·벤치마크 없음 · 교리 판결 아님
      </p>
    </figure>
  );
}
