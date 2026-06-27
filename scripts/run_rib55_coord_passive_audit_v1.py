#!/usr/bin/env python3
"""[HYPO] rib55 + SKU-COORD passive audit: render, R1 ablation, coord v2, v2 stub roundtrip."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/final/artifacts/rib55_coord_passive_audit_v1_latest.json"
REPORT = ROOT / "reports/rib55_coord_passive_audit_v1_latest.json"

STEPS: list[tuple[str, list[str]]] = [
    ("passive_smoke", [sys.executable, "scripts/run_rib55_angle_overlay_passive_smoke_v1.py"]),
    ("l0_l1_ablation", [sys.executable, "scripts/run_rib55_l0_l1_ablation_v1.py"]),
    ("manifest_coord_v2", [sys.executable, "scripts/build_rib55_manifest_coord_v2_v1.py"]),
    ("validate_coord_v2", [sys.executable, "scripts/validate_anatomy_overlay_coord_v2_v1.py"]),
    ("coord_wire_example", [sys.executable, "scripts/build_coord_wire_packet_example_v1.py"]),
    ("coord_wire_bench", [sys.executable, "scripts/build_coord_wire_packet_bench_v1.py"]),
    ("edge_encoder_spec", [sys.executable, "scripts/build_edge_encoder_spec_v1.py"]),
    (
        "edge_encoder_coord_determinism",
        [sys.executable, "scripts/check_edge_encoder_coord_wire_determinism_v1.py"],
    ),
    (
        "edge_encoder_mask_hybrid_determinism",
        [sys.executable, "scripts/check_edge_encoder_mask_hybrid_determinism_v1.py"],
    ),
    ("edge_encoder_air_gap_pack", [sys.executable, "scripts/build_edge_encoder_air_gap_poc_pack_v1.py"]),
    ("edge_encoder_air_gap_bundle", [sys.executable, "scripts/build_edge_encoder_air_gap_bundle_v1.py"]),
    ("edge_encoder_air_gap_verify", [sys.executable, "scripts/check_edge_encoder_air_gap_bundle_v1.py"]),
    (
        "edge_encoder_cross_process_http",
        [sys.executable, "scripts/check_edge_encoder_cross_process_determinism_v1.py"],
    ),
    ("edge_encoder_pyinstaller_readiness", [sys.executable, "scripts/build_edge_encoder_sdk_pyinstaller_v1.py"]),
    (
        "edge_encoder_pyinstaller_gate",
        [sys.executable, "scripts/check_edge_encoder_pyinstaller_readiness_v1.py"],
    ),
    ("edge_encoder_vpc_runbook", [sys.executable, "scripts/build_edge_encoder_vpc_deploy_runbook_v1.py"]),
    ("edge_encoder_vpc_checklist_html", [sys.executable, "scripts/build_edge_encoder_vpc_checklist_html_v1.py"]),
    (
        "edge_encoder_pyinstaller_binary_smoke",
        [sys.executable, "scripts/check_edge_encoder_pyinstaller_binary_smoke_v1.py"],
    ),
    ("edge_encoder_sdk_smoke", [sys.executable, "scripts/run_edge_encoder_sdk_cli_v1.py", "smoke"]),
    (
        "pytest_edge_encoder",
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_edge_encoder_spec_v1.py",
            "tests/test_edge_encoder_sdk_v1.py",
            "-q",
        ],
    ),
    ("education_mock_html", [sys.executable, "scripts/build_rib55_infographic_education_mock_all_v1.py"]),
    (
        "pytest_coord_v2",
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_coord_anatomy_overlay_wire_v1_lib.py",
            "tests/test_compression_token_api_v2_stub.py::test_v2_coord_anatomy_overlay_compress_expand_render",
            "tests/test_render_rib55_angle_overlay_v1.py",
            "-q",
        ],
    ),
    (
        "multi_axis_promotion_gate",
        [sys.executable, "scripts/validate_mkm_multi_axis_promotion_gate_policy_v1.py"],
    ),
    (
        "adjudication_workflow",
        [sys.executable, "scripts/build_rib55_adjudication_workflow_v1.py", "--skip-prereq-chain"],
    ),
    (
        "validate_adjudication_template_schema",
        [
            sys.executable,
            "-c",
            "import json; from pathlib import Path; import jsonschema; "
            "r=Path('docs/final/artifacts/rib55_overlay_adjudication_record_v1.template.json'); "
            "s=Path('docs/final/schemas/rib55_overlay_adjudication_record_v1.schema.json'); "
            "jsonschema.Draft7Validator(json.loads(s.read_text(encoding='utf-8'))).validate(json.loads(r.read_text(encoding='utf-8'))); "
            "print('template schema ok')",
        ],
    ),
    (
        "apply_adjudication_g1",
        [
            sys.executable,
            "scripts/apply_rib55_overlay_adjudication_v1.py",
            "--record-json",
            "docs/final/artifacts/rib55_overlay_adjudication_record_g1_infographic_v1.json",
        ],
    ),
    (
        "apply_adjudication_alt_bench",
        [
            sys.executable,
            "scripts/apply_rib55_overlay_adjudication_v1.py",
            "--record-json",
            "docs/final/artifacts/rib55_overlay_adjudication_record_alt_bench_v1.json",
        ],
    ),
    (
        "apply_adjudication_second_rib",
        [
            sys.executable,
            "scripts/apply_rib55_overlay_adjudication_v1.py",
            "--record-json",
            "docs/final/artifacts/rib55_overlay_adjudication_record_second_rib_v1.json",
        ],
    ),
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(name: str, cmd: list[str]) -> dict:
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return {
        "step": name,
        "cmd": cmd,
        "exit_code": proc.returncode,
        "stdout_tail": (proc.stdout or "")[-600:],
        "stderr_tail": (proc.stderr or "")[-300:] if proc.stderr else None,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-pytest", action="store_true")
    args = ap.parse_args()

    rows: list[dict] = []
    ok = True
    for name, cmd in STEPS:
        if args.skip_pytest and name in ("pytest_coord_v2", "pytest_edge_encoder"):
            rows.append({"step": name, "skipped": True})
            continue
        row = _run(name, cmd)
        rows.append(row)
        if row["exit_code"] != 0:
            ok = False
            break

    doc = {
        "schema": "rib55_coord_passive_audit_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "adjudication_pending": True,
        "steps": rows,
        "ok": ok,
        "reproduce": "py scripts/run_rib55_coord_passive_audit_v1.py",
        "adjudication_pointer": "docs/final/artifacts/rib55_adjudication_workflow_v1_latest.json",
        "operator_lines": [
            "- [RIB55-AUDIT] passive chain ok; send_gate=HOLD.",
            "- [RIB55-AUDIT] formal adjudication record still required for education_internal.",
        ],
    }
    if ok:
        wf = ROOT / "docs/final/artifacts/rib55_adjudication_workflow_v1_latest.json"
        manifest = ROOT / "docs/final/artifacts/rib55_angle_overlay_manifest_v1.json"
        entry_status = None
        if manifest.is_file():
            mdoc = json.loads(manifest.read_text(encoding="utf-8"))
            entry = (mdoc.get("entries") or [{}])[0]
            entry_status = entry.get("status")
            inf = entry.get("infographic_field_v1") or {}
            doc["infographic_field_present"] = bool(inf.get("headline_ko"))
            doc["entry_status"] = entry_status
        if wf.is_file():
            wf_doc = json.loads(wf.read_text(encoding="utf-8"))
            pending = wf_doc.get("pending_entry_ids") or []
            doc["pending_entry_ids"] = pending
            done = entry_status in ("adjudicated_education_internal", "adjudicated_with_reservations")
            doc["adjudication_pending"] = bool(pending) and not done
            doc["operator_lines"].append(f"- [RIB55-AUDIT] pending_entries={pending}")
            if done:
                doc["operator_lines"][-2] = "- [RIB55-AUDIT] G1 education_internal adjudication applied; send_gate=HOLD."
    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(payload, encoding="utf-8")
    REPORT.write_text(payload, encoding="utf-8")
    print(json.dumps({"ok": ok, "out": str(OUT), "steps": len(rows)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
