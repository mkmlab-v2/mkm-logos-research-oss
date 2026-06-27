import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { siteCopy } from "@/content/siteCopy";
import { WellnessEntryClient } from "./WellnessEntryClient";

const wellness = siteCopy.patient_wellness_entry;

export const metadata: Metadata = wellness
  ? {
      title: wellness.seo.title,
      description: wellness.seo.description,
      alternates: { canonical: "/wellness" },
    }
  : {
      title: "환자 웰니스 | JEMA AI",
      description: "비진단 · 일상 리듬·성찰 참고 안내.",
    };

export default function WellnessPage() {
  if (!wellness) notFound();

  return (
    <WellnessEntryClient
      copy={wellness}
      site={{
        header: siteCopy.header,
        nav: siteCopy.nav,
        links: siteCopy.links,
        hub_links: siteCopy.hub_links,
        footer: siteCopy.footer,
      }}
    />
  );
}
