/** Map saju_myeongni_lite_enrich_v1 / verify-lite payload → mindmap input. */

import type { MyeongniLiteMindmapInput } from "@/lib/myeongniPathMindmapV1";

function record(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

function str(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

function num(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function pillarsFromLite(lite: Record<string, unknown>): MyeongniLiteMindmapInput["pillars"] {
  const pillars = record(lite.pillars);
  if (pillars) {
    return {
      year: str(pillars.year),
      month: str(pillars.month),
      day: str(pillars.day),
      hour: str(pillars.hour),
    };
  }
  return {
    year: str(lite.year_pillar ?? lite.year),
    month: str(lite.month_pillar ?? lite.month),
    day: str(lite.day_pillar ?? lite.day),
    hour: str(lite.hour_pillar ?? lite.hour),
  };
}

export function myeongniLiteRecordToMindmapInput(
  query: string,
  lite: Record<string, unknown> | null | undefined,
): MyeongniLiteMindmapInput | null {
  if (!lite) return null;

  const pillars = pillarsFromLite(lite);
  if (!pillars?.year && !pillars?.day) return null;

  const dae = record(lite.daewoon_current);
  const sew = record(lite.sewoon_current);
  const tg = record(lite.ten_god_lite);
  const oheng = record(lite.oheng_visible);
  const strength = record(lite.strength_hint);

  const countsRaw = tg?.counts_combined_ko ?? tg?.counts_surface_ko;
  const counts =
    countsRaw && typeof countsRaw === "object" && !Array.isArray(countsRaw)
      ? (countsRaw as Record<string, number>)
      : undefined;

  return {
    query: query.trim() || "명리 질의",
    pillars,
    daewoon_current: dae
      ? {
          pillar: str(dae.pillar ?? dae.saju),
          age_start: num(dae.age_start),
          age_end: num(dae.age_end),
        }
      : null,
    sewoon_current: sew
      ? {
          calendar_year: num(sew.calendar_year),
          pillar: str(sew.pillar),
        }
      : null,
    ten_god_lite: counts ? { counts_combined_ko: counts } : undefined,
    oheng_visible: oheng
      ? {
          dominant_element_visible: str(oheng.dominant_element_visible),
          weakest_element_visible: str(oheng.weakest_element_visible),
        }
      : undefined,
    strength_hint: strength
      ? {
          strength_label: str(strength.strength_label),
        }
      : undefined,
  };
}

export const MYEONGNI_FULL_REPORT_SSOT = {
  script: "scripts/build_myeongni_full_report_v1.py",
  schema: "myeongni_full_report_v1",
  note_ko:
    "마인드맵은 lite(enrich)만 사용합니다. 월운·용신·임상 해석은 풀 리포트 SSOT·한의사 human_confirm 경로를 따릅니다.",
} as const;
