import type { Metadata } from "next";
import { NationalKmAskClient } from "@/components/NationalKmAskClient";
import { NATIONAL_KM_ASK_V1 } from "@/lib/national-km-ask-v1";
import { NATIONAL_KM_ASK_CANONICAL_URL } from "@/lib/no1kmedi-portal-host";

export const metadata: Metadata = {
  title: `${NATIONAL_KM_ASK_V1.product_name_ko} · JEMA`,
  description: NATIONAL_KM_ASK_V1.meta_description_ko,
  alternates: { canonical: NATIONAL_KM_ASK_CANONICAL_URL },
};

export default function NationalKmAskPage() {
  return <NationalKmAskClient />;
}
