#!/usr/bin/env python3
"""Build Edge Encoder client contract v1 from SKU-COORD wire SSOT. [HYPO] B-track."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COORD_EXAMPLE = ROOT / "docs/final/artifacts/coord_wire_packet_example_v1_latest.json"
OUT = ROOT / "docs/final/artifacts/edge_encoder_spec_v1_latest.json"
REPORT = ROOT / "reports/edge_encoder_spec_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build() -> dict:
    if not COORD_EXAMPLE.is_file():
        raise FileNotFoundError(
            f"missing {COORD_EXAMPLE}; run build_coord_wire_packet_example_v1.py first"
        )
    example = json.loads(COORD_EXAMPLE.read_text(encoding="utf-8"))
    token_ref = (example.get("token_proxy_cl100k") or {}).get("coord_wire_tokens")

    from scripts.compression_hybrid_router_spec_v1_lib import resolve_hybrid_router

    mask_res = resolve_hybrid_router("public-open-web-v1")
    mask_backend = mask_res.recommended_backend if mask_res else "mkm_candidate_pool"

    return {
        "schema": "edge_encoder_spec_v1",
        "generated_at_utc": _utc(),
        "track": "B",
        "research_only": True,
        "hypothesis_tier": "B",
        "send_gate": "HOLD",
        "ready_for_external_send": False,
        "maturity": "sdk_alpha",
        "boundary_ack": (
            "[HYPO] Client-side Edge Encoder contract — user retains originals locally; "
            "only coord_wire + base_sha256 crosses the wire. Not a shipped SDK; "
            "MASK Track A KPI (47% universal) must not merge (FAIL-COMP-004)."
        ),
        "fail_comp_004": (
            "Do not cite coord_wire token savings as global compression API or Track A headline."
        ),
        "client_obligations": {
            "retain_original_locally": True,
            "pre_sync_base_catalog": True,
            "emit_coord_wire_only": True,
            "verify_base_sha256_before_send": True,
            "allowed_upload_surfaces": [
                "coord_wire_minimal JSON",
                "compact_coord_wire token",
                "semantic_pointer_v1 (optional)",
            ],
            "forbidden_upload_surfaces": [
                "raw_image_bytes",
                "unmasked_customer_jsonl_bulk",
                "full_png_base64_on_default_path",
            ],
        },
        "server_forbidden": {
            "original_bulk_to_mkm_saas": True,
            "unlicensed_base_image_bytes": True,
            "note_ko": "서버는 base_sha256·coord_spec 검증·metering만; 원문·라이선스 미확인 바이트 수신 금지.",
        },
        "coord_wire_schema": {
            "path": "docs/final/schemas/edge_encoder_coord_wire_v1.schema.json",
            "wire_mode": "anatomy_overlay_coord_v1",
            "example_artifact": "docs/final/artifacts/coord_wire_packet_example_v1_latest.json",
            "token_proxy_cl100k_reference": token_ref,
        },
        "deterministic_sync": {
            "status": "bench_ready",
            "gate_script": "scripts/check_edge_encoder_coord_wire_determinism_v1.py",
            "checks": [
                "jsonschema: edge_encoder_coord_wire_v1",
                "parse_coord_wire_text(canonical JSON)",
                "compact_coord_wire roundtrip entry_id",
                "fixture base_sha256 matches wire.base_sha256",
            ],
        },
        "mask_hybrid_determinism": {
            "status": "bench_ready",
            "gate_script": "scripts/check_edge_encoder_mask_hybrid_determinism_v1.py",
            "backend": mask_backend,
            "corpus_tag": "public-open-web-v1",
            "checks": [
                "duplicate /v2/compress fingerprint stable",
                "hybrid_router_backend_recommended binding",
                "cached compression_packet expand stable",
            ],
        },
        "sdk_cli": {
            "status": "sdk_alpha",
            "script": "scripts/run_edge_encoder_sdk_cli_v1.py",
            "lib": "scripts/edge_encoder_sdk_v1_lib.py",
            "commands": ["encode-manifest", "validate", "local-roundtrip", "http-roundtrip", "smoke"],
            "original_bulk_sent_default": False,
        },
        "air_gap_poc": {
            "status": "bundle_materialized",
            "deployment_mode": "air_gap_on_prem",
            "pack_artifact": "docs/final/artifacts/edge_encoder_air_gap_poc_pack_v1_latest.json",
            "builder": "scripts/build_edge_encoder_air_gap_poc_pack_v1.py",
            "bundle_dir": "reports/edge_encoder_air_gap_bundle_v1_latest",
            "bundle_builder": "scripts/build_edge_encoder_air_gap_bundle_v1.py",
            "bundle_gate": "scripts/check_edge_encoder_air_gap_bundle_v1.py",
            "invoke_chain": "scripts/Invoke-EdgeEncoderAirGapPoC_v1.ps1",
        },
        "cross_process_http": {
            "status": "bench_ready",
            "gate_script": "scripts/check_edge_encoder_cross_process_determinism_v1.py",
            "lib": "scripts/edge_encoder_http_roundtrip_v1_lib.py",
            "checks": [
                "ephemeral uvicorn v2 stub health",
                "TestClient vs HTTP compression_packet fingerprint",
                "expand text parity",
            ],
        },
        "portable_launcher": {
            "status": "launcher_scripts",
            "builder": "scripts/build_edge_encoder_sdk_portable_launcher_v1.py",
            "out_dir": "reports/edge_encoder_sdk_portable_launcher_v1_latest",
        },
        "pyinstaller": {
            "status": "spec_scaffold",
            "entrypoint": "scripts/edge_encoder_sdk_frozen_entrypoint_v1.py",
            "builder": "scripts/build_edge_encoder_sdk_pyinstaller_v1.py",
            "pyinstaller_readiness_gate": "scripts/check_edge_encoder_pyinstaller_readiness_v1.py",
            "pyinstaller_binary_smoke": "scripts/check_edge_encoder_pyinstaller_binary_smoke_v1.py",
            "readiness_artifact": "docs/final/artifacts/edge_encoder_pyinstaller_readiness_v1_latest.json",
        },
        "vpc_deploy_runbook": {
            "status": "runbook_scripted",
            "builder": "scripts/build_edge_encoder_vpc_deploy_runbook_v1.py",
            "artifact": "docs/final/artifacts/edge_encoder_vpc_deploy_runbook_v1_latest.json",
            "operator_html": "reports/demo/edge_encoder_vpc_deploy_checklist_v1.html",
            "operator_html_builder": "scripts/build_edge_encoder_vpc_checklist_html_v1.py",
        },
        "ssot_pointers": {
            "coord_wire_example": "docs/final/artifacts/coord_wire_packet_example_v1_latest.json",
            "coord_wire_bench": "docs/final/artifacts/coord_wire_packet_bench_v1_latest.json",
            "sku_separation_brief": "docs/final/artifacts/compression_sku_separation_brief_v1_latest.json",
            "hybrid_router_coord_modes": "docs/final/artifacts/compression_hybrid_router_spec_v1.json",
            "v2_openapi": "docs/final/openapi_token_compression_v2_draft.yaml",
            "coord_lib": "scripts/coord_anatomy_overlay_wire_v1_lib.py",
            "v2_stub_route": "POST /v2/compress sku_class=coord → POST /v2/expand render",
        },
        "reproduce": [
            "py scripts/build_coord_wire_packet_example_v1.py",
            "py scripts/build_edge_encoder_spec_v1.py",
            "py scripts/check_edge_encoder_coord_wire_determinism_v1.py",
            "py scripts/check_edge_encoder_mask_hybrid_determinism_v1.py",
            "py scripts/build_edge_encoder_air_gap_poc_pack_v1.py",
            "py scripts/build_edge_encoder_air_gap_bundle_v1.py",
            "py scripts/check_edge_encoder_air_gap_bundle_v1.py",
            "powershell -File scripts/Invoke-EdgeEncoderAirGapPoC_v1.ps1",
            "py scripts/check_edge_encoder_cross_process_determinism_v1.py",
            "py scripts/build_edge_encoder_sdk_portable_launcher_v1.py",
            "py scripts/build_edge_encoder_sdk_pyinstaller_v1.py",
            "py scripts/build_edge_encoder_vpc_deploy_runbook_v1.py",
            "py scripts/run_edge_encoder_sdk_cli_v1.py smoke",
            "py -m pytest tests/test_edge_encoder_spec_v1.py tests/test_edge_encoder_sdk_v1.py -q",
        ],
    }


def main() -> int:
    sys.path.insert(0, str(ROOT))
    from scripts.edge_encoder_spec_v1_lib import validate_edge_encoder_spec

    doc = build()
    errors = validate_edge_encoder_spec(doc)
    if errors:
        print(json.dumps({"ok": False, "errors": errors}, ensure_ascii=False), file=sys.stderr)
        return 1

    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(payload, encoding="utf-8")
    REPORT.write_text(payload, encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(OUT), "maturity": doc["maturity"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
