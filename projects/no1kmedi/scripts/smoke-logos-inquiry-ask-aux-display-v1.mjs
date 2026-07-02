/**
 * Verify research aux display helpers (gematria pin + sasang hint) — no numerology leak.
 * Run: npx --yes tsx ./scripts/smoke-logos-inquiry-ask-aux-display-v1.mjs [--base https://logos.jema-ai.com]
 */
import {
  gematriaPinAuxLine,
  researchAuxInsightLines,
  sasangHintAuxLine,
} from "../src/lib/logosInquiryAskDisplayV1.ts";

const baseIdx = process.argv.indexOf("--base");
const base = (
  process.argv.find((a) => a.startsWith("--base="))?.slice(7) ||
  (baseIdx >= 0 ? process.argv[baseIdx + 1] : "") ||
  ""
).replace(/\/$/, "");

function assert(cond, msg) {
  if (!cond) throw new Error(msg);
}

function unitSmoke() {
  const gemLine = gematriaPinAuxLine({
    path_token_preview: ["lemma_alpha", "Gematria_Pin:abcdef123456", "Jhn.19.34"],
  });
  assert(gemLine?.includes("게마트리아 핀 1건"), "gematria pin count");
  assert(gemLine?.includes("비공개"), "gematria security note");
  assert(!/\d{4,}/.test(gemLine ?? ""), "no long numerology in aux line");

  const sasLine = sasangHintAuxLine({
    regime_hint_b_track: {
      schema: "sasang_regime_hint_b_track_v1",
      research_only: true,
      non_gating: true,
      regime_hypothesis: "소음",
      mapping_target: "observation",
      token: "Sasang_Regime:소음",
      disclaimer_ko: "[HYPO][NON_GATING]",
    },
  });
  assert(sasLine?.includes("[HYPO][NON_GATING]"), "sasang hypo tag");
  assert(sasLine?.includes("소음"), "sasang hypothesis");

  const both = researchAuxInsightLines(
    { path_token_preview: ["Gematria_Pin:aa11bb22cc33"] },
    {
      regime_hint_b_track: {
        schema: "sasang_regime_hint_b_track_v1",
        research_only: true,
        non_gating: true,
        regime_hypothesis: "태양",
        mapping_target: null,
        token: "Sasang_Regime:태양",
        disclaimer_ko: "",
      },
    },
  );
  assert(both.length === 2, "both aux lines");
  return { unit_ok: true, gemLine, sasLine, both };
}

async function liveSmoke() {
  if (!base) return { live_skipped: true };
  const res = await fetch(`${base}/api/logos-research/query`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "User-Agent": "MKM-LogosInquiryAuxSmoke/1.0",
    },
    body: JSON.stringify({
      query: "요한복음 19장 옆구리에서 나온 피와 물의 의미",
      output_format: "inquiry_report_v1",
      stream_s4: false,
      domain_lane: "logos",
      intent_chip: "reports",
    }),
  });
  if (!res.ok) {
    return { live_ok: false, status: res.status };
  }
  const data = await res.json();
  const s2 = data.report?.sections?.S2;
  const s3 = data.report?.sections?.S3;
  const aux = researchAuxInsightLines(s2, s3);
  return {
    live_ok: true,
    aux_count: aux.length,
    aux_preview: aux,
    pin_count: (s2?.path_token_preview ?? []).filter((t) => /^Gematria_Pin:/i.test(t)).length,
    has_sasang: Boolean(s3?.regime_hint_b_track),
  };
}

async function main() {
  const unit = unitSmoke();
  const live = await liveSmoke();
  const ok = unit.unit_ok && (live.live_skipped || live.live_ok);
  console.log(JSON.stringify({ ok, unit, live }, null, 2));
  process.exit(ok ? 0 : 1);
}

main().catch((err) => {
  console.error(JSON.stringify({ ok: false, error: String(err) }));
  process.exit(1);
});
