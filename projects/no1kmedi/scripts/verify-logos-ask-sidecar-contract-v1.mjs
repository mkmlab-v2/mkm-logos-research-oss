/**
 * Validate logos_ask_graph_sidecar_contract_v1_latest.json structure (no JSON Schema lib).
 * Run: npm run verify:logos-ask-sidecar-contract
 */
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "../../..");
const CONTRACT = path.join(
  ROOT,
  "docs/final/artifacts/logos_ask_graph_sidecar_contract_v1_latest.json",
);

function assert(cond, msg) {
  if (!cond) throw new Error(msg);
}

const doc = JSON.parse(readFileSync(CONTRACT, "utf8"));
assert(doc.schema === "logos_ask_graph_sidecar_contract_v1", "schema id");
assert(doc.max_mesh_nodes <= 40, "mesh cap");
assert(doc.sse_graph_sync?.mode === "post_snapshot", "sse mode");
assert(Array.isArray(doc.ui_public_layers?.stream_events), "ui stream_events");
assert(
  doc.ui_public_layers.stream_events.join(",") === "snapshot,s4_delta,s4_done,done,error",
  "stream event order",
);
assert(
  doc.ui_public_layers.public_report_sections?.join(",") === "S1,S4",
  "public sections",
);
assert(
  doc.ui_public_layers.collapsed_dev_sections?.join(",") === "S2,S3,S5",
  "collapsed sections",
);
assert(doc.ui_public_layers.graph_seed_from === "S1.verse_refs", "graph seed");
assert(
  doc.ui_public_layers.graph_component === "LogosResearchAskGraphPanel",
  "graph component",
);
assert(
  doc.ui_public_layers.layout_order?.[0] === "citation_lock_strip",
  "layout starts citation lock",
);
assert(doc.forbidden_public_labels.includes("repair_v2"), "repair_v2 forbidden");

console.log(
  JSON.stringify({
    ok: true,
    contract: CONTRACT,
    ui_public_layers: doc.ui_public_layers.trust_order_ko,
    stream_events: doc.ui_public_layers.stream_events,
  }),
);
