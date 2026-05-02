# @MKM12-METADATA
# Type: Logic
# Purpose: Regression for myeongni / sasang / logos independent lens v0 runners.
# Keywords: independent_lens, multilens, b-track

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]

_RUNNERS = (
    ("scripts/run_lens_myeongni.py", "myeongni_independent_lens_v0", "myeongni"),
    ("scripts/run_lens_sasang.py", "sasang_independent_lens_v0", "sasang"),
    ("scripts/run_lens_logos.py", "logos_independent_lens_v0", "logos"),
)


@pytest.mark.parametrize("script_rel,schema,lens_id", _RUNNERS)
def test_runner_emits_schema(tmp_path: Path, script_rel: str, schema: str, lens_id: str) -> None:
    runner = _ROOT / script_rel
    assert runner.is_file(), runner
    out = tmp_path / f"lens_{lens_id}.json"
    cmd = [sys.executable, str(runner), "--output", str(out)]
    # data/logos/4lens_batch_sample.json is gitignored; CI has no batch vectors.
    if script_rel.endswith("run_lens_logos.py"):
        cmd.append("--allow-fallback")
    cp = subprocess.run(
        cmd,
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == schema
    assert doc.get("lens_id") == lens_id
    assert doc.get("hypothesis_tier") == "B"
    assert doc.get("boundary_ack") is True
    scores = doc.get("scores") or {}
    assert -1.0 <= float(scores.get("direction_score", 0)) <= 1.0
    assert 0.0 <= float(scores.get("confidence", 0)) <= 1.0


def test_logos_lens_evidence_refs_minimal_fixture(tmp_path: Path) -> None:
    runner = _ROOT / "scripts/run_lens_logos.py"
    fx = _ROOT / "tests/fixtures/logos_4lens_batch_minimal_v1.json"
    out = tmp_path / "logos_evidence.json"
    cp = subprocess.run(
        [sys.executable, str(runner), "--batch-json", str(fx), "--output", str(out)],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "logos_independent_lens_v0"
    refs = doc.get("evidence_refs") or []
    assert len(refs) == 2
    assert refs[0].get("verse_id") == "JHN.3.16"
    assert refs[0].get("quote_hash", "").startswith("sha256:")
    assert "[#JHN.3.16]" in (refs[0].get("hash_tagged_snippet") or "")
    nar = doc.get("narrative_snippet_guarded") or ""
    assert "[#JHN.3.16]" in nar and "[#PSA.23.1]" in nar
    assert doc.get("snippet_guard_policy")
