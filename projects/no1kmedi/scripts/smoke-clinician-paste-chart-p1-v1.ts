/**
 * Offline smoke: ephemeral encounter + thread backup parse.
 * Run: npx --yes tsx ./scripts/smoke-clinician-paste-chart-p1-v1.ts
 */

import {
  buildClinicianThreadsBackup,
  mergeImportedClinicianThreads,
  parseClinicianThreadsBackup,
  createEmptyClinicianThread,
} from "../src/lib/clinician-chat-storage";
import {
  buildEphemeralEncounterPointer,
  buildEphemeralEncounterSlug,
  canUseEphemeralEncounter,
} from "../src/lib/clinician-ephemeral-encounter-v1";
import { runIntakeFusionDraftChain } from "../src/lib/km-intake-fusion-draft-bridge-v1";
import { resolveMkmWorkspaceRoot } from "../src/lib/km-workspace-root-v1";

function assert(cond: boolean, msg: string) {
  if (!cond) throw new Error(msg);
}

const slug = buildEphemeralEncounterSlug("박신규");
assert(slug.startsWith("ephemeral_"), "ephemeral slug prefix");

const ptr = buildEphemeralEncounterPointer(slug, "박신규");
assert(Boolean(ptr.ref_token?.startsWith("EPH-")), "ephemeral ref token");

assert(
  canUseEphemeralEncounter({
    allowEphemeral: true,
    display: "박신규",
    birthInstantUtc: "1990-01-01T00:00:00+09:00",
  }),
  "can ephemeral",
);

const root = resolveMkmWorkspaceRoot();
let fusionOk = false;
let fusionEphemeral = false;
if (root) {
  const fusion = runIntakeFusionDraftChain(
    {
      display: "박신규",
      intakeText: "두통 3일 · 만성 피로 · 스트레스",
      birthInstantUtc: "1985-06-15T00:00:00+09:00",
      ianaTz: "Asia/Seoul",
      isMale: true,
      allowEphemeral: true,
      validateSchema: false,
      validatePolicy: false,
      renderMd: false,
    },
    root,
  );
  fusionOk = fusion.ok;
  fusionEphemeral = fusion.ok ? Boolean(fusion.ephemeral) : false;
}

const t1 = createEmptyClinicianThread();
const backup = buildClinicianThreadsBackup([t1]);
const roundtrip = parseClinicianThreadsBackup(JSON.stringify(backup));
assert(roundtrip.ok && roundtrip.threads.length === 1, "backup roundtrip");
const merged = mergeImportedClinicianThreads([], roundtrip.threads);
assert(merged.length === 1, "merge import");

console.log(
  JSON.stringify(
    {
      schema: "smoke_clinician_paste_chart_p1_v1",
      ok: true,
      slug,
      fusion_ok: fusionOk,
      fusion_ephemeral: fusionEphemeral,
      workspace_root: root || null,
    },
    null,
    2,
  ),
);
