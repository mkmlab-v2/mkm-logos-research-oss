/**
 * Offline smoke: Paste Chart Omni-box extract heuristics.
 * Run: npx --yes tsx ./scripts/smoke-clinician-chart-paste-extract-v1.ts
 */

import {
  birthdateToBirthInstantUtc,
  extractPasteChartDraftV1,
  formatPasteExtractChipLabel,
} from "../src/lib/clinician-chart-paste-extract-v1";

function assert(cond: boolean, msg: string) {
  if (!cond) throw new Error(msg);
}

const sample1 = extractPasteChartDraftV1(
  "환자명: 이희철\n1990.03.15 남\n식후 더부룩함 2주 · 피로",
);
assert(sample1.display_name === "이희철", "name from label");
assert(sample1.birthdate === "1990-03-15", "birthdate full");
assert(sample1.sex === "M" || sample1.sex === "unknown", "sex");
assert(sample1.confidence === "high", "high confidence");
assert(Boolean(sample1.chief_complaint?.includes("더부룩")), "chief complaint");

const sample2 = extractPasteChartDraftV1("90년생 남성 이○○ 원장님 소개로 내원 · 상열감");
assert(sample2.display_name === undefined || sample2.confidence === "low", "ambiguous name low");
assert(sample2.birthdate === "1990-01-01", "90년생 birth");
assert(formatPasteExtractChipLabel(sample2).includes("?") || Boolean(sample2.display_name), "chip tolerates low");

const sample3 = extractPasteChartDraftV1("김민수 / 36세 남 / 요통 3주");
assert(sample3.display_name === "김민수", "inline name");
assert(sample3.age_years === 36, "age years");
assert(sample3.sex === "M", "inline sex");

const instant = birthdateToBirthInstantUtc("1990-03-15");
assert(Boolean(instant?.includes("T")), "birth instant iso");

console.log(
  JSON.stringify(
    {
      schema: "smoke_clinician_chart_paste_extract_v1",
      ok: true,
      samples: { sample1, sample2, sample3, instant },
    },
    null,
    2,
  ),
);
