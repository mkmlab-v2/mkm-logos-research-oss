/**
 * Offline smoke: Logos auth.md + discovery lib alignment.
 * Run from projects/no1kmedi: node scripts/check-logos-auth-md-v1.mjs
 */
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const authPath = join(root, "public", "auth.md");
const libPath = join(root, "src", "lib", "logosAgentAuthDiscoveryV1.ts");

const REQUIRED_SECTIONS = [
  "Step 1 — Discover",
  "Step 2 — Pick a method",
  "Step 3 — Register",
  "Step 5 — Exchange claim",
  "Revoke",
  "Forbidden agent actions",
];

const REQUIRED_PHRASES = [
  "tier_c_service_auth",
  "research_only",
  "send_gate: HOLD",
  "service_auth",
  "x-logos-api-key",
  "authorization_pending",
  "/api/agent/identity",
  "logos.jema-ai.com",
  "/api/logos-research/presets",
  "/api/logos-research/query",
];

function main() {
  const auth = readFileSync(authPath, "utf8");
  const lib = readFileSync(libPath, "utf8");
  const failures = [];

  for (const section of REQUIRED_SECTIONS) {
    if (!auth.includes(section)) failures.push(`missing_section:${section}`);
  }
  for (const phrase of REQUIRED_PHRASES) {
    if (!auth.includes(phrase)) failures.push(`missing_phrase:${phrase}`);
  }
  if (!lib.includes('implementation_status: "tier_c_service_auth"')) {
    failures.push("lib:implementation_status");
  }
  for (const scope of [
    "logos.presets.read",
    "logos.query.read",
    "logos.evidence.write",
    "logos.lead.write",
  ]) {
    if (!lib.includes(scope)) failures.push(`lib:scope:${scope}`);
  }

  if (failures.length) {
    console.error("[check-logos-auth-md] FAIL", failures);
    process.exit(1);
  }
  console.log("[check-logos-auth-md] OK", { authPath, libPath });
}

main();
