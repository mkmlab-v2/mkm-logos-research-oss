"""[HYPO] Verbatim spine codec + bench smoke."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _run(script: str, *extra: str) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, str(ROOT / script), *extra]
    return subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)


def test_verbatim_spine_roundtrip_unit() -> None:
    from scripts.nextgen_verbatim_spine_codec_v1 import (
        verbatim_spine_decode,
        verbatim_spine_decode_binary,
        verbatim_spine_encode,
        verbatim_spine_packet_to_binary,
    )

    raw = "손실 대속 contract ENTRY_16 read-only"
    pkt = verbatim_spine_encode(raw)
    assert verbatim_spine_decode(pkt) == raw
    blob = verbatim_spine_packet_to_binary(pkt)
    assert verbatim_spine_decode_binary(blob) == raw


def test_verbatim_spine_bench_golden40() -> None:
    out = ROOT / "experiments/nextgen_clean_slate_cpu_v1/results/_test_spine_bench_v1.json"
    proc = _run(
        "scripts/run_nextgen_verbatim_spine_bench_v1.py",
        "--out-json",
        str(out),
        "--mode",
        "spine_only",
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    agg = doc["arms"][0]["aggregate"]
    assert agg["byte_exact_subset_parity"] == 1.0
    assert agg["avg_reconstruction_fidelity_jaccard"] == 1.0


def test_hybrid_spine_logos_stack() -> None:
    out = (
        ROOT
        / "experiments/nextgen_clean_slate_cpu_v1/results/_test_hybrid_logos_stack_v1.json"
    )
    proc = _run(
        "scripts/run_nextgen_hybrid_spine_logos_stack_v1.py",
        "--out-json",
        str(out),
        "--keep-ratio",
        "0.80",
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["aggregate"]["byte_exact_subset_parity"] == 1.0
