import type { Metadata, Viewport } from "next";

import { SmartfarmOperatorClient } from "@/components/smartfarm/SmartfarmOperatorClient";
import { smartfarmOperatorCopy } from "@/content/smartfarmOperatorCopy";

const hubBase =
  process.env.NEXT_PUBLIC_JEMA_HUB_URL?.trim() || "https://jema-ai.com";

export const metadata: Metadata = {
  metadataBase: new URL(hubBase),
  title: smartfarmOperatorCopy.seo.title,
  description: smartfarmOperatorCopy.seo.description,
  alternates: {
    canonical: "/smartfarm/operator",
  },
  manifest: "/smartfarm-operator.webmanifest",
  appleWebApp: {
    capable: true,
    title: "MKM 농장운영",
    statusBarStyle: "black-translucent",
  },
};

export const viewport: Viewport = {
  themeColor: "#070d0b",
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
};

export default function SmartfarmOperatorPage() {
  return <SmartfarmOperatorClient />;
}
