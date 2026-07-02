/**
 * Self-verify /logos-research/ask UI contract: inquiry_report_v1 + SSE S4 body.
 * Run: node ./scripts/smoke-logos-inquiry-ask-ui-v1.mjs [--base http://localhost:3010]
 */
import { consumeLogosInquirySse } from "../src/lib/logosInquiryStreamClientV1.ts";

const base = (() => {
  const eq = process.argv.find((a) => a.startsWith("--base="));
  if (eq) return eq.slice(7).replace(/\/$/, "");
  const idx = process.argv.indexOf("--base");
  if (idx >= 0 && process.argv[idx + 1] && !process.argv[idx + 1].startsWith("-")) {
    return process.argv[idx + 1].replace(/\/$/, "");
  }
  return "http://127.0.0.1:3010";
})();

const query = "시편 23편 — lemma·경로 관점에서 연구 질문을 구체화해 달라";

async function main() {
  const res = await fetch(`${base}/api/logos-research/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query,
      output_format: "inquiry_report_v1",
      stream_s4: true,
      domain_lane: "logos",
      intent_chip: "reports",
    }),
  });

  if (!res.ok) {
    const text = await res.text();
    console.error(JSON.stringify({ ok: false, step: "http", status: res.status, text: text.slice(0, 400) }));
    process.exit(1);
  }

  const ct = res.headers.get("content-type") || "";
  if (!ct.includes("text/event-stream")) {
    console.error(JSON.stringify({ ok: false, step: "content_type", ct }));
    process.exit(1);
  }

  let snapshot = false;
  let deltaChars = 0;
  let s4Body = "";
  let doneReport = null;

  await consumeLogosInquirySse(res, {
    onSnapshot: () => {
      snapshot = true;
    },
    onS4Delta: (text) => {
      deltaChars += text.length;
    },
    onS4Done: (body) => {
      s4Body = body;
    },
    onDone: (report) => {
      doneReport = report;
    },
  });

  const finalBody = doneReport?.sections?.S4?.body_ko || s4Body || "";
  const ok = snapshot && finalBody.trim().length > 20;
  console.log(
    JSON.stringify({
      ok,
      base,
      snapshot,
      delta_chars: deltaChars,
      s4_len: finalBody.length,
      s4_preview: finalBody.slice(0, 120),
    }),
  );
  process.exit(ok ? 0 : 1);
}

main().catch((err) => {
  console.error(JSON.stringify({ ok: false, error: String(err) }));
  process.exit(1);
});
