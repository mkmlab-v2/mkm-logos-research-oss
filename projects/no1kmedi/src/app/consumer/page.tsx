import type { Metadata } from "next";
import { Suspense } from "react";
import { ConsumerWorkspaceClient } from "./ConsumerWorkspaceClient";

export const metadata: Metadata = {
  title: "일반인 상담 · JEMA AI",
  description: "상담 전 참고용 안내와 사전문진 연결을 제공하는 보조 화면입니다. 의료행위를 대체하지 않습니다.",
  alternates: { canonical: "/consumer" },
};

export default function ConsumerPage() {
  return (
    <Suspense
      fallback={
        <div className="workspace-fallback" role="status" aria-live="polite">
          화면을 불러오는 중…
        </div>
      }
    >
      <ConsumerWorkspaceClient />
    </Suspense>
  );
}
