#!/usr/bin/env node
/** Offline unit checks for eno-multimodal-intake-v1 (no HTTP). */
import {
  buildEnoMultimodalIntakeSnapshot,
  parseEnoHealthPayload,
  applyEnoIntakeToClinicianNotes,
} from "../src/lib/eno-multimodal-intake-v1.ts";

function assert(cond: boolean, msg: string) {
  if (!cond) throw new Error(msg);
}

const sample = {
  health_data: {
    survey: { vector_4d: { S: 0.27, L: 0.24, K: 0.23, M: 0.26 } },
    voice: { jitter: 0.18 },
    tongue: { color: "LightRed", hydrationScore: 62 },
    rppg: { heart_rate: 74, stress_score: 48 },
  },
};

const parsed = parseEnoHealthPayload(sample);
assert(parsed.ok, "parse sample");
const snap = buildEnoMultimodalIntakeSnapshot(parsed.data, "paste_json");
assert(snap.schema === "eno_multimodal_intake_snapshot_v1", "schema");
assert(snap.channels.voice === "present", "voice present");
assert(snap.channels.tongue === "present", "tongue present");
assert(snap.clinician_summary_ko.includes("[엔오 관측·보조]"), "summary tag");
const merged = applyEnoIntakeToClinicianNotes("기존 메모", snap);
assert(merged.includes("기존 메모") && merged.includes("[엔오 관측·보조]"), "merge notes");

console.log("verify-eno-multimodal-intake-v1: ok");
