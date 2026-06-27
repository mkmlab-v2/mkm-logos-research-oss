/**
 * Paste Chart chip extract — LLM assist (server-only · Track B · human_confirm).
 * Falls back to regex draft on parse/LLM failure.
 */

import { generateClinicalText } from "@/lib/ai-provider";
import {
  extractPasteChartDraftV1,
  mergePasteExtractDraft,
  type PasteExtractDraftV1,
} from "@/lib/clinician-chart-paste-extract-v1";

export function pasteExtractLlmEnabled(): boolean {
  const v = (process.env.KM_CLINICIAN_PASTE_EXTRACT_LLM || "").trim().toLowerCase();
  return v === "1" || v === "true" || v === "yes" || v === "on";
}

type LlmChipJson = {
  display_name?: string;
  birthdate?: string;
  sex?: "M" | "F" | "unknown";
  age_years?: number;
  chief_complaint?: string;
};

function parseLlmJson(text: string): LlmChipJson | null {
  const trimmed = text.trim();
  const fence = trimmed.match(/```(?:json)?\s*([\s\S]*?)```/i);
  const raw = fence?.[1]?.trim() || trimmed;
  try {
    const parsed = JSON.parse(raw) as LlmChipJson;
    return parsed && typeof parsed === "object" ? parsed : null;
  } catch {
    const start = raw.indexOf("{");
    const end = raw.lastIndexOf("}");
    if (start < 0 || end <= start) return null;
    try {
      return JSON.parse(raw.slice(start, end + 1)) as LlmChipJson;
    } catch {
      return null;
    }
  }
}

function normalizeSex(raw?: string): "M" | "F" | "unknown" | undefined {
  if (!raw) return undefined;
  const t = raw.trim().toUpperCase();
  if (t === "M" || t === "MALE" || t === "남" || t === "남성") return "M";
  if (t === "F" || t === "FEMALE" || t === "여" || t === "여성") return "F";
  if (t === "UNKNOWN" || t === "U") return "unknown";
  return undefined;
}

export type PasteExtractLlmResult =
  | { ok: true; draft: PasteExtractDraftV1; provider: string; regex_baseline: PasteExtractDraftV1 }
  | { ok: false; error: string; regex_baseline?: PasteExtractDraftV1 };

export async function extractPasteChartDraftLlmV1(chartText: string): Promise<PasteExtractLlmResult> {
  const baseline = extractPasteChartDraftV1(chartText);
  if (!pasteExtractLlmEnabled()) {
    return { ok: false, error: "paste_extract_llm_disabled", regex_baseline: baseline };
  }

  const text = chartText.replace(/\r\n/g, "\n").trim().slice(0, 12000);
  if (!text) {
    return { ok: false, error: "chart_text_required", regex_baseline: baseline };
  }

  const systemInstruction = `You extract clinician paste-chart metadata for Korean EMR/chat snippets.
Return ONLY one JSON object with keys: display_name (string|omit), birthdate (YYYY-MM-DD|omit), sex (M|F|unknown|omit), age_years (number|omit), chief_complaint (short string|omit).
Do not diagnose. Do not invent data absent from the text. research_only human_confirm.`;

  const prompt = `Extract patient metadata chips from this pasted chart text:\n\n${text}`;

  try {
    const gen = await generateClinicalText({
      prompt,
      systemInstruction,
      temperature: 0.1,
      maxOutputTokens: 320,
      feature: "clinician_paste_extract_v1",
    });

    const parsed = parseLlmJson(gen.text);
    if (!parsed) {
      return { ok: false, error: "llm_json_parse_failed", regex_baseline: baseline };
    }

    const sex = normalizeSex(parsed.sex);
    const merged = mergePasteExtractDraft(baseline, {
      display_name: parsed.display_name?.trim() || undefined,
      birthdate: parsed.birthdate?.trim() || undefined,
      sex: sex || undefined,
      age_years:
        typeof parsed.age_years === "number" && Number.isFinite(parsed.age_years)
          ? Math.round(parsed.age_years)
          : undefined,
      chief_complaint: parsed.chief_complaint?.trim().slice(0, 800) || undefined,
      sources: [...baseline.sources, "llm_chip_extract_v1"],
      confidence: "low",
    });

    if (merged.display_name && (merged.birthdate || (merged.age_years && merged.sex !== "unknown"))) {
      merged.confidence = "high";
    }

    return { ok: true, draft: merged, provider: gen.provider, regex_baseline: baseline };
  } catch {
    return { ok: false, error: "llm_request_failed", regex_baseline: baseline };
  }
}
