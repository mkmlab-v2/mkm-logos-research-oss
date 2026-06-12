#!/usr/bin/env python3
"""Gate: MKM Family identity federation (jema-ai.com IdP) — paths and policy."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = [
    ROOT / "docs/final/schemas/mkm_family_account_v1.schema.json",
    ROOT / "docs/final/schemas/mkm_family_product_link_v1.schema.json",
    ROOT / "docs/final/artifacts/mkm_family_identity_policy_v1_latest.json",
    ROOT / "projects/no1kmedi/src/lib/mkmFamilyAuthConfigV1.ts",
    ROOT / "projects/no1kmedi/src/lib/mkmFamilyAccountStoreV1.ts",
    ROOT / "projects/no1kmedi/src/app/api/mkm-family/session/route.ts",
    ROOT / "projects/no1kmedi/src/app/api/mkm-family/auth/google/route.ts",
    ROOT / "projects/no1kmedi/src/app/api/mkm-family/rp/handoff/route.ts",
    ROOT / "projects/no1kmedi/src/app/api/mkm-family/rp/exchange/route.ts",
    ROOT / "projects/mkm/mkm-life/lib/mkm-family-rp-client-v1.ts",
    ROOT / "projects/mkm/mkm-life/app/auth/mkm-callback/page.tsx",
    ROOT / "projects/no1kmedi/src/hooks/useMkmFamilySessionV1.ts",
    ROOT / "projects/no1kmedi/src/lib/mkmFamilyHandoffV1.ts",
    ROOT / "scripts/Initialize-MkmFamilyGoogleOAuthSecureStore_v1.ps1",
    ROOT / "scripts/Invoke-ApplyMkmFamilyGoogleOAuthToVps_v1.ps1",
    ROOT / "scripts/Verify-MkmFamilyIdentityReadiness_v1.ps1",
    ROOT / "scripts/smoke_mkm_family_identity_live_v1.py",
]

FORBIDDEN_IN_POLICY_BODY = [
    "merge_personadiary_packages_into_mkmlife_db",
]


def main() -> int:
    issues: list[str] = []
    for path in REQUIRED:
        if not path.is_file():
            issues.append(f"missing: {path.relative_to(ROOT)}")

    policy_path = ROOT / "docs/final/artifacts/mkm_family_identity_policy_v1_latest.json"
    if policy_path.is_file():
        policy = json.loads(policy_path.read_text(encoding="utf-8"))
        if policy.get("human_approval", {}).get("personadiary_mkmlife_db_merge") is not False:
            issues.append("policy: personadiary_mkmlife_db_merge must be false")
        if policy.get("human_approval", {}).get("cross_product_identity_federation") is not True:
            issues.append("policy: cross_product_identity_federation must be true")
        raw = policy_path.read_text(encoding="utf-8")
        for token in FORBIDDEN_IN_POLICY_BODY:
            if token not in raw:
                issues.append(f"policy missing forbidden marker: {token}")

    plugins = ROOT / "projects/no1kmedi/src/lib/universeHubPluginsV2.ts"
    if plugins.is_file():
        text = plugins.read_text(encoding="utf-8")
        if "personadiary_preview" not in text:
            issues.append("hub plugins: personadiary_preview missing")

    out = {"overall_ok": not issues, "issues": issues}
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if not issues else 1


if __name__ == "__main__":
    sys.exit(main())
