"use client";

import { HUB_INTENT_CHIPS, type HubIntentId } from "@/lib/universeHubIntentRouterV2";

type Props = {
  selected: HubIntentId | null;
  onSelect: (id: HubIntentId | null) => void;
};

export function IntentChipRowV2({ selected, onSelect }: Props) {
  return (
    <div className="universe-hub-intent-row" role="group" aria-label="질문 의도">
      {HUB_INTENT_CHIPS.map((chip) => {
        const isSelected = selected === chip.id;
        return (
          <button
            key={chip.id}
            type="button"
            className={isSelected ? "universe-hub-intent-chip is-selected" : "universe-hub-intent-chip"}
            aria-pressed={isSelected}
            onClick={() => onSelect(isSelected ? null : chip.id)}
          >
            {chip.label}
          </button>
        );
      })}
    </div>
  );
}
