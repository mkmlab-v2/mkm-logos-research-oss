"""HAAN → SASANG analogy_bench sidecar wire."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_build_haan_sasang_analogy_bench_wire_v1() -> None:
    out = ROOT / "docs/final/artifacts/haan_sasang_analogy_bench_wire_v1_latest.json"
    cp = subprocess.run(
        ["py", str(ROOT / "scripts/build_haan_sasang_analogy_bench_wire_v1.py"), "--out", str(out)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "haan_sasang_analogy_bench_wire_v1"
    assert doc["send_gate"] == "HOLD"
    assert doc["wire_count"] >= 1
    for w in doc["wires"]:
        assert w["wire_link_type"] == "analogy_bench"
        assert "[HYPO]" in w["rationale"]
        assert w["corpus_type"] == "haan_paper_digest_tier0"
