/** Server-side logos research handoff loader (Node route handlers). */
import { readFile } from "node:fs/promises";
import path from "node:path";

import type { LogosJemaAiResearchHandoffV1 } from "./logosJemaAiResearchHandoffV1";
import type { LogosTextMvpHandoffSummary } from "./logosResearchTextMvpV1";
import { DEFAULT_TEXT_MVP_HANDOFF } from "./logosResearchTextMvpV1";
import { handoffToTextMvpSummary } from "./logosJemaAiResearchHandoffV1";

const HANDOFF_REL = "public/data/logos_jema_ai_research_handoff_v1.json";

export async function loadLogosResearchHandoffServer(): Promise<LogosJemaAiResearchHandoffV1 | null> {
  try {
    const filePath = path.join(process.cwd(), HANDOFF_REL);
    const raw = await readFile(filePath, "utf8");
    return JSON.parse(raw) as LogosJemaAiResearchHandoffV1;
  } catch {
    return null;
  }
}

export async function loadTextMvpHandoffSummary(): Promise<LogosTextMvpHandoffSummary> {
  const doc = await loadLogosResearchHandoffServer();
  return doc ? handoffToTextMvpSummary(doc) : DEFAULT_TEXT_MVP_HANDOFF;
}
