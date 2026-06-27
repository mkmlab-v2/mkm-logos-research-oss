#!/usr/bin/env node
/**
 * Post-build gate — NSIS installer exists after `npm run build`.
 */

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const bundleDir = path.join(root, "src-tauri", "target", "release", "bundle", "nsis");

function assert(cond, msg) {
  if (!cond) throw new Error(msg);
}

assert(fs.existsSync(bundleDir), `missing bundle dir: ${bundleDir}`);

const installers = fs
  .readdirSync(bundleDir)
  .filter((name) => name.endsWith("-setup.exe") || name.endsWith("_setup.exe"));

assert(installers.length > 0, `no NSIS setup exe in ${bundleDir}`);

const setup = path.join(bundleDir, installers[0]);
const stat = fs.statSync(setup);

console.log(
  JSON.stringify(
    {
      schema: "smoke_clinician_paste_chart_tauri_nsis_artifact_v1",
      ok: true,
      setup,
      bytes: stat.size,
    },
    null,
    2,
  ),
);
