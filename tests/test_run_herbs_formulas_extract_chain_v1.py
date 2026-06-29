"""Tests for herbs_formulas extract chain (build + optional citation skip)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHAIN = ROOT / "scripts/run_herbs_formulas_extract_chain_v1.py"
INPUT_MD = ROOT / "tests/fixtures/herbs_formulas_lecture_extract_input_v1.md"
DUAL_MD = ROOT / "tests/fixtures/herbs_formulas_lecture_dual_citation_v1.md"


def _run_chain(
    *,
    input_md: Path,
    out_json: Path,
    extra_args: list[str] | None = None,
) -> subprocess.CompletedProcess[str]:
    cmd = [
        sys.executable,
        str(CHAIN),
        "--input",
        str(input_md),
        "--out-json",
        str(out_json),
        "--no-write-locks",
    ]
    if extra_args:
        cmd.extend(extra_args)
    return subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)


def test_herbs_extract_chain_builds_and_skips_citation_locks(tmp_path: Path) -> None:
    out = tmp_path / "chain.json"
    proc = _run_chain(input_md=INPUT_MD, out_json=out)
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["ok"] is True
    assert doc["extract"]["schema"] == "herbs_formulas_extract_v1"
    assert doc["steps"]["dosage_validate"]["exit_code"] == 0
    assert doc["doi_lock"]["skipped"] is True
    assert doc["pmid_lock"]["skipped"] is True


def test_herbs_extract_chain_dual_citation_offline_runs_locks(tmp_path: Path) -> None:
    out = tmp_path / "chain_dual.json"
    proc = _run_chain(input_md=DUAL_MD, out_json=out, extra_args=["--offline"])
    assert proc.returncode == 0, proc.stderr + proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["ok"] is True
    assert doc["offline"] is True
    assert doc["extract"]["schema"] == "herbs_formulas_extract_v1"
    assert doc["extract"]["provenance"]["source_material_ids"] == [
        "fixture:lecture_bangje_2026_dual_citation_demo"
    ]
    assert doc["doi_lock"]["ok"] is True
    assert doc["doi_lock"].get("skipped") is not True
    assert doc["doi_lock"]["total_dois"] == 1
    assert doc["pmid_lock"]["ok"] is True
    assert doc["pmid_lock"].get("skipped") is not True
    assert doc["pmid_lock"]["total_pmids"] == 2


def test_herbs_extract_chain_skip_doi_lock_flag(tmp_path: Path) -> None:
    out = tmp_path / "chain_no_doi.json"
    proc = _run_chain(
        input_md=DUAL_MD,
        out_json=out,
        extra_args=["--offline", "--skip-doi-lock"],
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["doi_lock_enabled"] is False
    assert doc["doi_lock"] is None
    assert doc["pmid_lock"]["ok"] is True


def test_herbs_extract_chain_skip_pmid_lock_flag(tmp_path: Path) -> None:
    out = tmp_path / "chain_no_pmid.json"
    proc = _run_chain(
        input_md=DUAL_MD,
        out_json=out,
        extra_args=["--offline", "--skip-pmid-lock"],
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["pmid_lock_enabled"] is False
    assert doc["pmid_lock"] is None
    assert doc["doi_lock"]["ok"] is True
