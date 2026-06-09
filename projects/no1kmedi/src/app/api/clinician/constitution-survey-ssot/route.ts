import { NextResponse } from "next/server";
import path from "node:path";
import { promises as fs } from "node:fs";
import { CONSTITUTION_QUESTIONS } from "@/lib/constitution-survey-schema";
import {
  defaultMkmlifeConsumerSurveyUrl,
  type ClinicianSurveySsotPayload,
} from "@/lib/clinician-survey-ssot-v1";

const BANK_REL = path.join(
  "docs",
  "final",
  "artifacts",
  "clinic_constitution_survey_item_bank_v1.json",
);

async function resolveWorkspaceRoot(): Promise<string | null> {
  const fromEnv = process.env.MKM_WORKSPACE_ROOT?.trim();
  const cwd = process.cwd();
  const candidates = [
    fromEnv ? path.resolve(fromEnv) : null,
    cwd,
    path.resolve(cwd, ".."),
    path.resolve(cwd, "..", ".."),
    path.resolve(cwd, "..", "..", ".."),
  ].filter((c): c is string => Boolean(c));
  for (const root of candidates) {
    try {
      await fs.access(path.join(root, BANK_REL));
      return root;
    } catch {
      /* next */
    }
  }
  return null;
}

export async function GET() {
  const consumerUrl = defaultMkmlifeConsumerSurveyUrl();
  const mkmlifeOrigin =
    process.env.MKMLIFE_CONSTITUTION_SURVEY_API_ORIGIN?.trim() || "https://mkmlife.com";

  const base: ClinicianSurveySsotPayload = {
    success: true,
    physician_lane: {
      presurvey_api: "/api/intake/patient-presurvey",
      constitution_questions_in_app: CONSTITUTION_QUESTIONS.length,
      ssot_bank_path: BANK_REL,
      print_form_path: "/forms/clinic_constitution_survey_print_v1.html",
      print_form_label_ko: "사상체질 자가문진지 14문항 (A4 인쇄 · 원내용지)",
    },
    consumer_lane: {
      survey_url: consumerUrl,
      score_api_path: `${mkmlifeOrigin.replace(/\/$/, "")}/api/v1/constitution/survey/score`,
      label: "소비자 14문항·MAI (mkmlife)",
      sublabel: "임상 확정·physician_gold와 별도 레인 · MBTI® 공식 검사 아님",
    },
    disclaimer:
      "진료실 문진·PIN은 physician_gold. mkmlife 설문은 consumer_survey_only이며 KPI·임상 단정에 합산하지 않습니다.",
  };

  const root = await resolveWorkspaceRoot();
  if (!root) {
    return NextResponse.json({
      ...base,
      pack_id: "mkm_constitution_survey_core_v1",
      pack_schema: "clinic_constitution_survey_item_bank_v1",
      item_count: undefined,
      lane: "consumer_survey_only",
      research_only: true,
      note: "MKM_WORKSPACE_ROOT unset — bank metadata not loaded from disk",
    });
  }

  try {
    const raw = await fs.readFile(path.join(root, BANK_REL), "utf8");
    const bank = JSON.parse(raw) as {
      pack_id?: string;
      schema?: string;
      lane?: string;
      research_only?: boolean;
      items?: unknown[];
    };
    return NextResponse.json({
      ...base,
      pack_id: bank.pack_id,
      pack_schema: bank.schema,
      item_count: Array.isArray(bank.items) ? bank.items.length : undefined,
      lane: bank.lane,
      research_only: bank.research_only,
    });
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    return NextResponse.json(
      { ...base, success: false, error: `bank_read_failed: ${msg}` },
      { status: 500 },
    );
  }
}
