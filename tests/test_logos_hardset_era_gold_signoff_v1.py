from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_READINESS = _ROOT / "scripts" / "check_logos_hardset_era_gold_signoff_readiness_v1.py"
_MARK = _ROOT / "scripts" / "mark_logos_hardset_era_gold_human_signoff_v1.py"


def test_readiness_fails_when_overrides_empty(tmp_path: Path) -> None:
    ov = tmp_path / "ov.json"
    ov.write_text(
        json.dumps(
            {
                "schema": "logos_chronology_hardset_era_gold_overrides_v1",
                "policy": {"human_signoff_completed": False},
                "overrides": [],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    out = tmp_path / "ready.json"
    cp = subprocess.run(
        [sys.executable, str(_READINESS), "--overrides-json", str(ov), "--output-json", str(out)],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 2
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["ready_for_human_margin_report"] is False


def test_human_margin_report_after_signoff() -> None:
    ov = _ROOT / "docs/final/artifacts/fixtures/logos_chronology_hardset_era_gold_overrides_v1.json"
    primary = _ROOT / "docs/final/artifacts/logos_chronology_hardset_text_blind_v2_eval_v1_latest.json"
    if not ov.is_file() or not primary.is_file():
        return
    cp = subprocess.run(
        [sys.executable, str(_ROOT / "scripts/build_logos_hardset_era_human_margin_report_v1.py")],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads((_ROOT / "reports/logos_hardset_era_human_margin_report_v1_latest.json").read_text(encoding="utf-8"))
    assert doc["ready"] is True
    assert doc["policy"]["ms_citation_allowed"] is False


def test_mark_signoff_requires_overrides(tmp_path: Path) -> None:
    ov = tmp_path / "ov.json"
    ov.write_text(
        json.dumps(
            {"schema": "logos_chronology_hardset_era_gold_overrides_v1", "policy": {}, "overrides": []},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    cp = subprocess.run(
        [sys.executable, str(_MARK), "--overrides-json", str(ov)],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode != 0
