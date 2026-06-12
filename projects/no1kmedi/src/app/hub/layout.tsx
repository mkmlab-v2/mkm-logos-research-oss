import type { Metadata } from "next";
import { HubShellClient } from "@/components/shell/HubShellClient";

export const metadata: Metadata = {
  title: "JEMA AI Hub — One Question",
  description:
    "통합 허브: 중앙 원퀘스천 + 플러그인 라우터. 무한 채팅이 아닌 단발 리포트 · research_only.",
  robots: { index: true, follow: true },
};

export default function HubLayout({ children }: { children: React.ReactNode }) {
  return <HubShellClient>{children}</HubShellClient>;
}
