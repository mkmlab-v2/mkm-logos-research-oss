"""Universal Root contributor fixture validate/bench smoke."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
EXAMPLE = ROOT / "tests/fixtures/contributions/pending/contributor_example_v1.json"


def test_contributor_example_shard_validates() -> None:
    proc = subprocess.run(
        [
            PY,
            "scripts/validate_universal_root_contributor_fixture_v1.py",
            "--json",
            str(EXAMPLE),
            "--stdout-only",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    doc = json.loads(proc.stdout.strip())
    assert doc["validation_ok"] is True
    assert doc["sample_count"] == 3


def test_contributor_bench_example_exit0() -> None:
    proc = subprocess.run(
        [
            PY,
            "scripts/run_universal_root_contributor_bench_v1.py",
            "--shard",
            str(EXAMPLE),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    out = ROOT / "reports/universal_root_contributor_bench_v1_latest.json"
    assert out.is_file()
    doc = json.loads(out.read_text(encoding="utf-8-sig"))
    assert doc["ok"] is True
    assert doc["telemetry"] is False


def test_missing_contributor_labels_fails() -> None:
    bad = {
        "schema": "nsm_41k_lexicon_crosswalk_contrib_v1",
        "research_only": True,
        "send_gate": "HOLD",
        "pair_count": 1,
        "samples": [
            {
                "prime_en": "bad",
                "probe_tokens": ["bad"],
                "contributor_provided": True,
                "customer_provided": False,
                "labels": ["research_only"],
                "source_note": "missing contributor labels",
            }
        ],
    }
    tmp = ROOT / "reports/_tmp_contributor_bad_v1.json"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text(json.dumps(bad), encoding="utf-8")
    try:
        proc = subprocess.run(
            [
                PY,
                "scripts/validate_universal_root_contributor_fixture_v1.py",
                "--json",
                str(tmp),
                "--min-rows",
                "1",
                "--stdout-only",
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode != 0
    finally:
        if tmp.is_file():
            tmp.unlink()
