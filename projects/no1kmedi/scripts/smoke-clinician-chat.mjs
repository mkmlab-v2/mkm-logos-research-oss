#!/usr/bin/env node
/**
 * Smoke: clinician-session bootstrap + guardian clinician chat (Gemini-like path).
 */
// localhost avoids Windows fetch-to-127.0.0.1 quirks on some Node builds
const BASE_URL = process.env.NO1KMEDI_BASE_URL || "http://localhost:3010";

function assert(cond, msg) {
  if (!cond) throw new Error(msg);
}

async function parseJsonResponse(path, res, text) {
  try {
    return JSON.parse(text);
  } catch {
    const snippet = text.replace(/\s+/g, " ").trim().slice(0, 120);
    throw new Error(`${path} non-JSON HTTP ${res.status}: ${snippet}`);
  }
}

async function get(path) {
  const res = await fetch(`${BASE_URL}${path}`, { cache: "no-store" });
  const text = await res.text();
  const json = await parseJsonResponse(path, res, text);
  return { res, json };
}

async function post(path, body) {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const text = await res.text();
  const json = await parseJsonResponse(path, res, text);
  return { res, json };
}

async function main() {
  const session = await get("/api/member/clinician-session");
  assert(session.res.status === 200, `clinician-session status ${session.res.status}`);
  assert(session.json?.success === true, "clinician-session success");

  const demo = await get("/api/clinician/demo-patient?slug=park_geumja");
  assert(demo.res.status === 200, `demo-patient status ${demo.res.status}`);
  assert(demo.json?.success === true, "demo-patient success");
  assert(
    demo.json?.slug || demo.json?.context_patch?.ssotSlug,
    "demo-patient slug",
  );

  const chat = await post("/api/guardian/ai-guardian/chat", {
    audience: "clinician",
    message: "만성 피로와 수면 장애가 3개월째입니다. 문진 포인트를 짧게 알려주세요.",
    chat_history: [],
    patient_context: {
      chief_complaint: "만성 피로",
      onset: "3개월",
      severity: "중등도",
    },
    health_data: { survey: { vector_4d: { S: 0.25, L: 0.25, K: 0.25, M: 0.25 } } },
  });

  if (chat.res.status === 200 && chat.json?.success && chat.json?.response) {
    console.log("OK clinician chat:", chat.json.response.slice(0, 120).replace(/\s+/g, " "), "…");
    console.log(
      JSON.stringify(
        { session: session.json, demo_slug: demo.json?.slug ?? demo.json?.context_patch?.ssotSlug, provider: chat.json.meta },
        null,
        2,
      ),
    );
    return;
  }

  if (chat.res.status >= 500) {
    console.warn(
      "WARN: chat returned",
      chat.res.status,
      chat.json?.error,
      "— set GEMINI_API_KEY or OPENROUTER_API_KEY in projects/no1kmedi/.env.local",
    );
    console.log(JSON.stringify({ session: session.json, chat: chat.json }, null, 2));
    return;
  }

  throw new Error(`unexpected chat response: ${chat.res.status} ${JSON.stringify(chat.json)}`);
}

main().catch((e) => {
  console.error(e.message || e);
  process.exit(1);
});
