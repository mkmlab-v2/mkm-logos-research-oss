from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_docling_wtt_compression_ab_v1.py"


def test_pre_normalize_pure_r1_no_markdown_injection() -> None:
    from scripts.run_docling_wtt_compression_ab_v1 import _pre_normalize_docling_style

    short = "배송 ███ 아직 안 왔어요."
    out = _pre_normalize_docling_style(short)
    assert "MARKDOWN" not in out
    assert out == short


def test_docling_wtt_ab_schema() -> None:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--sample-count", "3", "--skip-docling-run"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode in (0, 1), proc.stderr
    payload = ROOT / "reports" / "docling_wtt_compression_ab_v1_latest.json"
    assert payload.is_file()
    data = json.loads(payload.read_text(encoding="utf-8"))
    assert data["schema"] == "docling_wtt_compression_ab_v1"
    assert data["disclaimer"] == "research_only"
    if data["status"] == "ok":
        assert "raw" in data
        assert "repair_v2" in data
        assert "per_case" in data
        assert len(data["per_case"]) >= 1
        assert "mean_token_saving_rate_proxy_repair_minus_raw" in data["delta"]
        assert data["raw_vs_repair_contract"]["markdown_hint_injection"] is False
