/**
 * Resolve Figma Hero pilot target from .env.local (OPT-IN MANUAL ONLY).
 * Not in CI/deploy chain. Layer B status: deferred_code_first (see design fusion SSOT).
 * Run from projects/no1kmedi: node scripts/resolve_no1kmedi_figma_hero_target_v1.mjs
 */
import { readFileSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");

function loadEnvLocal() {
  const path = join(root, ".env.local");
  if (!existsSync(path)) return;
  for (const line of readFileSync(path, "utf8").split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const eq = trimmed.indexOf("=");
    if (eq < 1) continue;
    const key = trimmed.slice(0, eq).trim();
    let val = trimmed.slice(eq + 1).trim();
    if ((val.startsWith('"') && val.endsWith('"')) || (val.startsWith("'") && val.endsWith("'"))) {
      val = val.slice(1, -1);
    }
    if (process.env[key] == null || process.env[key] === "") process.env[key] = val;
  }
}

loadEnvLocal();

const url = process.env.FIGMA_TARGET_DESIGN_URL?.trim() ?? "";
const nodeId = process.env.FIGMA_HERO_NODE_ID?.trim() ?? "";
const frameName = process.env.FIGMA_HERO_FRAME_NAME?.trim() ?? "";

if (!url) {
  console.error(
    "[resolve_no1kmedi_figma_hero_target_v1] skipped: Layer B deferred_code_first — set FIGMA_TARGET_DESIGN_URL in .env.local only when a Figma Design file exists (FigJam is not valid).",
  );
  process.exit(2);
}

const payload = {
  schema: "no1kmedi_figma_hero_target_v1",
  design_url: url,
  hero_node_id: nodeId || null,
  hero_frame_name: frameName || null,
  hero_component: "src/components/HomeHeroSection.tsx",
  token_map: "docs/final/artifacts/no1kmedi_figma_token_map_v1.json",
};

console.log(JSON.stringify(payload, null, 2));
process.exit(0);
