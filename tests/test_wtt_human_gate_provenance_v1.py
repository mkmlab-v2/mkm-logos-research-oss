"""WTT human gate + provenance ledger v1."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "scripts/run_wtt_human_gate_interactive_v1.py"
CHECK = ROOT / "scripts/check_wtt_pilot_provenance_v1.py"


def _source_rows(tenant: str, n: int = 20) -> list[dict]:
    return [
        {
            "session_id": f"{tenant}-session-{i:03d}",
            "text": f"[masked] 환불 문의 ███ 세션 {i} 010-****-{1000+i:04d}",
            "domain_tag": "customer-support-chat",
        }
        for i in range(1, n + 1)
    ]


def test_human_gate_writes_intake_and_provenance(tmp_path: Path) -> None:
    tenant = "test-wtt-pilot-v1"
    src = tmp_path / "source.jsonl"
    src.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in _source_rows(tenant)) + "\n",
        encoding="utf-8",
    )
    intake = ROOT / f"data/wtt/intake/{tenant}.jsonl"
    prov = ROOT / f"data/wtt/provenance/{tenant}.provenance.json"
    intake.unlink(missing_ok=True)
    prov.unlink(missing_ok=True)

    proc = subprocess.run(
        [
            sys.executable,
            str(GATE),
            "--tenant-id",
            tenant,
            "--source-jsonl",
            str(src),
            "--consent-source-ref",
            "data/wtt/provenance/evidence/test_consent.txt",
            "--approve-all",
            "--public-facing-ok",
            "--out",
            str(tmp_path / "gate.json"),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert intake.is_file()
    assert prov.is_file()
    lines = [ln for ln in intake.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 20
    row = json.loads(lines[0])
    assert row["customer_provided"] is True
    assert "human_gate_approved" in row["labels"]
    assert "pilot_fill_template" not in row["labels"]

    chk = subprocess.run(
        [
            sys.executable,
            str(CHECK),
            "--tenant-id",
            tenant,
            "--strict",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert chk.returncode == 0, chk.stderr or chk.stdout

    intake.unlink(missing_ok=True)
    prov.unlink(missing_ok=True)
