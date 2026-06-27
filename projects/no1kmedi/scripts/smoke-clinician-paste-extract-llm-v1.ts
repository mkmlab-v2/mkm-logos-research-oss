/**
 * Offline smoke: paste-extract LLM gate (disabled by default).
 * Run: npx --yes tsx ./scripts/smoke-clinician-paste-extract-llm-v1.ts
 */

import { extractPasteChartDraftLlmV1, pasteExtractLlmEnabled } from "../src/lib/clinician-paste-extract-llm-v1";

function assert(cond: unknown, msg: string): asserts cond {
  if (!cond) throw new Error(msg);
}

async function main() {
  assert(!pasteExtractLlmEnabled(), "default env should keep LLM extract off");
  const off = await extractPasteChartDraftLlmV1("김민수 / 36세 남 / 요통 3주");
  assert(!off.ok && off.error === "paste_extract_llm_disabled", "disabled gate");
  assert(off.regex_baseline?.display_name === "김민수", "regex baseline preserved");

  console.log(
    JSON.stringify(
      {
        schema: "smoke_clinician_paste_extract_llm_v1",
        ok: true,
        llm_enabled: pasteExtractLlmEnabled(),
      },
      null,
      2,
    ),
  );
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
