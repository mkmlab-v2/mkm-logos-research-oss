#!/usr/bin/env node
/**
 * Offline smoke: encounter-artifacts pointer contract (no Next server).
 * Run from repo root or projects/no1kmedi with MKM workspace at ../../
 */
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
  const slug = "lee_heecheol";
  const pointerPath = path.join(monoRoot, "reports", `${slug}_intake_ssot_pointer_v1.json`);
  assert(fs.existsSync(pointerPath), `missing pointer: ${pointerPath}`);
  const pointer = JSON.parse(fs.readFileSync(pointerPath, "utf8"));
  assert(pointer.ref_token === "LEE-HEECHEOL-2026-001", `ref_token: ${pointer.ref_token}`);
  const mdRel = pointer.paths?.lifestyle_management_md;
  const kakaoRel = pointer.paths?.clinic_kakao;
  assert(mdRel && fs.existsSync(path.join(monoRoot, mdRel)), "lifestyle_management_md missing");
  assert(kakaoRel && fs.existsSync(path.join(monoRoot, kakaoRel)), "clinic_kakao missing");
  const printRel = resolvePrintHtmlRel(pointer.paths || {});
  assert(printRel && fs.existsSync(path.join(monoRoot, printRel)), `print html missing: ${printRel}`);
  console.log(`smoke-clinician-encounter-artifacts-offline: OK slug=${slug} print=${printRel}`);
}

main();
