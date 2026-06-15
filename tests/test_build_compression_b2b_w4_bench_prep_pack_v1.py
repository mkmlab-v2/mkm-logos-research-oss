"""W4 B2B bench prep pack builder."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/build_compression_b2b_w4_bench_prep_pack_v1.py"
OUT = ROOT / "docs/final/artifacts/compression_b2b_w4_bench_prep_pack_v1_latest.json"
HYPO_AUDIT = ROOT / "docs/final/artifacts/compression_mask_hypo_passive_cross_audit_v1_latest.json"


def test_build_w4_pack_exit_zero_when_hypo_passes() -> None:
    if not HYPO_AUDIT.is_file():
        subprocess.run(
            [sys.executable, str(ROOT / "scripts/run_compression_mask_hypo_passive_cross_audit_v1.py")],
            cwd=str(ROOT),
            check=True,
            timeout=180,
        )
    proc = subprocess.run(
        [sys.executable, str(BUILDER)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(OUT.read_text(encoding="utf-8"))
    assert doc["schema"] == "compression_b2b_w4_bench_prep_pack_v1"
    assert doc["external_launch_decision"] == "BLOCKED_BY_READINESS"
    assert doc["guardrails"]["fail_comp_004"] is True
    mask = doc["mask_hypo_chain"]
    assert mask["all_steps_pass"] is True
    assert mask["v2_stub_shadow_bind_metadata"] is True
    assert doc["aggregate"]["ready_for_external_send"] is False


def test_build_pack_lib_shape() -> None:
    from scripts.build_compression_b2b_w4_bench_prep_pack_v1 import build_pack

    doc = build_pack()
    assert "mask_hypo_chain" in doc
    assert doc["scripts"]["w4_routine"] == "scripts/Run-CompressionB2bWeek4Routine_v1.ps1"
