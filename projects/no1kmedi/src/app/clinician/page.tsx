import type { Metadata } from "next";
import { headers } from "next/headers";
import { Suspense } from "react";
import { normalizeRequestHost, shouldUseMinimalClinicianShell } from "@/lib/no1kmedi-portal-host";
import { ClinicianWorkspaceClient } from "./ClinicianWorkspaceClient";

export const metadata: Metadata = {
  title: "한의사 보조 · JEMA AI",
  description:
    "대화 중심 CDSS·SOAP 초안·환자 번들 보조 화면입니다. 참고·초안용이며 최종 진단·처방은 한의사가 확정합니다.",
  alternates: { canonical: "/clinician" },
};

export default function ClinicianPage() {
  const host = normalizeRequestHost(headers().get("host"));
  const minimalShell = shouldUseMinimalClinicianShell(host);

  return (
    <>
      <div data-clinician-pilot-route="v2" data-clinician-sidebar-mode="gpt-persist" hidden aria-hidden="true" />
      <Suspense
        fallback={
          <div className="workspace-fallback" role="status" aria-live="polite">
            화면을 불러오는 중…
          </div>
        }
      >
        <ClinicianWorkspaceClient minimalShell={minimalShell} />
      </Suspense>
    </>
  );
}
