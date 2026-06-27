import type { ChartPasteSection } from "@/components/ClinicianChartPastePanel";
import { buildSoapStubFromConsultDraft } from "@/lib/clinician-consult-payload-v1";

const SOAP_LABELS: Record<string, string> = {
  subjective: "S · 주관적 소견",
  objective: "O · 객관적 소견",
  assessment: "A · 평가·변증",
  plan: "P · 계획",
};

export function buildChartPasteSectionsFromSoapStub(
  soap: Record<string, { text?: string } | string>,
): ChartPasteSection[] {
  const sections: ChartPasteSection[] = [];
  for (const [id, label] of Object.entries(SOAP_LABELS)) {
    const raw = soap[id];
    const text =
      typeof raw === "string" ? raw.trim() : String((raw as { text?: string })?.text || "").trim();
    if (!text) continue;
    sections.push({
      id,
      title: label,
      hint: "한의사랑 SOAP 해당 칸에 붙여넣기",
      text,
    });
  }
  return sections;
}

export function buildChartPasteSectionsFromCdsDraft(draft: {
  clinical_summary: string;
  reasoning: { syndrome_hypothesis: string; care_direction: string; caution: string };
}): ChartPasteSection[] {
  return buildChartPasteSectionsFromSoapStub(buildSoapStubFromConsultDraft(draft));
}

export function buildChartPasteSectionsFromBundle(bundle: Record<string, unknown>): ChartPasteSection[] {
  const clinical = bundle.clinical_soap_v1;
  if (clinical && typeof clinical === "object") {
    return buildChartPasteSectionsFromSoapStub(clinical as Record<string, { text?: string }>);
  }
  return [];
}

export function mergeChartPasteSections(...groups: ChartPasteSection[][]): ChartPasteSection[] {
  const seen = new Set<string>();
  const out: ChartPasteSection[] = [];
  for (const group of groups) {
    for (const section of group) {
      if (!section.text.trim() || seen.has(section.id)) continue;
      seen.add(section.id);
      out.push(section);
    }
  }
  return out;
}
