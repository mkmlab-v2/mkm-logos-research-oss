#!/usr/bin/env node
const url = process.env.ATHENA_MANSERYEOK_API_URL;
const token = process.env.ATHENA_MANSERYEOK_API_TOKEN?.trim();

function fail(message) {
  console.error(`check-manseryeok-live-env failed: ${message}`);
  process.exit(1);
}

async function main() {
  if (!url) fail("ATHENA_MANSERYEOK_API_URL is required");

  let parsed;
  try {
    parsed = new URL(url);
  } catch {
    fail("ATHENA_MANSERYEOK_API_URL must be a valid URL");
  }

  if (!["http:", "https:"].includes(parsed.protocol)) {
    fail("ATHENA_MANSERYEOK_API_URL must use http/https");
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 10_000);
  try {
    const res = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { "x-api-token": token } : {}),
      },
      body: JSON.stringify({
        birth_instant_utc: "1987-12-31T15:00:00Z",
        iana_tz: "Asia/Seoul",
        birth_datetime: "1988-01-03 06:30",
      }),
      signal: controller.signal,
    });
    if (!res.ok) fail(`endpoint probe failed with status ${res.status}`);

    const json = await res.json();
    if (!json || typeof json.saju_label !== "string" || json.saju_label.trim().length === 0) {
      fail("endpoint must return a non-empty saju_label");
    }
  } catch (error) {
    fail(error.message);
  } finally {
    clearTimeout(timeout);
  }

  console.log("check-manseryeok-live-env passed");
}

main();
