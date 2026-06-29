"""Compression Tier-0 pilot apply form — copy SSOT, validation lib, route wiring."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_COPY = ROOT / "projects" / "no1kmedi" / "marketing-site" / "public-copy.json"
APPLY_FORM_SSOT = ROOT / "docs" / "final" / "artifacts" / "compression_pilot_audit_apply_form_v1.json"
VALIDATION_LIB = ROOT / "projects" / "no1kmedi" / "src" / "lib" / "compressionPilotAuditApplyV1.ts"
API_ROUTE = ROOT / "projects" / "no1kmedi" / "src" / "app" / "api" / "leads" / "compression-pilot-audit" / "route.ts"
APPLY_PAGE = ROOT / "projects" / "no1kmedi" / "src" / "app" / "enterprise" / "apply" / "page.tsx"


def test_apply_copy_and_ssot_aligned() -> None:
    data = json.loads(PUBLIC_COPY.read_text(encoding="utf-8"))
    apply = data["compression_pilot_audit_apply"]
    assert apply["hero"]["steps"]
    assert len(apply["options"]["company_stage"]) >= 3
    assert "47%" in apply["labels"]["no_guarantee_ack"]
    assert "SLA" in apply["labels"]["not_sla_ack"]
    ssot = json.loads(APPLY_FORM_SSOT.read_text(encoding="utf-8"))
    assert ssot["apply_url_local"] == "/enterprise/apply"
    assert ssot["send_gate"] == "HOLD"
    assert ssot["payload_schema"] == "compression_pilot_audit_apply_v1"
    ent = data["enterprise"]["compression_roi"]
    assert ent["apply_href"] == "/enterprise/apply"


def test_apply_implementation_paths_exist() -> None:
    assert VALIDATION_LIB.is_file()
    assert API_ROUTE.is_file()
    assert APPLY_PAGE.is_file()
    page = APPLY_PAGE.read_text(encoding="utf-8")
    assert "CompressionPilotAuditApplyForm" in page
    route = API_ROUTE.read_text(encoding="utf-8")
    assert "validateCompressionPilotAuditApply" in route
    assert "deliverLeadWebhook" in route
    assert "OPS_ALARM_WEBHOOK_URL" in route
    assert "send_gate" in VALIDATION_LIB.read_text(encoding="utf-8")
    sync = ROOT / "scripts" / "Sync-CompressionPilotAuditWebhook_v1.ps1"
    assert sync.is_file()
