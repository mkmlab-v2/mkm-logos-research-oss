"""Tests for digested fact arxiv binding check."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECK = ROOT / "scripts/check_digested_fact_arxiv_binding_v1.py"
HYBRID = ROOT / "docs/final/artifacts/tier0_hybrid_ai_web_sweep_2026-06-20_digested_facts_latest.json"


def test_arxiv_binding_check_hybrid_exit_zero(tmp_path: Path) -> None:
    assert HYBRID.is_file(), "run hybrid digestion chain first"
    out = tmp_path / "binding.json"
    proc = subprocess.run(
        [sys.executable, str(CHECK), "--input", str(HYBRID), "--out", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["ok"] is True
    assert doc["error_count"] == 0


def test_arxiv_binding_detects_ce_collm_misbind(tmp_path: Path) -> None:
    from scripts.check_digested_fact_arxiv_binding_v1 import check_bindings

    doc = {
        "facts": [
            {
                "fact_id": "bad_bind",
                "comparison_arm": "CE-CoLLM",
                "provenance": {"extraction_method": "explicit_block", "arxiv_id": "2507.16731"},
            }
        ]
    }
    registry = json.loads(
        (ROOT / "docs/final/artifacts/mkm_digested_arxiv_binding_registry_v1.json").read_text(
            encoding="utf-8"
        )
    )
    issues = check_bindings(doc, registry=registry, source_path="test.json")
    assert any(i["severity"] == "error" for i in issues)
