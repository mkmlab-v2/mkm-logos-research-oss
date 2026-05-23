import type { Metadata } from "next";
import { smartfarmCopy } from "@/content/smartfarmCopy";

const hubBase =
  process.env.NEXT_PUBLIC_JEMA_HUB_URL?.trim() || "https://jema-ai.com";

export const metadata: Metadata = {
  metadataBase: new URL(hubBase),
  title: smartfarmCopy.seo.title,
  description: smartfarmCopy.seo.description,
  alternates: {
    canonical: "/smartfarm",
  },
  openGraph: {
    title: smartfarmCopy.seo.title,
    description: smartfarmCopy.seo.description,
    url: `${hubBase}/smartfarm`,
    siteName: smartfarmCopy.brand.product,
    locale: "ko_KR",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: smartfarmCopy.seo.title,
    description: smartfarmCopy.seo.description,
  },
};

export default function SmartfarmLayout({ children }: { children: React.ReactNode }) {
  return children;
}
