#!/usr/bin/env node
/**
 * Smoke: POST /api/myeongni/studio-mindmap-v1 (verify-lite → mindmap_input).
 * Requires dev server + MKM_WORKSPACE_ROOT for Python engine.
 */
const baseUrl = (process.env.NO1KMEDI_BASE_URL || "http://127.0.0.1:3020").replace(/\/$/, "");

async function main() {
  const res = await fetch(`${baseUrl}/api/myeongni/studio-mindmap-v1`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      query: "올해 흐름은?",
      year: 1991,
      month: 3,
      day: 10,
      hour: 11,
      minute: 10,
      tz: "Asia/Seoul",
      is_male: true,
      is_solar: true,
    }),
  });
  const json = await res.json().catch(() => ({}));
  if (!res.ok || !json.success) {
    console.error("[smoke:myeongni-studio-mindmap] failed", res.status, json);
    process.exit(1);
  }
  const pillars = json.mindmap_input?.pillars;
  if (!pillars?.day) {
    console.error("[smoke:myeongni-studio-mindmap] missing mindmap_input.pillars", json);
    process.exit(1);
  }
  if (json.send_gate !== "HOLD") {
    console.error("[smoke:myeongni-studio-mindmap] send_gate must be HOLD");
    process.exit(1);
  }
  if (json.boundary_warning !== true && json.gate_status === "REVIEW") {
    console.warn("[smoke:myeongni-studio-mindmap] note: REVIEW without boundary_warning flag");
  }
  console.log("[smoke:myeongni-studio-mindmap] ok", pillars.day, json.gate_status, json.boundary_warning);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
