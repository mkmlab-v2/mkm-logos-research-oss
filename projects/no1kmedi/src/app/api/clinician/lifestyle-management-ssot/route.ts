import { NextResponse } from "next/server";
import { readFile } from "fs/promises";
import path from "path";

export const runtime = "nodejs";

/** SSOT pointer for clinic lifestyle print v2 (physician_gold, patient-facing clinical tone). */
export async function GET() {
  try {
    const root = process.cwd();
    const monoRoot = path.join(root, "..", "..");
    const templatePath = path.join(
      monoRoot,
      "docs",
      "final",
      "artifacts",
      "clinic_lifestyle_management_template_v2.json",
    );
    const formatSpecPath = path.join(
      monoRoot,
      "docs",
      "final",
      "artifacts",
      "clinic_lifestyle_management_format_spec_v2.json",
    );
    const fixturePath = path.join(
      monoRoot,
      "docs",
      "final",
      "artifacts",
      "fixtures",
      "clinic_lifestyle_management_post_miscarriage_soeum_v2.example.json",
    );
    const [templateRaw, formatRaw, fixtureRaw] = await Promise.all([
      readFile(templatePath, "utf8"),
      readFile(formatSpecPath, "utf8"),
      readFile(fixturePath, "utf8"),
    ]);
    const template = JSON.parse(templateRaw) as Record<string, unknown>;
    const formatSpec = JSON.parse(formatRaw) as Record<string, unknown>;
    const example = JSON.parse(fixtureRaw) as Record<string, unknown>;

    return NextResponse.json({
      success: true,
      template_id: template.template_id,
      schema: template.instance_schema,
      lane: "physician_gold",
      research_only: true,
      physician_lane: {
        print_form_path: String(template.print_form_path ?? "/forms/clinic_lifestyle_management_print_v2.html"),
        print_form_label_ko: String(template.print_form_label_ko ?? "회복·생활관리 안내서"),
        template_ssot_path: "docs/final/artifacts/clinic_lifestyle_management_template_v2.json",
        format_spec_path: "docs/final/artifacts/clinic_lifestyle_management_format_spec_v2.json",
        fixture_example_path: String(template.fixture_example_path ?? ""),
        render_script: String(template.render_script ?? "scripts/render_clinic_lifestyle_management_print_v1.py"),
        bundle_slot_key: "lifestyle_management",
        legacy_v1_template: "docs/final/artifacts/clinic_lifestyle_management_template_v1.json",
      },
      language_policy: formatSpec.language_policy,
      section_order: formatSpec.section_order_patient_facing,
      example_instance: example,
      disclaimer:
        "환자 인쇄본은 현대 의학·회복 프로토콜 표현만. 명리·사주는 internal_reference(차트용). consumer/mkmlife 자동 합선 금지.",
    });
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    return NextResponse.json({ success: false, error: msg }, { status: 500 });
  }
}
