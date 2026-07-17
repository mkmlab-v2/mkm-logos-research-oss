import type { Metadata } from "next";

import { logosResearchCopy } from "@/content/logosResearchCopy";

const logosBase = logosResearchCopy.publicUrl.replace(/\/$/, "");

/** Cap Next ISR default (s-maxage=31536000) so brand/copy deploys don't leave 1-year stale HTML. */
export const revalidate = 3600;

export const metadata: Metadata = {
  metadataBase: new URL(logosBase),
  title: "LOGOS — 성경 연구 워크스페이스",
  description:
    "성경 질문 → 인용 근거·학파 비교 리포트. Public Beta · 연구 참고 · 무료 쿼터. 투자·실거래 조언 아님.",
  alternates: {
    canonical: "/logos-research",
  },
  openGraph: {
    title: "LOGOS — 성경 연구 워크스페이스",
    description: "구절 인용과 학파별 해석을 한 리포트로. Public Beta · 연구 참고.",
    url: `${logosBase}/logos-research`,
    siteName: logosResearchCopy.brand.productShort,
    locale: "ko_KR",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "LOGOS — 성경 연구 워크스페이스",
    description: "구절 인용과 학파별 해석을 한 리포트로. Public Beta · 연구 참고.",
  },
};

export default function LogosResearchLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <link rel="preconnect" href="https://fonts.googleapis.com" />
      <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      <link
        href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Source+Serif+4:opsz,wght@8..60,500;8..60,600&display=swap"
        rel="stylesheet"
      />
      {children}
    </>
  );
}
