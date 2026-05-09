#!/usr/bin/env node

import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.resolve(__dirname, "..");
const eventsPath = path.join(projectRoot, "memory", "commercialization", "hub_events.jsonl");

const allowedEvents = new Set([
  "click_hub_cross_cta",
  "view_clinician_workspace",
  "submit_lead",
  "click_free_validation",
  "book_call",
  "view_pricing",
  "chat_answer_tier_result",
  "premium_payment_start",
  "premium_payment_redirect",
  "premium_access_verified",
]);

function fail(message) {
  console.error(`[check-telemetry-event-schema] ${message}`);
  process.exit(1);
}

try {
  const raw = await readFile(eventsPath, "utf8").catch(() => "");
  if (!raw.trim()) {
    console.log("[check-telemetry-event-schema] no telemetry rows found, skipping.");
    process.exit(0);
  }

  const lines = raw.split(/\r?\n/).filter((line) => line.trim().length > 0);
  for (let i = 0; i < lines.length; i += 1) {
    let row;
    try {
      row = JSON.parse(lines[i]);
    } catch {
      fail(`line ${i + 1}: invalid JSON`);
    }
    if (typeof row.event !== "string" || !row.event.trim()) {
      fail(`line ${i + 1}: event missing`);
    }
    if (!allowedEvents.has(row.event)) {
      fail(`line ${i + 1}: unsupported event "${row.event}"`);
    }
    if (typeof row.ts_utc !== "string" || !row.ts_utc.trim()) {
      fail(`line ${i + 1}: ts_utc missing`);
    }
    if (typeof row.session_id !== "string" || !row.session_id.trim()) {
      fail(`line ${i + 1}: session_id missing`);
    }
  }

  console.log(`[check-telemetry-event-schema] passed (${lines.length} row(s)).`);
} catch (error) {
  const message = error instanceof Error ? error.message : String(error);
  fail(`failed: ${message}`);
}
