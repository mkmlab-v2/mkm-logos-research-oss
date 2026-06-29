"""Premium CS customer-masked fill template builder."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "scripts/build_wtt_premium_cs_customer_template_v1.py"
VALIDATE = ROOT / "scripts/validate_wtt_pilot_jsonl_v1.py"


def test_build_20_premium_cs_template(tmp_path: Path) -> None:
    out = tmp_path / "premium_cs.jsonl"
    proc = subprocess.run(
        [sys.executable, str(BUILD), "--out-jsonl", str(out), "--sessions", "20"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    lines = [ln for ln in out.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 20
    row = json.loads(lines[0])
    assert row["domain_tag"] == "customer-support-chat"
    assert "pilot_fill_template" in row["labels"]
    assert "synthetic_stub" not in row["labels"]
    assert "synthetic_spicy" not in row["labels"]
    assert row["customer_provided"] is False


def test_premium_cs_template_validates_strict(tmp_path: Path) -> None:
    out = tmp_path / "premium_cs.jsonl"
    subprocess.run(
        [sys.executable, str(BUILD), "--out-jsonl", str(out), "--sessions", "20"],
        cwd=str(ROOT),
        check=True,
    )
    proc = subprocess.run(
        [
            sys.executable,
            str(VALIDATE),
            "--jsonl",
            str(out),
            "--min-sessions",
            "20",
            "--strict",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
