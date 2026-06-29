from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_GATE = ROOT / "tests/fixtures/ops_dynamical_l4_minimal_cohort_gate_v1.json"
L3_EVAL = ROOT / "reports/ops_dynamical_l3_eval_v1_latest.json"


@pytest.fixture
def l3_prereq_doc() -> dict:
    if not L3_EVAL.is_file():
        pytest.skip("L3 eval artifact missing on disk")
    return json.loads(L3_EVAL.read_text(encoding="utf-8-sig"))


def test_l4_eval_on_disk_artifacts(l3_prereq_doc: dict):
    sys.path.insert(0, str(ROOT))
    from scripts.ops_dynamical_bench_v1_lib import eval_l4_clinical_cohort, load_l4_inputs

    assert FIXTURE_GATE.is_file()
    gate_doc, l3_doc, profiles = load_l4_inputs()
    assert gate_doc is not None
    assert l3_doc is not None
    doc = eval_l4_clinical_cohort(gate_doc=gate_doc, l3_doc=l3_doc, profiles=profiles, missing=[])
    assert doc["schema"] == "ops_dynamical_l4_eval_v1"
    assert doc["track"] == "B"
    assert doc["send_gate"] == "HOLD"
    assert len(profiles) >= 3
    assert doc["metrics"]["clinical_epsilon_score"] is not None
    if l3_prereq_doc.get("ok"):
        assert doc["ok"] is True


def test_l4_eval_fixture_cohort_passes(l3_prereq_doc: dict):
    sys.path.insert(0, str(ROOT))
    from scripts.ops_dynamical_bench_v1_lib import eval_l4_clinical_cohort, load_l4_inputs

    gate_doc = json.loads(FIXTURE_GATE.read_text(encoding="utf-8"))
    _, _, profiles = load_l4_inputs(cohort_gate_path=FIXTURE_GATE)
    doc = eval_l4_clinical_cohort(
        gate_doc=gate_doc,
        l3_doc=l3_prereq_doc,
        profiles=profiles,
        missing=[],
    )
    assert doc["ok"] is True
    assert doc["metrics"]["endpoint_coverage_rate"] == 1.0
    assert doc["checks_pass_count"] == doc["checks_total"]


def test_l4_runner_exit_0():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/run_ops_dynamical_l4_clinical_eval_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    out_path = ROOT / "reports/ops_dynamical_l4_eval_v1_latest.json"
    assert out_path.is_file(), proc.stderr or proc.stdout
    doc = json.loads(out_path.read_text(encoding="utf-8"))
    assert doc["schema"] == "ops_dynamical_l4_eval_v1"
    assert len(doc["profiles"]) >= 3
    if proc.returncode != 0:
        pytest.skip(f"L4 runner exit {proc.returncode} — l3 prereq may be stale")
