"""Gate for myeongni+sasang GraphRAG Ollama live bench artifact."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_myeongni_sasang_graphrag_ollama_live_bench_gate_passes() -> None:
    bench = ROOT / "reports/myeongni_sasang_graphrag_ollama_live_bench_v1_latest.json"
    assert bench.is_file(), f"missing bench artifact: {bench}"
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/check_myeongni_sasang_graphrag_ollama_live_bench_gate_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    gate = ROOT / "docs/final/artifacts/myeongni_sasang_graphrag_ollama_live_bench_gate_v1_latest.json"
    doc = json.loads(gate.read_text(encoding="utf-8-sig"))
    assert doc.get("ok") is True
    assert doc.get("wires_to_scoring_core") is False
    assert "사이드카" in (doc.get("product_policy_ko") or "")
