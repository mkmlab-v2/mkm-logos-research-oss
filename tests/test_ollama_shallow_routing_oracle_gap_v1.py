"""routing_oracle_gap shadow eval for Ollama shallow router v1 [HYPO]."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHADOW_BENCH = ROOT / "tests/fixtures/ollama_shallow_router_bench_shadow_perfect_v1.json"
GAP_OUT = ROOT / "reports/ollama_shallow_routing_oracle_gap_v1_test_latest.json"


def test_routing_oracle_gap_shadow_perfect_exit0() -> None:
    if GAP_OUT.exists():
        GAP_OUT.unlink()
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/build_ollama_shallow_routing_oracle_gap_v1.py"),
            "--bench-json",
            str(SHADOW_BENCH),
            "--out-json",
            str(GAP_OUT),
            "--max-oracle-gap",
            "0.0",
            "--min-cloud-skip-ratio",
            "1.0",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    doc = json.loads(GAP_OUT.read_text(encoding="utf-8"))
    assert doc.get("schema") == "ollama_shallow_routing_oracle_gap_v1"
    assert doc.get("send_gate") == "HOLD"
    raw = doc.get("raw") or {}
    assert raw.get("routing_oracle_gap") == 0.0
    assert raw.get("router_hit_rate") == 1.0
    assert raw.get("cloud_skip_ratio") == 1.0
    assert raw.get("deep_routing_recall") == 1.0
    assert doc.get("delta", {}).get("routing_oracle_gap_delta_repair_v2_minus_raw") == 0.0


def test_routing_oracle_gap_from_latest_bench_if_live() -> None:
    bench = ROOT / "reports/ollama_shallow_router_bench_v1_latest.json"
    if not bench.is_file():
        return
    doc = json.loads(bench.read_text(encoding="utf-8"))
    if doc.get("mode") != "live":
        return
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/build_ollama_shallow_routing_oracle_gap_v1.py"),
            "--bench-json",
            str(bench),
            "--max-oracle-gap",
            "0.25",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
