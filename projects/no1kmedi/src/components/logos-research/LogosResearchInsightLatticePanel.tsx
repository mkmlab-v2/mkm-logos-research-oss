"use client";

import { useEffect, useMemo, useState } from "react";

const LATTICE_URL = "/data/logos_studio/era_insight_lattice_genesis_v1.json";

export type GapChip = {
  chip_id: string;
  label_ko: string;
  bridge_question_ko?: string;
  hypothesis_class?: string;
};

export type LatticeCard = {
  card_id: string;
  layer?: string;
  title_ko?: string;
  body_ko?: string;
  gap_chips?: GapChip[];
};

export type EraInsightLatticeDoc = {
  schema_version?: string;
  era_id?: string;
  cards?: LatticeCard[];
};

type Props = {
  activePresetId?: string;
  onGapChipClick?: (chip: GapChip) => void;
};

export function LogosResearchInsightLatticePanel({ activePresetId, onGapChipClick }: Props) {
  const [doc, setDoc] = useState<EraInsightLatticeDoc | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [activeChipId, setActiveChipId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(LATTICE_URL, { cache: "force-cache" });
        if (!res.ok) throw new Error(`lattice_http_${res.status}`);
        const data = (await res.json()) as EraInsightLatticeDoc;
        if (!cancelled) {
          setDoc(data);
          setLoadError(null);
        }
      } catch (e: unknown) {
        if (!cancelled) {
          setLoadError(e instanceof Error ? e.message : "lattice_failed");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const gapCard = useMemo(
    () => (doc?.cards || []).find((c) => c.card_id === "gap"),
    [doc],
  );
  const chips = gapCard?.gap_chips || [];
  const showEraGap =
    !activePresetId ||
    activePresetId.startsWith("era_") ||
    activePresetId === "dynamic_graphrag";

  if (loadError) return null;
  if (!showEraGap || !chips.length) return null;

  return (
    <div className="lr-studio-lattice" aria-labelledby="lr-studio-lattice-title">
      <h3 id="lr-studio-lattice-title">{gapCard?.title_ko ?? "구조적 갭 · bridge 제안"}</h3>
      {gapCard?.body_ko ? <p className="lr-studio-lattice-lead">{gapCard.body_ko}</p> : null}
      <div className="lr-studio-gap-chips" role="list">
        {chips.map((chip) => (
          <button
            key={chip.chip_id}
            type="button"
            role="listitem"
            className={`lr-studio-gap-chip${activeChipId === chip.chip_id ? " lr-studio-gap-chip--active" : ""}`}
            title={chip.bridge_question_ko}
            onClick={() => {
              setActiveChipId(chip.chip_id);
              onGapChipClick?.(chip);
            }}
          >
            <span className="lr-studio-gap-chip-label">{chip.label_ko}</span>
            {chip.hypothesis_class ? (
              <span className="lr-studio-gap-chip-tag">[{chip.hypothesis_class}]</span>
            ) : null}
          </button>
        ))}
      </div>
      {activeChipId ? (
        <p className="lr-studio-gap-bridge" role="status">
          {chips.find((c) => c.chip_id === activeChipId)?.bridge_question_ko}
        </p>
      ) : null}
    </div>
  );
}
