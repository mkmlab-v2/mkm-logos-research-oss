import type { Metadata } from "next";
import { NationalKmAskClient } from "@/components/NationalKmAskClient";
import { NATIONAL_KM_ASK_V1 } from "@/lib/national-km-ask-v1";

export const metadata: Metadata = {
  title: `${NATIONAL_KM_ASK_V1.product_name_ko} · no1kmedi`,
  description:
    "대국민 한의학 이해·생활관리 참고 Q&A. 진단·처방·응급 판단을 대체하지 않습니다. 한의사는 clinic.no1kmedi.com 진료 보조 모드를 이용하세요.",
  alternates: { canonical: "/ask" },
};

export default function NationalKmAskPage() {
  return <NationalKmAskClient />;
}
