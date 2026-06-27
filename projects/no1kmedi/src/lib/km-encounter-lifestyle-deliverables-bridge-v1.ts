import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

import { resolveEncounterPatient, resolvePrintHtmlRel } from "@/lib/clinician-encounter-artifacts-v1";
import { resolveMkmWorkspaceRoot } from "@/lib/km-workspace-root-v1";

export type LifestyleDeliverablesRequestV1 = {
  slug?: string;
  refToken?: string;
  display?: string;
  fusionMarkdown?: string;
  writeKakaoDraft?: boolean;
};

export type LifestyleDeliverablesResultV1 =
  | {
      ok: true;
      slug: string;
      refToken: string;
      displayLabel: string;
      lifestyleJsonRel: string;
      printHtmlRel: string;
      kakaoDraftRel?: string;
      kakaoGoldRel?: string;
    }
  | { ok: false; error: string; stderr?: string };

function fixtureRelFromPointer(paths: Record<string, string>): string | null {
  return paths.lifestyle_management_fixture || paths.lifestyle_v2 || null;
}

export function runEncounterLifestyleDeliverablesChain(
  req: LifestyleDeliverablesRequestV1,
  workspaceRoot?: string,
): LifestyleDeliverablesResultV1 {
  const root = workspaceRoot?.trim() || resolveMkmWorkspaceRoot();
  if (!root) return { ok: false, error: "workspace_root_not_found" };

  const resolved = resolveEncounterPatient({
    root,
    slug: req.slug,
    refToken: req.refToken,
    display: req.display,
  });
  if ("error" in resolved) return { ok: false, error: resolved.error };

  const paths = resolved.pointer.paths || {};
  const fixtureRel = fixtureRelFromPointer(paths);
  if (!fixtureRel) {
    return { ok: false, error: "lifestyle_management_fixture_missing_in_pointer" };
  }

  const fixtureAbs = path.join(root, fixtureRel);
  if (!fs.existsSync(fixtureAbs)) {
    return { ok: false, error: `lifestyle_fixture_missing_on_disk:${fixtureRel}` };
  }

  const printRel = resolvePrintHtmlRel(paths);
  if (!printRel) {
    return { ok: false, error: "print_html_not_configured_in_pointer" };
  }

  const printAbs = path.join(root, printRel);
  const renderScript = path.join(root, "scripts", "render_clinic_lifestyle_management_print_v1.py");
  if (!fs.existsSync(renderScript)) {
    return { ok: false, error: "render_clinic_lifestyle_management_print_v1.py missing" };
  }

  const py = process.env.MKM_PYTHON?.trim() || "py";
  const child = spawnSync(
    py,
    [renderScript, "--input-json", fixtureAbs, "--out-html", printAbs],
    { cwd: root, encoding: "utf-8", maxBuffer: 8 * 1024 * 1024, timeout: 60_000, windowsHide: true },
  );

  if (child.status !== 0) {
    return {
      ok: false,
      error: (child.stderr || child.stdout || `render exit ${child.status}`).trim().slice(0, 3000),
      stderr: child.stderr,
    };
  }

  if (!fs.existsSync(printAbs)) {
    return { ok: false, error: `print_html_not_written:${printRel}` };
  }

  let kakaoDraftRel: string | undefined;
  const fusionMd = req.fusionMarkdown?.trim();
  if (req.writeKakaoDraft !== false && fusionMd) {
    const runDir = path.join(root, "reports", "cdss_runtime", `lifestyle_kakao_draft_${resolved.slug}_${Date.now()}`);
    fs.mkdirSync(runDir, { recursive: true });
    kakaoDraftRel = path.join("reports", "cdss_runtime", path.basename(runDir), "kakao_from_fusion_draft.md").replace(
      /\\/g,
      "/",
    );
    const draftAbs = path.join(root, kakaoDraftRel);
    const header = [
      `# 카톡 드래프트 (fusion 초안 — Human Gold 전 검토)`,
      ``,
      `**slug:** ${resolved.slug} · **ref:** ${resolved.pointer.ref_token || ""}`,
      `**주의:** physician_gold SSOT(\`clinic_kakao\`)를 덮어쓰지 않음. 원장 확정 후 복사·발송.`,
      ``,
      `---`,
      ``,
    ].join("\n");
    fs.writeFileSync(draftAbs, `${header}${fusionMd}\n`, "utf-8");
  }

  return {
    ok: true,
    slug: resolved.slug,
    refToken: String(resolved.pointer.ref_token || resolved.slug),
    displayLabel: String(resolved.pointer.display_label || resolved.slug),
    lifestyleJsonRel: fixtureRel.replace(/\\/g, "/"),
    printHtmlRel: printRel.replace(/\\/g, "/"),
    kakaoDraftRel,
    kakaoGoldRel: paths.clinic_kakao?.replace(/\\/g, "/"),
  };
}
