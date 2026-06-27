import type { Metadata } from "next";

import { logosResearchCopy } from "@/content/logosResearchCopy";

const logosBase = logosResearchCopy.publicUrl.replace(/\/$/, "");

const docsDescription =
  "Graph Studio, citation lock, pilot scope, and glossary. HYPO · research_only · NON_GATING · send_gate HOLD.";

export const metadata: Metadata = {
  metadataBase: new URL(logosBase),
  title: {
    default: "Logos Public Docs — JEMA AI",
    template: "%s — Logos Public Docs",
  },
  description: docsDescription,
  alternates: {
    canonical: "/logos-research/docs",
  },
  openGraph: {
    title: "Logos Public Docs — JEMA AI",
    description: docsDescription,
    url: `${logosBase}/logos-research/docs`,
    siteName: logosResearchCopy.brand.productLine,
    locale: "ko_KR",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Logos Public Docs — JEMA AI",
    description: docsDescription,
  },
};

export default function LogosResearchDocsLayout({ children }: { children: React.ReactNode }) {
  return children;
}
