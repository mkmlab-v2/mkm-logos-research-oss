import type { Metadata, Viewport } from "next";

export const metadata: Metadata = {
  title: "PersonaDiary | 내 기지 — Pull-first",
  description:
    "4레인 · 주간 5 · 지금 1타 · 로컬 일기. preview_only · 푸시 없음 · 서버 일기 저장 없음.",
  alternates: { canonical: "/personadiary/ops" },
  appleWebApp: {
    capable: true,
    title: "PersonaDiary",
    statusBarStyle: "black-translucent",
  },
};

export const viewport: Viewport = {
  themeColor: "#000000",
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default function PersonadiaryOpsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
