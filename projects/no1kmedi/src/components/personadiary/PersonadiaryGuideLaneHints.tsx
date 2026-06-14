"use client";

import { extractLaneHintsFromDailyGuide } from "@/lib/personadiaryGuideLaneHints";
import type { DailyGuidePackage } from "@/lib/personadiaryDailyGuide";
import { PERSONADIARY_LANE_LABELS, PERSONADIARY_LANES } from "@/lib/personadiaryMobileOpsV1";

type Props = {
  pkg: DailyGuidePackage | null;
};

export function PersonadiaryGuideLaneHints({ pkg }: Props) {
  const hints = extractLaneHintsFromDailyGuide(pkg);
  const anyHint = PERSONADIARY_LANES.some((lane) => hints[lane]);

  if (!anyHint) return null;

  return (
    <div className="pd-ops-guide-lanes" aria-label="레인별 성찰 힌트">
      <p className="pd-ops-muted pd-ops-guide-lanes-label">
        레인별 힌트 · <span className="pd-ops-hypo-tag">[NON_GATING]</span> 처방·진단 아님
      </p>
      <ul className="pd-ops-guide-lanes-list">
        {PERSONADIARY_LANES.map((lane) =>
          hints[lane] ? (
            <li key={lane}>
              <span className="pd-ops-guide-lane-name">{PERSONADIARY_LANE_LABELS[lane]}</span>
              <span>{hints[lane]}</span>
            </li>
          ) : null
        )}
      </ul>
    </div>
  );
}
