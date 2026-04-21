import type { Metadata } from "next";
import { Suspense } from "react";
import { ClinicianWorkspaceClient } from "./ClinicianWorkspaceClient";

export const metadata: Metadata = {
  title: "한의사 임상 보조 · JEMA AI",
  description: "근거 기반 진료 준비 초안과 안전 고지를 제공하는 보조 화면입니다. 최종 진단·처방은 의료진이 확정합니다.",
  alternates: { canonical: "/clinician" },
};

export default function ClinicianPage() {
  return (
    <Suspense
      fallback={
        <div className="workspace-fallback" role="status" aria-live="polite">
          화면을 불러오는 중…
        </div>
      }
    >
      <ClinicianWorkspaceClient />
    </Suspense>
  );
}
