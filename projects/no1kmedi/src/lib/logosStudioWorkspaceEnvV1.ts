import { readFileSync } from "node:fs";
import path from "node:path";

import { resolveMkmWorkspaceRoot } from "./km-workspace-root-v1";

const WORKSPACE_ENV_KEYS = [
  "AZURE_OPENAI_ENDPOINT",
  "AZURE_OPENAI_API_KEY",
  "AZURE_OPENAI_DEPLOYMENT",
  "AZURE_OPENAI_DEPLOYMENT_NAME",
  "AZURE_OPENAI_API_VERSION",
  "AZURE_OPENAI_FETCH_TIMEOUT_MS",
  "MKM_LOGOS_LLM_DISTILL_ENABLE",
  "LOGOS_STUDIO_AZURE_DISTILL",
  "LOGOS_STUDIO_GEN2_AZURE_DISTILL",
  "LOGOS_STUDIO_AZURE_DISTILL_MIN_VERSE_REFS",
  "LOGOS_STUDIO_AZURE_DISTILL_COMPLEXITY_MIN_SIGNALS",
  "LOGOS_STUDIO_AZURE_TIMEOUT_MS",
  "LOGOS_STUDIO_GEN2_AZURE_TIMEOUT_MS",
  "MKM_WORKSPACE_ROOT",
] as const;

function parseDotenvLine(line: string): { key: string; value: string } | null {
  const trimmed = line.trim();
  if (!trimmed || trimmed.startsWith("#")) return null;
  const eq = trimmed.indexOf("=");
  if (eq <= 0) return null;
  const key = trimmed.slice(0, eq).trim();
  let value = trimmed.slice(eq + 1).trim();
  if (
    (value.startsWith('"') && value.endsWith('"')) ||
    (value.startsWith("'") && value.endsWith("'"))
  ) {
    value = value.slice(1, -1);
  }
  return { key, value };
}

function readWorkspaceDotenv(root: string): Record<string, string> {
  const out: Record<string, string> = {};
  for (const fileName of [".env", ".env.local"]) {
    const filePath = path.join(root, fileName);
    try {
      const raw = readFileSync(filePath, "utf8");
      for (const line of raw.split(/\r?\n/)) {
        const parsed = parseDotenvLine(line);
        if (!parsed) continue;
        out[parsed.key] = parsed.value;
      }
    } catch {
      // optional file
    }
  }
  return out;
}

/** Merge monorepo root .env keys into child-process env when Next dev lacks Azure vars. */
export function mergeLogosStudioWorkspaceEnv(
  baseEnv: NodeJS.ProcessEnv = process.env,
): NodeJS.ProcessEnv {
  const root = resolveMkmWorkspaceRoot();
  if (!root) return { ...baseEnv };
  const workspaceEnv = readWorkspaceDotenv(root);
  const merged: NodeJS.ProcessEnv = { ...baseEnv, MKM_WORKSPACE_ROOT: root };
  for (const key of WORKSPACE_ENV_KEYS) {
    const current = String(merged[key] || "").trim();
    const fallback = String(workspaceEnv[key] || "").trim();
    if (!current && fallback) merged[key] = fallback;
  }
  return merged;
}
