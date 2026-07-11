"""External-facing Fact-Lock pass."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/check_external_facing_fact_lock_v1.py"


def test_default_scan_exit_0():
    proc = subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    doc = json.loads((ROOT / "reports/external_facing_fact_lock_v1_latest.json").read_text(encoding="utf-8"))
    assert doc["ok"] is True


def test_forbidden_phrase_fails(tmp_path: Path):
    bad = tmp_path / "bad_draft.md"
    bad.write_text("Our global only package achieves zero hallucination in 60 seconds.\n", encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--target", str(bad)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 1
    doc = json.loads((ROOT / "reports/external_facing_fact_lock_v1_latest.json").read_text(encoding="utf-8"))
    assert doc["violation_count"] >= 1


def test_middleware_orphan_headline_fails(tmp_path: Path):
    """Claim-A residual: headline checklist is exit-gated via external fact-lock."""
    bad = tmp_path / "mkm_middleware_claim_a_orphan_draft.md"
    bad.write_text(
        "Keep the corpus local. Send pointers.\nBuyer pitch only. No Blind prefer tension named.\n",
        encoding="utf-8",
    )
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--target", str(bad)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 1, proc.stdout + proc.stderr
    doc = json.loads((ROOT / "reports/external_facing_fact_lock_v1_latest.json").read_text(encoding="utf-8"))
    assert doc["ok"] is False
    assert any(v.get("code") == "headline_reuse_orphan" for v in doc.get("violations") or [])
    assert doc.get("headline_reuse_guard", {}).get("applied") is True


def test_middleware_egress_hero_passes():
    target = ROOT / "docs/final/artifacts/mkm_middleware_l0_send_ready_onepager_v1_latest.md"
    if not target.is_file():
        return
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--target", str(target)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    doc = json.loads((ROOT / "reports/external_facing_fact_lock_v1_latest.json").read_text(encoding="utf-8"))
    assert doc["ok"] is True
    assert doc.get("headline_reuse_guard", {}).get("applied") is True


def test_contract_header_written(tmp_path: Path):
    clean = tmp_path / "clean.md"
    clean.write_text("Artifact-bound discipline with reproducible KPIs. send_gate HOLD.\n", encoding="utf-8")
    contract = tmp_path / "contract.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--target",
            str(clean),
            "--scope",
            "Logos OSS harness smoke only",
            "--write-contract",
            str(contract),
            "--evidence",
            "reports/logos_oss_premarket_smoke_v1_latest.json|py scripts/run_logos_oss_premarket_smoke_v1.py",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    hdr = json.loads(contract.read_text(encoding="utf-8"))
    assert hdr["schema"] == "mkm_external_facing_contract_header_v1"
    assert hdr["scope_closed"] == "Logos OSS harness smoke only"
    assert hdr["send_gate"] == "HOLD"

