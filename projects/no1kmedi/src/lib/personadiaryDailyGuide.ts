import { readFile } from "fs/promises";
import path from "path";

export type DailyGuideBlock = {
  type: string;
  title_ko: string;
  body_ko?: string;
  ref?: string;
  badge_ko?: string;
};

export type DailyGuidePackage = {
  schema?: string;
  calendar_kst?: string;
  concept_ko?: string;
  ui_blocks?: DailyGuideBlock[];
  reflect_template_ko?: string;
  disclaimer_ko?: string;
};

function normalizeProfileId(raw: string | null | undefined): string {
  const id = (raw || process.env.NEXT_PUBLIC_PERSONADIARY_PROFILE_ID || "commander")
    .trim()
    .toLowerCase();
  if (!/^[a-z0-9_-]{1,32}$/.test(id)) {
    return "commander";
  }
  return id;
}

export async function resolveDailyGuidePath(
  profileId?: string | null
): Promise<string | null> {
  const pid = normalizeProfileId(profileId);
  const cwd = process.cwd();
  const candidates = [
    path.join(cwd, "public", "data", "profiles", `${pid}.json`),
    path.join(cwd, "public", "data", "personadiary_daily_response_package_v1.json"),
    process.env.PERSONADIARY_DAILY_PACKAGE_JSON?.trim(),
    process.env.MKM_WORKSPACE_ROOT
      ? path.join(
          process.env.MKM_WORKSPACE_ROOT.trim(),
          "docs/final/artifacts/personadiary_daily_response_package_v1_latest.json"
        )
      : "",
    path.resolve(cwd, "..", "..", "docs/final/artifacts/personadiary_daily_response_package_v1_latest.json"),
    path.resolve(cwd, "..", "..", "..", "docs/final/artifacts/personadiary_daily_response_package_v1_latest.json"),
  ].filter((p): p is string => Boolean(p && p.length > 0));

  for (const p of candidates) {
    try {
      await readFile(p, "utf8");
      return p;
    } catch {
      /* next */
    }
  }
  return null;
}

export async function loadDailyGuidePackage(
  profileId?: string | null
): Promise<DailyGuidePackage | null> {
  const filePath = await resolveDailyGuidePath(profileId);
  if (!filePath) return null;
  const raw = await readFile(filePath, "utf8");
  const doc = JSON.parse(raw) as DailyGuidePackage;
  if (doc.schema !== "personadiary_daily_response_package_v1") return null;
  return doc;
}

export function buildReflectionText(
  pkg: DailyGuidePackage,
  userText: string
): string {
  const snippet =
    userText.trim().length > 120
      ? `${userText.trim().slice(0, 120)}…`
      : userText.trim();
  const template = pkg.reflect_template_ko;
  if (template && template.includes("{user}")) {
    return template.replace("{user}", snippet);
  }
  return `오늘 당신이 남긴 마음: "${snippet}" — 구슬은 가이드형 성찰만 비춥니다.`;
}
