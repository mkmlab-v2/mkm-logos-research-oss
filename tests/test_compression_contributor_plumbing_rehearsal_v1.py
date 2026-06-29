"""Gate-plumbing rehearsal corpus + candidate rehearsal flag."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD_CORPUS = ROOT / "scripts/build_compression_contributor_gate_plumbing_rehearsal_corpus_v1.py"
VALIDATE = ROOT / "scripts/validate_compression_contributor_jsonl_v1.py"
BUILD_CANDIDATE = ROOT / "scripts/build_compression_contributor_promotion_candidate_v1.py"


def test_plumbing_corpus_validates(tmp_path: Path) -> None:
    out = tmp_path / "plumbing.jsonl"
    proc = subprocess.run(
        [sys.executable, str(BUILD_CORPUS), "--out-jsonl", str(out), "--rows", "12"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    vout = tmp_path / "validate.json"
    vproc = subprocess.run(
        [sys.executable, str(VALIDATE), "--jsonl", str(out), "--out-json", str(vout), "--min-rows", "10"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert vproc.returncode == 0, vproc.stderr + vproc.stdout
    doc = json.loads(vout.read_text(encoding="utf-8"))
    assert doc["validation_ok"] is True
    first = json.loads(out.read_text(encoding="utf-8").splitlines()[0])
    assert first.get("rehearsal_only") is True
    assert "gate_plumbing_rehearsal" in first.get("labels", [])


def test_candidate_rehearsal_flag(tmp_path: Path) -> None:
    validate = tmp_path / "validate.json"
    validate.write_text(
        json.dumps({"validation_ok": True, "row_count": 12, "input_jsonl": "x.jsonl", "input_sha256": "abc"}),
        encoding="utf-8",
    )
    poc = tmp_path / "poc.json"
    poc.write_text(
        json.dumps(
            {
                "case_count": 12,
                "cases_passed": 8,
                "parse_or_api_failures": 0,
                "aggregate": {"mean_jaccard_proxy": 0.8, "mean_token_saving_rate_proxy": 0.15},
            }
        ),
        encoding="utf-8",
    )
    out = tmp_path / "candidate.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(BUILD_CANDIDATE),
            "--validate-json",
            str(validate),
            "--poc-json",
            str(poc),
            "--out-json",
            str(out),
            "--rehearsal-only",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("rehearsal_only") is True
    assert doc.get("commander_may_apply_track_a_bridge") is True
    assert "cite_as_github_moat_evidence" in doc.get("forbidden_actions", [])
