#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const exe = path.join(root, "src-tauri", "target", "release", "clinician_paste_chart_tauri.exe");

if (!fs.existsSync(exe)) {
  console.error("missing release exe:", exe);
  process.exit(1);
}
const stat = fs.statSync(exe);
if (stat.size < 500_000) {
  console.error("exe too small:", stat.size);
  process.exit(1);
}

console.log(
  JSON.stringify(
    {
      schema: "smoke_clinician_paste_chart_tauri_build_artifact_v1",
      ok: true,
      exe,
      bytes: stat.size,
    },
    null,
    2,
  ),
);
