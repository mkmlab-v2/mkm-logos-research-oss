#!/usr/bin/env node
/**
 * HTTP smoke: clinician graph build-from-cds → review-feedback → pilot-kpi-summary.
 * Offline-safe: uses workspace CDS fixture (no MKM Python required for graph build).
 *
 *   npm run smoke:clinician-graph-http
 *   NO1KMEDI_BASE_URL=http://127.0.0.1:3010 npm run smoke:clinician-graph-http
 */

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const BASE_URL = process.env.NO1KMEDI_BASE_URL || "http://127.0.0.1:3010";
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const WORKSPACE_ROOT = path.resolve(__dirname, "../../..");
const FIXTURE = path.join(
  WORKSPACE_ROOT,
  "tests/fixtures/km_physician_cds_assist_envelope_with_tri_layer_v1.example.json",
);

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

async function request(urlPath, init) {
  const res = await fetch(`${BASE_URL}${urlPath}`, init);
  const text = await res.text();
  let json;
  try {
    json = JSON.parse(text);
  } catch {
    json = { raw: text };
  }
  return { res, json };
}

function loadFixtureEnvelope() {
  assert(fs.existsSync(FIXTURE), `fixture missing: ${FIXTURE}`);
  const doc = JSON.parse(fs.readFileSync(FIXTURE, "utf8"));
  assert(doc.schema === "km_physician_cds_assist_envelope_v1", "fixture schema");
  return doc;
}

async function main() {
  const encounterRef = `graph_smoke_${Date.now()}`;
  const envelope = loadFixtureEnvelope();

  let build;
  try {
    build = await request("/api/clinician/graph/build-from-cds", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Origin: BASE_URL,
        Referer: `${BASE_URL}/clinician`,
      },
      body: JSON.stringify({
        schema: "clinician_graph_build_from_cds_request_v1",
        request_id: encounterRef,
        cds_envelope: envelope,
        reasoning: {
          syndrome_hypothesis: "Illustrative pattern (smoke)",
          care_direction: "Physician review required",
          caution: "Deploy smoke caution flag",
        },
        options: {
          include_sasang_hint: true,
          include_conflict_paths: true,
        },
      }),
    });
  } catch (err) {
    console.error(`smoke-clinician-graph-http: SKIP (server unreachable at ${BASE_URL}). Start: npm run dev`);
    console.error(String(err?.message || err));
    process.exit(0);
  }

  assert(build.res.status === 200, `build-from-cds expected 200, got ${build.res.status}: ${build.json?.error}`);
  assert(build.json?.success === true, "build-from-cds success");
  const bundle = build.json?.graph_bundle_v1;
  assert(bundle && Array.isArray(bundle.nodes) && bundle.nodes.length >= 2, "graph nodes");
  assert(Array.isArray(bundle.edges), "graph edges");
  assert(build.json?.boundary?.physician_confirmation_required === true, "boundary");

  const feedback = await request("/api/clinician/graph/review-feedback", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Origin: BASE_URL,
      Referer: `${BASE_URL}/clinician`,
    },
    body: JSON.stringify({
      schema: "clinician_graph_review_feedback_request_v1",
      encounter_ref: encounterRef,
      target_id: bundle.nodes[1]?.id || "node:smoke",
      target_kind: "node",
      feedback: "hold",
      reason_code: "deploy_smoke",
    }),
  });
  assert(feedback.res.status === 200, `review-feedback expected 200, got ${feedback.res.status}`);
  assert(feedback.json?.success === true && feedback.json?.queued_for_review === true, "feedback queued");

  const kpi = await request("/api/clinician/graph/pilot-kpi-summary", { method: "GET" });
  assert(kpi.res.status === 200, `pilot-kpi-summary expected 200, got ${kpi.res.status}`);
  assert(kpi.json?.success === true, "pilot-kpi-summary success");
  assert(kpi.json?.summary?.schema === "clinician_graph_pilot_kpi_summary_v1" || kpi.json?.summary, "kpi summary");

  console.log(
    `smoke-clinician-graph-http: OK nodes=${bundle.nodes.length} edges=${bundle.edges.length} conflicts=${bundle.conflict_groups?.length || 0}`,
  );
}

main().catch((error) => {
  console.error("smoke-clinician-graph-http failed:", error.message);
  process.exit(1);
});
