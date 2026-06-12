/**
 * Fail if homepage still embeds known marketing literals (should live in public-copy.json).
 * Run: node scripts/check-homepage-marketing-copy-wired_v1.mjs
 */
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const pagePath = join(root, "src/app/page.tsx");
const homeRoutePath = join(root, "src/app/home/page.tsx");
const homeComponentPath = join(root, "src/components/MarketingLegacyHomePage.tsx");
const page = readFileSync(pagePath, "utf8");
const homeRoute = readFileSync(homeRoutePath, "utf8");
const homeComponent = readFileSync(homeComponentPath, "utf8");

const bannedLiterals = [
  "본문으로 건너뛰기",
  "근거 출처 매핑",
  "핵심 역량",
  "브랜드 모션 특징",
  "신뢰 지표",
  "Why MKM AI?",
  "일반인 홍보·상담 안내와 한의사",
  "무료 검증 신청",
  "월 30회 샘플 검증",
];

const marketingSurfaces = [page, homeRoute, homeComponent].join("\n");
const hits = bannedLiterals.filter((s) => marketingSurfaces.includes(s));
if (hits.length) {
  console.error("[check-homepage-marketing-copy-wired_v1] hardcoded literals in homepage surfaces:");
  for (const h of hits) console.error(`  - ${h}`);
  process.exit(1);
}

const wiredSource =
  page.includes("MarketingLegacyHomePage") || homeRoute.includes("MarketingLegacyHomePage")
    ? homeComponent
    : page;
if (!wiredSource.includes("c.homepage_a11y") || !wiredSource.includes("c.why_mkm_ai")) {
  console.error(
    "[check-homepage-marketing-copy-wired_v1] homepage missing c.homepage_a11y / c.why_mkm_ai wiring",
  );
  process.exit(1);
}

console.log("[check-homepage-marketing-copy-wired_v1] passed.");
process.exit(0);
