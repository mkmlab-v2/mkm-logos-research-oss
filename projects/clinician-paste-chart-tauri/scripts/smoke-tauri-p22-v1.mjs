#!/usr/bin/env node
/**
 * Offline P2.2 gate — hotkey + clipboard inject markers in Rust source.
 */

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const libRs = path.join(root, "src-tauri", "src", "lib.rs");
const cap = path.join(root, "src-tauri", "capabilities", "default.json");
const conf = path.join(root, "src-tauri", "tauri.conf.json");

function assert(cond, msg) {
  if (!cond) throw new Error(msg);
}

const lib = fs.readFileSync(libRs, "utf8");
assert(lib.includes("on_shortcut"), "missing global shortcut registration");
assert(lib.includes("paste_clipboard_into_chart"), "missing clipboard paste handler");
assert(lib.includes(".pc-omni-textarea"), "missing omni textarea selector");

const permissions = JSON.parse(fs.readFileSync(cap, "utf8")).permissions;
assert(permissions.includes("clipboard-manager:allow-read-text"), "clipboard permission missing");
assert(permissions.includes("global-shortcut:allow-register"), "hotkey permission missing");

const bundle = JSON.parse(fs.readFileSync(conf, "utf8")).bundle;
assert(Array.isArray(bundle.targets) && bundle.targets.includes("nsis"), "nsis target missing");

console.log(
  JSON.stringify(
    {
      schema: "smoke_clinician_paste_chart_tauri_p22_v1",
      ok: true,
      hotkey_env: "KM_CLINICIAN_HOTKEY",
      default_hotkey: "Ctrl+Shift+V",
    },
    null,
    2,
  ),
);
