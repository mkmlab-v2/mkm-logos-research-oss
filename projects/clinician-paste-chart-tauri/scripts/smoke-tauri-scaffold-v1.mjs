#!/usr/bin/env node
/**
 * Offline scaffold gate — file layout only (no cargo/tauri build).
 */

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

const required = [
  "package.json",
  "README.md",
  ".env.example",
  "src-tauri/Cargo.toml",
  "src-tauri/tauri.conf.json",
  "src-tauri/src/main.rs",
  "src-tauri/src/lib.rs",
  "src-tauri/capabilities/default.json",
  "src-tauri/icons/icon.png",
  "src-tauri/icons/icon.ico",
];

function assert(cond, msg) {
  if (!cond) throw new Error(msg);
}

for (const rel of required) {
  const p = path.join(root, rel);
  assert(fs.existsSync(p), `missing: ${rel}`);
}

const conf = JSON.parse(fs.readFileSync(path.join(root, "src-tauri/tauri.conf.json"), "utf8"));
assert(conf.identifier === "com.jemaai.clinician.pastechart", "identifier mismatch");
assert(conf.productName === "MKM Paste Chart", "productName mismatch");

console.log(
  JSON.stringify(
    {
      schema: "smoke_clinician_paste_chart_tauri_scaffold_v1",
      ok: true,
      files_checked: required.length,
      identifier: conf.identifier,
    },
    null,
    2,
  ),
);
