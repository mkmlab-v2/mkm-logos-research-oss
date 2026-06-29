"""ko shorts full chain planner + quick offline smoke."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_ko_shorts_full_chain_v1 import build_full_chain_plan, run_full_chain_v1  # noqa: E402


def test_build_full_chain_plan_has_core_steps() -> None:
    plan = build_full_chain_plan(
        skip_fetch=True,
        skip_spike=True,
        skip_burn=False,
        profile="netflix_v16",
        include_tts_bench=False,
        include_alignment_spike=False,
        alignment_backend="auto",
        routing_sidecar=None,
        include_whisperx=False,
        port=8796,
    )
    names = [n for n, _ in plan]
    assert names == ["gate_bench", "burnin_batch", "cursor_ide_qa", "manual_qa_checklist"]


def test_build_full_chain_plan_includes_alignment_spike() -> None:
    plan = build_full_chain_plan(
        skip_fetch=True,
        skip_spike=True,
        skip_burn=True,
        profile="netflix_v16",
        include_tts_bench=False,
        include_alignment_spike=True,
        alignment_backend="auto",
        routing_sidecar=None,
        include_whisperx=False,
        port=8796,
    )
    names = [n for n, _ in plan]
    assert names[:2] == ["alignment_backend_spike", "segment_backend_decision"]
    assert "gate_bench" in names


def test_build_full_chain_plan_includes_delegate_and_drift_kpi() -> None:
    plan = build_full_chain_plan(
        skip_fetch=True,
        skip_spike=True,
        skip_burn=True,
        profile="netflix_v16_pro",
        include_tts_bench=False,
        include_alignment_spike=False,
        alignment_backend="auto",
        routing_sidecar=None,
        include_whisperx=False,
        port=8796,
        include_delegate=True,
        include_drift_kpi=True,
    )
    names = [n for n, _ in plan]
    assert names[-2:] == ["target_wav_delegate", "timing_drift_kpi"]


def test_full_chain_quick_cli() -> None:
    out = ROOT / "reports/ko_shorts_full_chain_quick_test_v1.json"
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/run_ko_shorts_full_chain_v1.py"), "--quick", "--out", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "ko_shorts_full_chain_v1"
    assert doc["ok"] is True
