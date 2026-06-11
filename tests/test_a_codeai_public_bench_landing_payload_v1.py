"""a-codeai open-bench landing payload + materialize smoke."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "docs/final/artifacts/a_codeai_public_reproduce_bundle_v1_latest.json"
PAYLOAD = ROOT / "docs/final/artifacts/a_codeai_public_bench_landing_payload_v1_latest.json"


@pytest.fixture(scope="module")
def ensure_bundle() -> None:
    if BUNDLE.is_file():
        return
    subprocess.run(
        [sys.executable, "scripts/build_a_codeai_public_reproduce_bundle_v1.py"],
        cwd=str(ROOT),
        check=True,
        capture_output=True,
    )


def test_build_bench_landing_payload(ensure_bundle: None) -> None:
    proc = subprocess.run(
        [sys.executable, "scripts/build_a_codeai_public_bench_landing_payload_v1.py"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(PAYLOAD.read_text(encoding="utf-8"))
    assert doc.get("schema") == "a_codeai_public_bench_landing_payload_v1"
    assert doc.get("send_gate") == "HOLD"
    assert doc.get("ready_for_external_send") is False
    public = doc.get("sections", {}).get("public_skus") or []
    assert len(public) == 4
    for row in public:
        assert row.get("corpus_sha256")
        assert row.get("forbidden_headline")
    routed = next((r for r in public if r.get("sku_id") == "compression_api_golden40_public_safe_routed"), None)
    if routed and isinstance(routed.get("mean_token_saving_rate_proxy"), (int, float)):
        assert float(routed["mean_token_saving_rate_proxy"]) > 0.0
        assert routed.get("external_sku") == "MKM-CHAT-D1"


def test_materialize_export_dry_run(ensure_bundle: None) -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/materialize_a_codeai_public_reproduce_bundle_v1.py",
            "--dry-run",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    report = ROOT / "reports/a_codeai_public_reproduce_materialize_v1_latest.json"
    doc = json.loads(report.read_text(encoding="utf-8"))
    assert doc.get("schema") == "a_codeai_public_reproduce_materialize_report_v1"
    assert doc.get("copied_count", 0) >= 50
    assert doc.get("path_candidates", 0) >= doc.get("copied_count", 0)


def test_resolve_export_closure() -> None:
    proc = subprocess.run(
        [sys.executable, "scripts/resolve_a_codeai_public_reproduce_export_closure_v1.py"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    out = json.loads(proc.stdout.strip().splitlines()[-1])
    assert out.get("path_count", 0) >= 20
