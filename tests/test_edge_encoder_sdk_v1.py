# Edge Encoder SDK v1 CLI — local encode + roundtrip [HYPO]

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts/run_edge_encoder_sdk_cli_v1.py"
AIR_GAP = ROOT / "scripts/build_edge_encoder_air_gap_poc_pack_v1.py"
SPEC = ROOT / "docs/final/artifacts/edge_encoder_spec_v1_latest.json"


def test_edge_encoder_sdk_smoke_exit_0():
    r = subprocess.run([sys.executable, str(CLI), "smoke"], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    doc = json.loads(r.stdout.strip().splitlines()[-1])
    assert doc["ok"] is True
    assert doc["tokens"] is not None
    assert doc["tokens"] < 220


def test_encode_manifest_writes_valid_wire(tmp_path: Path):
    out = tmp_path / "wire.json"
    r = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "encode-manifest",
            "--entry-id",
            "pilot_ninth_rib_55deg_v0",
            "--out-json",
            str(out),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["original_bulk_sent"] is False
    assert doc["coord_wire_minimal"]["base_sha256"] == (
        "82dc7d64e87caed9ff257414aa6db76371d20dab637e56df00f67e2fcdb0ddde"
    )


def test_local_roundtrip_exit_0():
    r = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "local-roundtrip",
            "--entry-id",
            "pilot_ninth_rib_55deg_v0",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stdout + r.stderr


def test_air_gap_poc_pack_build():
    r = subprocess.run([sys.executable, str(AIR_GAP)], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    out = ROOT / "docs/final/artifacts/edge_encoder_air_gap_poc_pack_v1_latest.json"
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["deployment_mode"] == "air_gap_on_prem"
    assert doc["send_gate"] == "HOLD"
    assert doc.get("maturity") == "bundle_materialized"
    assert doc.get("bundle_dir")


def test_air_gap_bundle_materialize_and_verify():
    build = ROOT / "scripts/build_edge_encoder_air_gap_bundle_v1.py"
    verify = ROOT / "scripts/check_edge_encoder_air_gap_bundle_v1.py"
    r1 = subprocess.run([sys.executable, str(build)], cwd=ROOT, capture_output=True, text=True)
    assert r1.returncode == 0, r1.stdout + r.stderr
    bundle_dir = ROOT / "reports/edge_encoder_air_gap_bundle_v1_latest"
    assert (bundle_dir / "bundle_manifest.json").is_file()
    wire_only = json.loads((bundle_dir / "wire/wire_only_export.json").read_text(encoding="utf-8"))
    assert wire_only["original_bulk_sent"] is False
    r2 = subprocess.run([sys.executable, str(verify)], cwd=ROOT, capture_output=True, text=True)
    assert r2.returncode == 0, r2.stdout + r2.stderr


def test_cross_process_http_determinism_exit_0():
    gate = ROOT / "scripts/check_edge_encoder_cross_process_determinism_v1.py"
    r = subprocess.run([sys.executable, str(gate)], cwd=ROOT, capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr
    doc = json.loads((ROOT / "reports/edge_encoder_cross_process_determinism_v1_latest.json").read_text(encoding="utf-8"))
    assert doc.get("fingerprint_match") is True
    assert doc.get("expand_text_match") is True


def test_portable_launcher_build():
    script = ROOT / "scripts/build_edge_encoder_sdk_portable_launcher_v1.py"
    r = subprocess.run([sys.executable, str(script)], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    out = ROOT / "reports/edge_encoder_sdk_portable_launcher_v1_latest/edge-smoke.ps1"
    assert out.is_file()


def test_pyinstaller_readiness_gate():
    build = ROOT / "scripts/build_edge_encoder_sdk_pyinstaller_v1.py"
    gate = ROOT / "scripts/check_edge_encoder_pyinstaller_readiness_v1.py"
    r1 = subprocess.run([sys.executable, str(build)], cwd=ROOT, capture_output=True, text=True)
    assert r1.returncode == 0, r1.stdout + r1.stderr
    r2 = subprocess.run([sys.executable, str(gate)], cwd=ROOT, capture_output=True, text=True)
    assert r2.returncode == 0, r2.stdout + r2.stderr
    doc = json.loads((ROOT / "docs/final/artifacts/edge_encoder_pyinstaller_readiness_v1_latest.json").read_text(encoding="utf-8"))
    assert doc["send_gate"] == "HOLD"


def test_vpc_deploy_runbook_build():
    script = ROOT / "scripts/build_edge_encoder_vpc_deploy_runbook_v1.py"
    r = subprocess.run([sys.executable, str(script)], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    doc = json.loads((ROOT / "docs/final/artifacts/edge_encoder_vpc_deploy_runbook_v1_latest.json").read_text(encoding="utf-8"))
    assert doc["deployment_mode"] == "customer_vpc_on_prem"
    assert len(doc.get("phases") or []) >= 5
    assert doc["original_bulk_sent"] is False


def test_vpc_checklist_html_build():
    script = ROOT / "scripts/build_edge_encoder_vpc_checklist_html_v1.py"
    r = subprocess.run([sys.executable, str(script)], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    html_path = ROOT / "reports/demo/edge_encoder_vpc_deploy_checklist_v1.html"
    assert html_path.is_file()
    text = html_path.read_text(encoding="utf-8")
    assert "original_bulk_sent" in text
    assert "FAIL-COMP-004" in text


def test_pyinstaller_binary_smoke_gate():
    gate = ROOT / "scripts/check_edge_encoder_pyinstaller_binary_smoke_v1.py"
    r = subprocess.run([sys.executable, str(gate)], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    doc = json.loads((ROOT / "reports/edge_encoder_pyinstaller_binary_smoke_v1_latest.json").read_text(encoding="utf-8"))
    assert doc.get("ok") is True or doc.get("skipped") is True


def test_vpc_deploy_package_zip_build():
    bundle_builder = ROOT / "scripts/build_edge_encoder_air_gap_bundle_v1.py"
    r0 = subprocess.run([sys.executable, str(bundle_builder)], cwd=ROOT, capture_output=True, text=True)
    assert r0.returncode == 0, r0.stdout + r0.stderr
    script = ROOT / "scripts/build_edge_encoder_vpc_deploy_package_v1.py"
    r = subprocess.run([sys.executable, str(script)], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    doc = json.loads(
        (ROOT / "docs/final/artifacts/edge_encoder_vpc_deploy_package_v1_latest.json").read_text(encoding="utf-8")
    )
    assert doc["send_gate"] == "HOLD"
    assert doc["original_bulk_sent"] is False
    zip_path = ROOT / doc["zip_path"]
    assert zip_path.is_file()
