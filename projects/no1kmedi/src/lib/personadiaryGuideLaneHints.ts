import type { DailyGuidePackage } from "./personadiaryDailyGuide";
import type { PersonadiaryLane } from "./personadiaryMobileOpsV1";

const LANES: PersonadiaryLane[] = ["body", "mind", "work", "rest"];

function clip(text: string, max = 96): string {
  const t = text.replace(/\s+/g, " ").trim();
  if (t.length <= max) return t;
  return `${t.slice(0, max - 1)}…`;
}

function firstBodyLine(block: { title_ko?: string; body_ko?: string }): string {
  const body = block.body_ko?.split("\n").find((l) => l.trim())?.trim();
  return clip(body || block.title_ko || "");
}

/** Pull-guide blocks → 4-lane reflection hints ([NON_GATING], not prescriptions). */
export function extractLaneHintsFromDailyGuide(
  pkg: DailyGuidePackage | null | undefined
): Partial<Record<PersonadiaryLane, string>> {
  if (!pkg?.ui_blocks?.length) return {};

  const hints: Partial<Record<PersonadiaryLane, string>> = {};
  const blocks = pkg.ui_blocks;

  const bodyBlock = blocks.find(
    (b) =>
      b.title_ko?.includes("몸") ||
      b.title_ko?.includes("리듬") ||
      b.type === "user_condition"
  );
  if (bodyBlock) hints.body = firstBodyLine(bodyBlock);

  const mindBlock =
    blocks.find((b) => b.type === "hero") ||
    blocks.find((b) => b.type === "verse") ||
    blocks.find((b) => b.type === "hypothesis_stream");
  if (mindBlock) hints.mind = firstBodyLine(mindBlock);

  const workBlock = blocks.find(
    (b) =>
      b.type === "card" &&
      (b.title_ko?.includes("일") ||
        b.title_ko?.includes("집중") ||
        b.title_ko?.includes("Next"))
  );
  if (workBlock) hints.work = firstBodyLine(workBlock);

  const restBlock = blocks.find(
    (b) =>
      b.title_ko?.includes("쉼") ||
      b.title_ko?.includes("휴") ||
      b.badge_ko?.includes("쉼")
  );
  if (restBlock) hints.rest = firstBodyLine(restBlock);

  return hints;
}
