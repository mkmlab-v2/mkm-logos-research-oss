import type { Metadata } from "next";
import { SiteHeader } from "@/components/SiteHeader";
import { PatientPreSurveyForm } from "@/components/PatientPreSurveyForm";
import { siteCopy } from "@/content/siteCopy";

export const metadata: Metadata = {
  title: "한의원 사전 문진 · JEMA AI",
  description:
    "접수 전 증상·체질·생활습관 설문입니다. 진단·처방이 아닌 상담 준비용이며, 최종 판단은 한의사가 수행합니다.",
  alternates: { canonical: "/intake" },
};

export default function IntakePage() {
  const c = siteCopy;
  return (
    <>
      <SiteHeader nav={c.nav} brand={c.header} links={c.links} />
      <main className="workspace-scroll-panel" style={{ maxWidth: "48rem", margin: "0 auto", padding: "1.5rem 1rem 3rem" }}>
        <PatientPreSurveyForm intakeMode="clinic_v1" />
      </main>
    </>
  );
}
