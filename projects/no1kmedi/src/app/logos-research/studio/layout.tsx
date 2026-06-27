import type { Metadata } from "next";

import { logosResearchCopy } from "@/content/logosResearchCopy";

const logosBase = logosResearchCopy.publicUrl.replace(/\/$/, "");

export const metadata: Metadata = {
  metadataBase: new URL(logosBase),
  title: "Graph Studio — Logos Scripture Research",
  description:
    "On-domain GraphRAG path workspace with citation lock. Track B HYPO · research_only · preset bundle.",
  alternates: {
    canonical: "/logos-research/studio",
  },
  manifest: "/logos-research/manifest.webmanifest",
  appleWebApp: {
    capable: true,
    title: "Logos Studio",
    statusBarStyle: "black-translucent",
  },
  icons: {
    apple: "/logos-research/icon-192.svg",
  },
};

export default function LogosResearchStudioLayout({ children }: { children: React.ReactNode }) {
  return children;
}
