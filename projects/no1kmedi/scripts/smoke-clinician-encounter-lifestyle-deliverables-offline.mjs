#!/usr/bin/env node
/**
 * Offline smoke: lifestyle fixture → print HTML (lee_heecheol).
 */
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const monoRoot = path.resolve(__dirname, "..", "..", "..");

function assert(cond, msg) {
  if (!cond) throw new Error(msg);
}

function resolvePrintHtmlRel(paths) {
  for (const [key, rel] of Object.entries(paths)) {
    if (!rel.endsWith(".html")) continue;
    if (rel.includes(" ") || rel.startsWith("py ")) continue;
    if (key.includes("print") || rel.includes("lifestyle_print")) return rel;
  }
  const cli = paths.lifestyle_render_cli || "";
  const m = /--out-html\s+(\S+)/.exec(cli);
  return m?.[1] || null;
}

function main() {
  const pointer = JSON.parse(
    fs.readFileSync(path.join(monoRoot, "reports", "lee_heecheol_intake_ssot_pointer_v1.json"), "utf8"),
  );
  const fixtureRel = pointer.paths?.lifestyle_management_fixture;
  const printRel = resolvePrintHtmlRel(pointer.paths || {});
  assert(fixtureRel && printRel, "pointer paths missing");

  const py = process.env.MKM_PYTHON || "py";
  const script = path.join(monoRoot, "scripts", "render_clinic_lifestyle_management_print_v1.py");
  const child = spawnSync(
    py,
    [script, "--input-json", path.join(monoRoot, fixtureRel), "--out-html", path.join(monoRoot, printRel)],
    { cwd: monoRoot, encoding: "utf-8", timeout: 60_000, windowsHide: true },
  );
  if (child.status !== 0) throw new Error((child.stderr || child.stdout || "").slice(0, 1500));
  const html = fs.readFileSync(path.join(monoRoot, printRel), "utf8");
  assert(html.includes("<html") || html.includes("<!DOCTYPE"), "html output invalid");
  console.log(`smoke-clinician-encounter-lifestyle-deliverables-offline: OK ${printRel}`);
}

main();
