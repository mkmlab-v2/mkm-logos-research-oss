from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILD_SCRIPT = ROOT / "scripts" / "build_layer5_human_audit_packet_v1.py"


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def test_build_human_audit_packet(tmp_path: Path) -> None:
    gold = tmp_path / "gold.jsonl"
    packet = tmp_path / "packet.json"
    review_csv = tmp_path / "review.csv"
    _write_jsonl(
        gold,
        [
            {"case_id": "c1", "expected_block": True, "expected_reasons": ["hold"], "review_status": "approved"},
            {"case_id": "c2", "expected_block": False, "expected_reasons": [], "review_status": "approved"},
        ],
    )
    proc = subprocess.run(
        [
            "py",
            str(BUILD_SCRIPT),
            "--goldset-jsonl",
            str(gold),
            "--packet-json",
            str(packet),
            "--review-csv",
            str(review_csv),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    doc = json.loads(packet.read_text(encoding="utf-8"))
    assert doc["schema"] == "layer5_human_audit_packet_v1"
    assert doc["case_count"] == 2
    csv_text = review_csv.read_text(encoding="utf-8")
    assert "case_id,audit_decision,notes" in csv_text
