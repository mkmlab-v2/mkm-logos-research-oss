from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_docling_pdf_ingress_compression_ab_v1.py"
PDF = ROOT / "reports" / "nvidia_inception_pitch_deck_v1.pdf"


def test_pdf_ingress_ab_schema() -> None:
    if not PDF.is_file():
        return
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--skip-docling-run"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode in (0, 1), proc.stderr
    payload = ROOT / "reports" / "docling_pdf_ingress_compression_ab_v1_latest.json"
    assert payload.is_file()
    data = json.loads(payload.read_text(encoding="utf-8"))
    assert data["schema"] == "docling_pdf_ingress_compression_ab_v1"
    assert data["ingress_axis"] == "pdf_document_not_wtt_chat"
    if data["status"] == "ok":
        assert "raw" in data and "repair_v2" in data
        assert "token_saving_rate_proxy_repair_minus_raw" in data["delta"]
