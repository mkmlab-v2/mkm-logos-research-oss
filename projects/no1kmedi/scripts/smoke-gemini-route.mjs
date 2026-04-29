#!/usr/bin/env node
/* eslint-disable no-console */
const BASE_URL = (process.env.NO1KMEDI_BASE_URL || "http://127.0.0.1:3010").replace(/\/$/, "");

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

async function request(path, init) {
  const res = await fetch(`${BASE_URL}${path}`, init);
  const text = await res.text();
  let json;
  try {
    json = JSON.parse(text);
  } catch {
    json = { raw: text };
  }
  return { res, json };
}

async function main() {
  const guardian = await request("/api/guardian/ai-guardian/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message: "오늘 컨디션 기준으로 짧은 생활 관리 조언 부탁해",
      health_data: { survey: { vector_4d: { S: 0.31, L: 0.22, K: 0.27, M: 0.20 } } },
      chat_history: [],
    }),
  });

  assert(guardian.res.status === 200, `guardian route expected 200, got ${guardian.res.status}`);
  assert(guardian.json?.success === true, "guardian success must be true");
  const provider = String(guardian.json?.meta?.provider || "");
  assert(provider.length > 0, "guardian provider missing");
  assert(
    provider.toLowerCase().startsWith("gemini:"),
    `guardian provider is not gemini route: provider=${provider}`
  );

  console.log(
    JSON.stringify(
      {
        ok: true,
        base_url: BASE_URL,
        guardian_provider: provider,
      },
      null,
      2
    )
  );
}

main().catch((error) => {
  console.error("[smoke:gemini-route] failed:", error.message);
  process.exit(1);
});
