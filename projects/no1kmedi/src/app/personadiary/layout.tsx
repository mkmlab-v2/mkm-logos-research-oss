import type { Metadata } from "next";
import { PersonadiaryMkmAuthBridge } from "@/components/personadiary/PersonadiaryMkmAuthBridge";
import { personadiaryCopy } from "@/content/personadiaryCopy";

const hubBase =
  process.env.NEXT_PUBLIC_JEMA_HUB_URL?.trim() || "https://jema-ai.com";

export const metadata: Metadata = {
  metadataBase: new URL(hubBase),
  title: personadiaryCopy.seo.title,
  description: personadiaryCopy.seo.description,
  alternates: { canonical: "/personadiary" },
  openGraph: {
    title: personadiaryCopy.seo.title,
    description: personadiaryCopy.seo.description,
    url: `${hubBase}/personadiary`,
    siteName: personadiaryCopy.brand.name,
    locale: "ko_KR",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: personadiaryCopy.seo.title,
    description: personadiaryCopy.seo.description,
  },
};

export default function PersonadiaryLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <>
      <PersonadiaryMkmAuthBridge />
      {children}
    </>
  );
}
