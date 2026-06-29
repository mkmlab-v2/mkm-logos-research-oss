"""Regression: DR bench ops paste builder."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "scripts/build_mkm_deep_research_bench_ops_paste_v1.py"
BENCH = ROOT / "reports/mkm_deep_research_bench_mini_v1_latest.json"
OUT_MD = ROOT / "reports/mkm_deep_research_bench_ops_paste_v1_latest.md"
OUT_JSON = ROOT / "reports/mkm_deep_research_bench_ops_paste_v1_latest.json"


def test_ops_paste_builder_exit_zero(tmp_path: Path) -> None:
    assert BENCH.is_file(), "run DR bench first or use committed latest json"
    out_json = tmp_path / "paste.json"
    out_md = tmp_path / "paste.md"
    r = subprocess.run(
        [
            sys.executable,
            str(BUILD),
            "--out-json",
            str(out_json),
            "--out-md",
            str(out_md),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    assert out_md.is_file()
    assert out_json.is_file()
    md = out_md.read_text(encoding="utf-8")
    assert "Commander one-screen" in md
    assert "send_gate" in md
    assert "baseline/challenge" in md
    doc = json.loads(out_json.read_text(encoding="utf-8"))
    assert doc["schema"] == "mkm_deep_research_bench_ops_paste_v1"
    assert doc["send_gate"] == "HOLD"
    assert doc["paste_build_ok"] is True
    assert doc.get("commander_review_only") is True


def test_ops_paste_commander_signoff(tmp_path: Path) -> None:
    out_json = tmp_path / "paste.json"
    out_md = tmp_path / "paste.md"
    out_json.write_text(
        json.dumps(
            {
                "commander_signoff_at": "2026-06-20T12:00:00Z",
                "commander_signoff_note": "weekly ok",
            }
        ),
        encoding="utf-8",
    )
    r = subprocess.run(
        [
            sys.executable,
            str(BUILD),
            "--input",
            str(BENCH),
            "--out-json",
            str(out_json),
            "--out-md",
            str(out_md),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads(out_json.read_text(encoding="utf-8"))
    assert doc["paste_copy_approved"] is True
    assert doc["commander_signoff_at"] == "2026-06-20T12:00:00Z"
    assert "paste_copy_approved:** true" in out_md.read_text(encoding="utf-8")
