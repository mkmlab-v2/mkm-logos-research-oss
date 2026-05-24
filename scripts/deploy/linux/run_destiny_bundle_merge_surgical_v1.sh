#!/usr/bin/env bash
# Surgical pre-merge: stash only merge blockers (not full repo -u).
set -euo pipefail
cd /opt/mkm-destiny-ai-41e38ec6
BACKUP="/opt/backups/pre-bundle-untracked-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$BACKUP"

TRACKED=(
  docs/final/artifacts/bench_l1_api_load_summary_vps_latest.json
  projects/bitcoin-trading/ops/v2/ssh/register_destiny_vps_health_monitor.sh
  projects/no1kmedi/.env.example
  projects/no1kmedi/marketing-site/company/index.html
  projects/no1kmedi/marketing-site/index.html
  projects/no1kmedi/marketing-site/public-copy.json
  projects/no1kmedi/package.json
  projects/no1kmedi/payapp-api/server.js
  projects/no1kmedi/scripts/check-marketing-copy-compliance.mjs
  projects/no1kmedi/scripts/check-public-copy-schema.mjs
  projects/no1kmedi/scripts/smoke-advanced-consult.mjs
  projects/no1kmedi/src/app/api/cdss/advanced-consult/route.ts
  projects/no1kmedi/src/app/api/intake/patient-presurvey/route.ts
  projects/no1kmedi/src/app/api/member/access-status/route.ts
  projects/no1kmedi/src/app/clinician/ClinicianWorkspaceClient.tsx
  projects/no1kmedi/src/app/clinician/page.tsx
  projects/no1kmedi/src/app/company/page.tsx
  projects/no1kmedi/src/app/globals.css
  projects/no1kmedi/src/app/page.tsx
  projects/no1kmedi/src/components/AdvancedConsultForm.tsx
  projects/no1kmedi/src/components/ContactActionLinks.tsx
  projects/no1kmedi/src/components/SiteHeader.tsx
  projects/no1kmedi/src/content/siteCopy.ts
  projects/no1kmedi/src/lib/km-cds-ui-analytics-events-v1.ts
  scripts/build_myeongni_full_report_v1.py
  scripts/render_patient_care_bundle_markdown_v1.py
)

UNTRACKED=(
  projects/no1kmedi/scripts/run-clinician-cds-bundle-smoke.ps1
  projects/no1kmedi/scripts/smoke-clinician-cds-bundle-http.mjs
  projects/no1kmedi/scripts/smoke-km-cds-envelope-adapter-v1.ts
  projects/no1kmedi/scripts/smoke-patient-care-bundle-from-cds-v1.ts
  projects/no1kmedi/src/app/api/cdss/patient-care-bundle-from-cds/route.ts
  projects/no1kmedi/src/app/enterprise/page.tsx
  projects/no1kmedi/src/components/ClinicianConsultContextPanel.tsx
  projects/no1kmedi/src/components/ClinicianPersistedChat.tsx
  projects/no1kmedi/src/components/ClinicianThreadRail.tsx
  projects/no1kmedi/src/components/HomepageAppEntry.tsx
  projects/no1kmedi/src/components/PatientCareBundlePreview.tsx
  projects/no1kmedi/src/hooks/useClinicianThreads.ts
  projects/no1kmedi/src/lib/clinician-chat-format.ts
  projects/no1kmedi/src/lib/clinician-chat-storage.ts
  projects/no1kmedi/src/lib/clinician-chat-types.ts
  projects/no1kmedi/src/lib/clinician-consult-payload-v1.ts
  projects/no1kmedi/src/lib/clinician-intake-utils.ts
  projects/no1kmedi/src/lib/km-cds-envelope-adapter-v1.ts
  projects/no1kmedi/src/lib/km-cds-envelope-pipeline-v1.ts
  projects/no1kmedi/src/lib/km-cds-envelope-python-bridge-v1.ts
  projects/no1kmedi/src/lib/km-cds-tri-layer-adapter-v1.ts
  projects/no1kmedi/src/lib/km-patient-care-bundle-auth-v1.ts
  projects/no1kmedi/src/lib/km-patient-care-bundle-python-bridge-v1.ts
)

if git diff --quiet -- "${TRACKED[@]}" 2>/dev/null; then
  echo "[stash] no tracked blocker diffs"
else
  git stash push -m "pre-bundle-surgical-tracked" -- "${TRACKED[@]}"
fi

for p in "${UNTRACKED[@]}"; do
  if [ -e "$p" ]; then
    mkdir -p "$BACKUP/$(dirname "$p")"
    mv "$p" "$BACKUP/$p"
    echo "[backup] $p"
  fi
done

git merge refs/remotes/bundle/vpssync-tip -m "sync: bundle from local (approved surgical)" --no-edit
echo "HEAD=$(git rev-parse --short HEAD)"
test -f projects/bitcoin-trading/src/api/binance_client.py && echo "binance_client_ok"
