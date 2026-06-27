import type { Metadata } from "next";

import { logosResearchCopy } from "@/content/logosResearchCopy";

const logosBase = logosResearchCopy.publicUrl.replace(/\/$/, "");

export const metadata: Metadata = {
  metadataBase: new URL(logosBase),
  title: "Logos Scripture Research — JEMA AI",
  description:
    "Cross-reference graph research workspace with citation lock. Track B HYPO · research_only · not investment or live trading advice.",
  alternates: {
    canonical: "/logos-research",
  },
  openGraph: {
    title: "Logos Scripture Research — JEMA AI",
    description:
      "Cross-reference graph · citation-locked Scripture research workspace. Track B [HYPO] · research_only.",
    url: `${logosBase}/logos-research`,
    siteName: logosResearchCopy.brand.productLine,
    locale: "ko_KR",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Logos Scripture Research — JEMA AI",
    description:
      "Cross-reference graph · citation-locked Scripture research workspace. Track B [HYPO] · research_only.",
  },
};

export default function LogosResearchLayout({ children }: { children: React.ReactNode }) {
  return children;
}
