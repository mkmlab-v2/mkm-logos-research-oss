#!/usr/bin/env python3
"""Build customer VPC on-prem deploy runbook artifact [HYPO] B-track."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/final/artifacts/edge_encoder_vpc_deploy_runbook_v1_latest.json"
REPORT = ROOT / "reports/edge_encoder_vpc_deploy_runbook_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build() -> dict:
    return {
        "schema": "edge_encoder_vpc_deploy_runbook_v1",
        "generated_at_utc": _utc(),
        "track": "B",
        "research_only": True,
        "hypothesis_tier": "B",
        "send_gate": "HOLD",
        "ready_for_external_send": False,
        "deployment_mode": "customer_vpc_on_prem",
        "maturity": "runbook_scripted",
        "boundary_ack": (
            "[HYPO] Customer VPC retains originals + base catalog; MKM SaaS receives coord_wire only. "
            "Not production SLA; counsel + customer corpus gates remain."
        ),
        "original_bulk_sent": False,
        "phases": [
            {
                "id": "P0_prerequisites",
                "title": "Prerequisites",
                "steps": [
                    "Import air-gap bundle: reports/edge_encoder_air_gap_bundle_v1_latest/",
                    "Sync licensed base catalog (base_asset_id + base_sha256) on VPC edge node",
                    "Optional: run local v2 compression stub on VPC (uvicorn port 8011) for HTTP roundtrip",
                ],
            },
            {
                "id": "P1_operator_smoke",
                "title": "Operator smoke",
                "steps": [
                    "powershell -File scripts/Invoke-EdgeEncoderAirGapPoC_v1.ps1",
                    "py scripts/check_edge_encoder_air_gap_bundle_v1.py",
                    "py scripts/check_edge_encoder_cross_process_determinism_v1.py",
                ],
            },
            {
                "id": "P2_local_encode",
                "title": "Encode on edge (no bulk upload)",
                "steps": [
                    "py scripts/run_edge_encoder_sdk_cli_v1.py encode-manifest --entry-id pilot_ninth_rib_55deg_v0",
                    "py scripts/run_edge_encoder_sdk_cli_v1.py validate --entry-id pilot_ninth_rib_55deg_v0",
                ],
            },
            {
                "id": "P3_wire_export",
                "title": "Wire export to control plane",
                "steps": [
                    "Ship wire/wire_only_export.json fields only (coord_wire_minimal, compact_coord_wire, base_sha256)",
                    "Verify metering metadata separate from image bytes",
                    "NEVER upload data/anatomy/fixtures/*.png on default path",
                ],
            },
            {
                "id": "P4_optional_saas_meter",
                "title": "Optional SaaS meter (coord only)",
                "steps": [
                    "POST /v2/compress sku_class=coord with coord_wire JSON text",
                    "POST /v2/expand decode_mode=codebook_only for audit replay",
                    "Human gate before any external customer SEND",
                ],
            },
        ],
        "human_gates": [
            "counsel_signoff",
            "customer_masked_corpus_intake",
            "vps_nginx_deploy_approval",
        ],
        "artifacts": {
            "air_gap_bundle": "reports/edge_encoder_air_gap_bundle_v1_latest",
            "wire_only_export": "reports/edge_encoder_air_gap_bundle_v1_latest/wire/wire_only_export.json",
            "portable_launcher": "reports/edge_encoder_sdk_portable_launcher_v1_latest",
            "pyinstaller_readiness": "docs/final/artifacts/edge_encoder_pyinstaller_readiness_v1_latest.json",
            "spec": "docs/final/artifacts/edge_encoder_spec_v1_latest.json",
        },
        "verify_commands": [
            "py scripts/check_edge_encoder_air_gap_bundle_v1.py",
            "py scripts/check_edge_encoder_cross_process_determinism_v1.py",
            "py scripts/check_edge_encoder_pyinstaller_readiness_v1.py",
            "py scripts/check_edge_encoder_pyinstaller_binary_smoke_v1.py",
        ],
        "operator_html": "reports/demo/edge_encoder_vpc_deploy_checklist_v1.html",
        "operator_html_builder": "scripts/build_edge_encoder_vpc_checklist_html_v1.py",
        "fail_comp_004": "Do not cite coord_wire token savings as global MASK 47% headline.",
    }


def main() -> int:
    doc = build()
    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(payload, encoding="utf-8")
    REPORT.write_text(payload, encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(OUT), "phases": len(doc["phases"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
