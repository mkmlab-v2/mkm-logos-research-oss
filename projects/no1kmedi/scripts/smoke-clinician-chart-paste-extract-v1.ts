/**
 * Offline smoke: Paste Chart Omni-box extract heuristics.
 * Run: npx --yes tsx ./scripts/smoke-clinician-chart-paste-extract-v1.ts
 */

import {
  birthdateToBirthInstantUtc,
  buildStructuredIntakeFromPaste,
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

const sample4 = extractPasteChartDraftV1(
  "김민수 / 1988-03-12 / 남 / 36세 / 요통 3주\n\n[주소] 서울 강남\n[CC] 요추부 통증, 3주 전부터 악화. 앉아 있을 때 더 아픔.",
);
assert(sample4.display_name === "김민수", "slash header name");
assert(sample4.birthdate === "1988-03-12", "slash header birthdate");
assert(sample4.sex === "M", "slash header sex");
assert(sample4.age_years === 36, "slash header age");
assert(sample4.confidence === "high", "slash header high confidence");
assert(Boolean(sample4.chief_complaint?.includes("요추부 통증")), "chief from [CC] section");

const sample5Input =
  "김민수 / 1988-03-12 / 남 / 36세 / 요통 3주\n\n[주소] 서울 강남\n[CC] 요추부 통증, 3주 전부터 악화. 앉아 있을 때 더 아픔.\n[Hx] 진통제 병력";
const sample5 = buildStructuredIntakeFromPaste(sample5Input);
assert(sample5.symptoms[0]?.includes("요추부"), "structured chief symptom");
assert(sample5.symptoms.length === 1, "symptoms only CC chief");
assert(!sample5.symptoms.some((s) => s.includes("[주소]")), "symptoms exclude address tag");
assert(sample5.situation.includes("김민수"), "structured situation name");
assert(sample5.situation.includes("서울 강남"), "situation includes address body");
assert(!sample5.situation.includes("[CC]"), "situation excludes CC block");
assert(!sample5.subjective_notes.includes("[CC]"), "notes exclude CC block");
assert(sample5.subjective_notes.includes("[Hx]"), "notes include Hx once");
assert(!sample5.subjective_notes.startsWith("김민수 / 1988"), "notes skip slash header");

const instant = birthdateToBirthInstantUtc("1990-03-15");
assert(Boolean(instant?.includes("T")), "birth instant iso");

const sample6 =
  "김민정 1988.06.25 양력 서울 오후 4시 출생 여자 168에 58키로  혈압 120에 83/ 최근 불면, 설진상 습울, 상열, 안면 홍조, , 불면, 두통/ 생리통, 복직근 긴장. 중완 압통, 때떄로 타이레놀 복용/ 흉곽 예각 설하정맥 얇은 편, 수족 냉한 편/ 소음인 추정/";
const sample6Draft = extractPasteChartDraftV1(sample6);
assert(sample6Draft.display_name === "김민정", "freeform leading name");
assert(sample6Draft.birthdate === "1988-06-25", "freeform birthdate");
assert(sample6Draft.sex === "F", "freeform sex");
assert(sample6Draft.confidence === "high", "freeform name+birth high");
assert(Boolean(sample6Draft.chief_complaint?.includes("불면")), "freeform clinical chief");
assert(!sample6Draft.chief_complaint?.startsWith("김민정 1988"), "chief excludes demographics");
const sample6Structured = buildStructuredIntakeFromPaste(sample6);
assert(Boolean(sample6Structured.subjective_notes.trim()), "freeform subjective_notes");

console.log(
  JSON.stringify(
    {
      schema: "smoke_clinician_chart_paste_extract_v1",
      ok: true,
      samples: { sample1, sample2, sample3, sample6Draft, instant },
    },
    null,
    2,
  ),
);
