from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_logos_studio_graphrag_insight_ab_bench_smoke() -> None:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/run_logos_studio_graphrag_insight_ab_bench_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    out = ROOT / "docs/final/artifacts/logos_studio_graphrag_insight_ab_bench_v1_latest.json"
    assert out.is_file(), f"missing artifact: {out}"
    doc = json.loads(out.read_text(encoding="utf-8-sig"))
    assert doc.get("schema") == "logos_studio_graphrag_insight_ab_bench_v1"
    assert doc.get("wires_to_scoring_core") is False
    raw = (doc.get("raw_repair_dual") or {}).get("raw") or {}
    assert raw.get("rows", 0) >= 6
