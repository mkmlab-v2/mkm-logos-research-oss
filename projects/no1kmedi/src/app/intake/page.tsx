import type { Metadata } from "next";
import { ClinicIntakeMobileWizard } from "@/components/ClinicIntakeMobileWizard";

export const metadata: Metadata = {
  title: "한의원 사전 문진 · JEMA AI",
  description:
    "접수 전 증상·생활습관 설문입니다. 체질을 몰라도 괜찮습니다. 진단·처방이 아닌 상담 준비용입니다.",
  alternates: { canonical: "/intake" },
};

export default function IntakePage() {
  return (
    <main className="clinic-intake-page">
      <header className="clinic-intake-page-bar">
        <a className="clinic-intake-page-brand" href="/">
          JEMA AI
        </a>
        <span className="clinic-intake-page-title">사전 문진</span>
      </header>
      <ClinicIntakeMobileWizard />
    </main>
  );
}
