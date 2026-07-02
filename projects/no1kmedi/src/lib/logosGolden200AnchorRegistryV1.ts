/** Golden-200 anchor registry loader — match logic in logosGolden200HubMatchV1.ts */
import { readFile } from "node:fs/promises";
import path from "node:path";

import { resolveLogosStudioWorkspaceRoot } from "./logosStudioEmbeddingBridgeV1";
import type { LogosStudioPreset } from "./logosResearchStudioV1";
import {
  getSyncGolden200Registry,
  matchGoldenHubQuery,
  type Golden200AnchorRegistryV1,
  type Golden200HubEntryV1,
  type BookChapterRuleV1,
} from "./logosGolden200HubMatchV1";

export type HubSpokeContractV1 = Golden200HubEntryV1["hub_spoke_contract"];

export const GOLDEN_200_REGISTRY_REL =
  "docs/final/artifacts/logos_golden_200_anchor_registry_v1_latest.json";

export type { Golden200AnchorRegistryV1, Golden200HubEntryV1, BookChapterRuleV1 };

export {
  getSyncGolden200Registry,
  matchGoldenHubQuery,
  matchGoldenHubTopic,
  hubPrimaryVerseRefs,
  parseRevelationChapterFromQuery,
  scoreGoldenHubEntry,
} from "./logosGolden200HubMatchV1";

const STUB_CLUSTER_PRESET_IDS = new Set([
  "job_job_suffering_reason",
  "job_existential_suffering",
]);

const JOB_QUERY_RE =
  /(욥|욥기|고난의\s*이유|신실|의인의\s*고난|job\s*\d|suffering|affliction)/i;

let cachedRegistry: Golden200AnchorRegistryV1 | null = null;

export async function loadGolden200AnchorRegistry(): Promise<Golden200AnchorRegistryV1 | null> {
  if (cachedRegistry) return cachedRegistry;
  const root = await resolveLogosStudioWorkspaceRoot();
  if (!root) return getSyncGolden200Registry();
  const filePath = path.join(root, GOLDEN_200_REGISTRY_REL);
  try {
    const raw = await readFile(filePath, "utf8");
    cachedRegistry = JSON.parse(raw) as Golden200AnchorRegistryV1;
    return cachedRegistry;
  } catch {
    return getSyncGolden200Registry();
  }
}

export function resolveGoldenHubPresetId(
  presets: LogosStudioPreset[],
  query: string,
  registry: Golden200AnchorRegistryV1,
): string | null {
  const hub = matchGoldenHubQuery(query, registry);
  if (!hub?.preset_override_ids?.length) return null;
  for (const id of hub.preset_override_ids) {
    if (presets.some((p) => p.id === id)) return id;
  }
  return null;
}

export function shouldSuppressStubEmbeddingRoute(query: string, presetId: string): boolean {
  if (!STUB_CLUSTER_PRESET_IDS.has(presetId)) return false;
  if (JOB_QUERY_RE.test(query)) return false;
  return true;
}

export function isStubClusterPresetId(presetId: string): boolean {
  return STUB_CLUSTER_PRESET_IDS.has(presetId);
}

export { STUB_CLUSTER_PRESET_IDS };
