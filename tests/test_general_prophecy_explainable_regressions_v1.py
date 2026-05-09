from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD_SCRIPT = ROOT / "scripts" / "build_general_prophecy_explainable_v1.py"
QUALITY_SCRIPT = ROOT / "scripts" / "report_general_prophecy_explainability_quality_v1.py"

FIX_SEED5 = ROOT / "tests" / "fixtures" / "general_prophecy_registry_seed_5_v1.json"
FIX_MACRO2026 = ROOT / "tests" / "fixtures" / "general_prophecy_registry_macro_h2_2026_pack_v1.json"
FIX_BRIER = ROOT / "tests" / "fixtures" / "general_prophecy_registry_brier_smoke_v1.json"


def _run_build(inp: Path, out: Path) -> dict:
    cp = subprocess.run(
        [
            sys.executable,
            str(BUILD_SCRIPT),
            "--input",
            str(inp),
            "--output",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    return json.loads(out.read_text(encoding="utf-8"))


def _run_quality(inp: Path, out: Path) -> dict:
    cp = subprocess.run(
        [
            sys.executable,
            str(QUALITY_SCRIPT),
            "--input",
            str(inp),
            "--output",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    return json.loads(out.read_text(encoding="utf-8"))


def test_seed_python_github_reproducible_evidence_fallback(tmp_path: Path):
    explainable = tmp_path / "seed5_explainable.json"
    doc = _run_build(FIX_SEED5, explainable)
    by_id = {q["question_id"]: q for q in doc.get("questions", [])}

    for qid in ("seed.python_stable_314_before_20260601", "seed.github_repo_default_branch_main_20261231"):
        q = by_id[qid]
        bib = q["explanation"]["biblical"]
        assert bib["verse_matches"], f"missing verse matches for {qid}"
        assert float(bib["keyword_coverage"]) >= 0.25

    quality = _run_quality(explainable, tmp_path / "seed5_quality.json")
    qrows = {r["question_id"]: r for r in quality.get("rows", [])}
    assert qrows["seed.python_stable_314_before_20260601"]["reproducible_evidence_ok"] is True
    assert qrows["seed.github_repo_default_branch_main_20261231"]["reproducible_evidence_ok"] is True


def test_gp_2026_reproducible_evidence_fallback(tmp_path: Path):
    explainable = tmp_path / "gp2026_explainable.json"
    doc = _run_build(FIX_MACRO2026, explainable)
    for q in doc.get("questions", []):
        qid = q.get("question_id", "")
        if not str(qid).startswith("gp_2026_"):
            continue
        bib = q["explanation"]["biblical"]
        assert bib["verse_matches"], f"missing verse matches for {qid}"
        assert float(bib["keyword_coverage"]) >= 0.3

    quality = _run_quality(explainable, tmp_path / "gp2026_quality.json")
    for row in quality.get("rows", []):
        if str(row.get("question_id", "")).startswith("gp_2026_"):
            assert row["reproducible_evidence_ok"] is True


def test_ci_brier_reproducible_evidence_fallback(tmp_path: Path):
    explainable = tmp_path / "brier_explainable.json"
    _run_build(FIX_BRIER, explainable)
    quality = _run_quality(explainable, tmp_path / "brier_quality.json")
    for row in quality.get("rows", []):
        if str(row.get("question_id", "")).startswith("ci.brier_"):
            assert row["reproducible_evidence_ok"] is True

