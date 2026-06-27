/**
 * Smoke: design token SSOT files exist and export expected keys.
 * Run: node ./scripts/check-design-tokens-smoke.mjs
 */
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const globals = readFileSync(join(root, "src/app/globals.css"), "utf8");
const requiredVars = [
  "--space-xs",
  "--space-2xl",
  "--text-hero",
  "--section-y",
  "--radius-lg",
];

const missing = requiredVars.filter((v) => !globals.includes(v));
if (missing.length) {
  console.error("[check-design-tokens-smoke] missing in globals.css:", missing.join(", "));
  process.exit(1);
}

const mapPath = join(root, "../../docs/final/artifacts/no1kmedi_figma_token_map_v1.json");
try {
  const map = JSON.parse(readFileSync(mapPath, "utf8"));
  if (map.schema !== "no1kmedi_figma_token_map_v1") {
    throw new Error("unexpected schema");
  }
} catch (e) {
  console.error("[check-design-tokens-smoke] figma map:", e.message);
  process.exit(1);
}

const fusionPath = join(root, "../../docs/final/artifacts/no1kmedi_design_fusion_ssot_v1.json");
try {
  const fusion = JSON.parse(readFileSync(fusionPath, "utf8"));
  if (fusion.schema !== "no1kmedi_design_fusion_ssot_v1") {
    throw new Error("unexpected fusion schema");
  }
  if (!fusion.figma_figjam?.board_url?.includes("figma.com/board")) {
    throw new Error("missing figjam board_url");
  }
  if (fusion.layer_b_blocked_reason) {
    throw new Error("deprecated layer_b_blocked_reason — use layer_b_status deferred_code_first");
  }
  if (fusion.layer_b_status === "not_started") {
    throw new Error("layer_b_status must not be not_started — use deferred_code_first");
  }
  if (fusion.layer_b_status !== "deferred_code_first") {
    throw new Error(`unexpected layer_b_status: ${fusion.layer_b_status}`);
  }
} catch (e) {
  console.error("[check-design-tokens-smoke] fusion ssot:", e.message);
  process.exit(1);
}

const flowComponent = join(root, "src/components/FieldLensGovernanceFlow.tsx");
const flowCss = readFileSync(join(root, "src/app/globals.css"), "utf8");
const flowSrc = readFileSync(flowComponent, "utf8");
if (!flowSrc.includes("non_gating")) {
  console.error("[check-design-tokens-smoke] FieldLensGovernanceFlow missing non_gating");
  process.exit(1);
}
const heroComponent = join(root, "src/components/HomeHeroSection.tsx");
if (!readFileSync(heroComponent, "utf8").includes("Layer B target")) {
  console.error("[check-design-tokens-smoke] HomeHeroSection missing Layer B marker");
  process.exit(1);
}
const copyJson = readFileSync(join(root, "marketing-site/public-copy.json"), "utf8");
if (!copyJson.includes("governance_flow") || !copyJson.includes("homepage_a11y")) {
  console.error("[check-design-tokens-smoke] public-copy missing governance_flow or homepage_a11y");
  process.exit(1);
}

try {
  execFileSync(process.execPath, [join(root, "scripts/check-homepage-marketing-copy-wired_v1.mjs")], {
    stdio: "inherit",
  });
} catch {
  process.exit(1);
}
if (!flowCss.includes(".field-lens-flow-grid")) {
  console.error("[check-design-tokens-smoke] globals missing .field-lens-flow-grid");
  process.exit(1);
}

const heroTokenChecks = [
  ["margin: 0 0 var(--space-xl)", ".hero-lead bottom margin"],
  [".hero-cta {", "hero-cta block"],
  ["gap: var(--space-md);", "hero-cta gap (base flex)"],
  ["font-size: var(--text-xs);", "hero-proof span font"],
  ["padding: var(--space-xs) var(--space-sm);", "hero-proof span padding"],
  ["margin-top: var(--space-md);", "hero-role-cta margin-top"],
];
for (const [needle, label] of heroTokenChecks) {
  if (!globals.includes(needle)) {
    console.error(`[check-design-tokens-smoke] hero token missing (${label}): ${needle}`);
    process.exit(1);
  }
}

const phase4TokenChecks = [
  [".pd-premium-cta {", "personadiary pd-premium-cta block"],
  ["gap: var(--space-md);", "pd-premium-cta gap (shared phase4)"],
  [".pd-glass {", "personadiary pd-glass block"],
  ["border-radius: var(--radius-lg);", "pd-glass radius (shared phase4)"],
  [".sf-hero-cta {", "smartfarm sf-hero-cta block"],
  [".sf-btn {", "smartfarm sf-btn block"],
  ["padding: var(--space-sm) var(--space-lg);", "sf-btn padding (shared phase4)"],
  ["border-radius: var(--radius-md);", "sf-btn radius (shared phase4)"],
  [".enterprise-eyebrow {", "enterprise eyebrow block"],
  ["padding: var(--space-xs) var(--space-md);", "enterprise-eyebrow padding"],
  [".enterprise-principle-chip {", "enterprise principle chip block"],
  ["border-radius: var(--radius-lg);", "enterprise chip radius (shared phase4)"],
];
for (const [needle, label] of phase4TokenChecks) {
  if (!globals.includes(needle)) {
    console.error(`[check-design-tokens-smoke] phase4 token missing (${label}): ${needle}`);
    process.exit(1);
  }
}

const phase5TokenChecks = [
  ["MKM-DESIGN-SYSTEM-TOKEN-V1 phase5/5b", "workspace phase5/5b marker comment"],
  [".workspace-nav-item {", "workspace nav item block"],
  ["border-radius: var(--radius-md);", "workspace nav radius (shared phase5)"],
  ["main.workspace-main {", "workspace main block"],
  ["padding: var(--space-md) var(--space-md) var(--space-lg);", "workspace main padding"],
  [".workspace-panel {", "workspace panel block"],
  [".clinician-chat-toolbar {", "clinician toolbar block"],
  [".clinician-chat-textarea {", "clinician textarea block"],
  [".workspace-consent-card {", "workspace consent card block"],
];
for (const [needle, label] of phase5TokenChecks) {
  if (!globals.includes(needle)) {
    console.error(`[check-design-tokens-smoke] phase5 token missing (${label}): ${needle}`);
    process.exit(1);
  }
}

const phase5bTokenChecks = [
  [".thread-rail-list {", "thread rail list block"],
  [".palette-input {", "palette input block"],
  [".chat-log {", "chat log block"],
  [".chat-bubble {", "chat bubble block"],
  ["border-radius: var(--radius-sm);", "chat bubble radius (shared phase5b)"],
];
for (const [needle, label] of phase5bTokenChecks) {
  if (!globals.includes(needle)) {
    console.error(`[check-design-tokens-smoke] phase5b token missing (${label}): ${needle}`);
    process.exit(1);
  }
}

const phase6TokenChecks = [
  [".chat-input-row {", "chat input row block"],
  [".lead-form input {", "lead form input block"],
  [".workspace-consent-check {", "workspace consent check block"],
  ["padding: var(--space-sm) var(--space-md);", "lead form input padding (phase6)"],
];
for (const [needle, label] of phase6TokenChecks) {
  if (!globals.includes(needle)) {
    console.error(`[check-design-tokens-smoke] phase6 token missing (${label}): ${needle}`);
    process.exit(1);
  }
}

const phase7TokenChecks = [
  [".lead-success {", "lead success block"],
  [".consult-access-row input {", "consult access input block"],
  ["margin: var(--space-md) 0 0;", "lead-success margin (phase7)"],
  ["gap: var(--space-sm);", "consult-access-row gap (phase7)"],
];
for (const [needle, label] of phase7TokenChecks) {
  if (!globals.includes(needle)) {
    console.error(`[check-design-tokens-smoke] phase7 token missing (${label}): ${needle}`);
    process.exit(1);
  }
}

const pdAndroidTokens = join(
  root,
  "../../docs/final/artifacts/personadiary_android_design_tokens_v1_latest.json"
);
try {
  const pdTok = JSON.parse(readFileSync(pdAndroidTokens, "utf8"));
  if (pdTok.schema !== "personadiary_android_design_tokens_v1") {
    throw new Error("unexpected personadiary android tokens schema");
  }
  if (!globals.includes("personadiary-android-design-tokens-v1")) {
    throw new Error("globals.css missing personadiary-android-design-tokens-v1 marker");
  }
} catch (e) {
  console.error("[check-design-tokens-smoke] personadiary android tokens:", e.message);
  process.exit(1);
}

const pdFigmaMap = join(
  root,
  "../../docs/final/artifacts/personadiary_figma_token_map_v1.json"
);
try {
  const pdMap = JSON.parse(readFileSync(pdFigmaMap, "utf8"));
  if (pdMap.schema !== "personadiary_figma_token_map_v1") {
    throw new Error("unexpected personadiary figma token map schema");
  }
  if (!pdMap.figma_file_key || !pdMap.figma_file_url?.includes("figma.com/design")) {
    throw new Error("personadiary figma file pointer missing");
  }
} catch (e) {
  console.error("[check-design-tokens-smoke] personadiary figma map:", e.message);
  process.exit(1);
}

console.log("[check-design-tokens-smoke] passed.");
process.exit(0);
