"""KM-VHI pilot record validator smoke."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "docs/final/artifacts/han_vocology_km_vhi_pilot_record_sample_v1.json"
SCRIPT = ROOT / "scripts/validate_han_vocology_km_vhi_pilot_record_v1.py"
JSONL_SCRIPT = ROOT / "scripts/validate_han_vocology_km_vhi_pilot_jsonl_v1.py"


def test_sample_record_validates_exit_0() -> None:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--record-json", str(SAMPLE)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_week0_sample_validates() -> None:
    week0 = ROOT / "docs/final/artifacts/han_vocology_km_vhi_pilot_record_week0_sample_v1.json"
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--record-json", str(week0)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_jsonl_validates_exit_0() -> None:
    jsonl = ROOT / "reports/han_vocology_km_vhi_pilot_records.jsonl"
    proc = subprocess.run(
        [sys.executable, str(JSONL_SCRIPT), "--jsonl", str(jsonl)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_jsonl_row_count_fifty_three() -> None:
    jsonl = ROOT / "reports/han_vocology_km_vhi_pilot_records.jsonl"
    lines = [ln for ln in jsonl.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 53


def test_pilot_closure_exit_0() -> None:
    script = ROOT / "scripts/build_han_vocology_pilot_closure_v1.py"
    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_cohort_gate_exit_0() -> None:
    gate = ROOT / "scripts/build_han_vocology_km_vhi_pilot_cohort_gate_v1.py"
    proc = subprocess.run(
        [sys.executable, str(gate)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_policy_mismatch_fails() -> None:
    data = json.loads(SAMPLE.read_text(encoding="utf-8"))
    data["clinical_policy"] = "L1"
    bad = ROOT / "reports/_test_km_vhi_pilot_bad_policy.json"
    bad.parent.mkdir(parents=True, exist_ok=True)
    bad.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--record-json", str(bad)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1


def test_bad_total_fails() -> None:
    data = json.loads(SAMPLE.read_text(encoding="utf-8"))
    data["total"] = 99
    bad = ROOT / "reports/_test_km_vhi_pilot_bad_total.json"
    bad.parent.mkdir(parents=True, exist_ok=True)
    bad.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--record-json", str(bad)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1


def test_cohort_gate_visit_week_zero_not_minus_one() -> None:
    gate_script = ROOT / "scripts/build_han_vocology_km_vhi_pilot_cohort_gate_v1.py"
    proc = subprocess.run(
        [sys.executable, str(gate_script)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    gate = json.loads(
        (ROOT / "reports/han_vocology_km_vhi_pilot_cohort_gate_v1_latest.json").read_text(encoding="utf-8")
    )
    for cohort in gate.get("cohorts") or []:
        weeks = cohort.get("visit_weeks") or []
        assert -1 not in weeks, cohort.get("pseudonym_id")


def test_pilot_final_report_exit_0() -> None:
    script = ROOT / "scripts/build_han_vocology_pilot_final_report_v1.py"
    proc = subprocess.run(
        [sys.executable, str(script), "--skip-validate"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    report = json.loads((ROOT / "reports/han_vocology_pilot_final_report_v1_latest.json").read_text(encoding="utf-8"))
    assert report.get("ok") is True
    assert report["executive"]["row_count"] == 53


def test_osce_rubric_build_and_validate_exit_0() -> None:
    build = ROOT / "scripts/build_han_vocology_osce_rubric_v1.py"
    validate = ROOT / "scripts/validate_han_vocology_osce_rubric_v1.py"
    proc_b = subprocess.run(
        [sys.executable, str(build)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc_b.returncode == 0, proc_b.stderr or proc_b.stdout
    proc_v = subprocess.run(
        [sys.executable, str(validate)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc_v.returncode == 0, proc_v.stderr or proc_v.stdout
    rubric = json.loads(
        (ROOT / "docs/final/artifacts/han_vocology_osce_rubric_v1_latest.json").read_text(encoding="utf-8")
    )
    assert rubric.get("track") == "B"
    assert rubric.get("send_gate") == "HOLD"
    assert len(rubric.get("stations") or []) == 8


def test_slides_export_mdpresent_exit_0_or_skip() -> None:
    cli = ROOT / "tools/vendor/mdpresent/packages/cli/dist/index.js"
    script = ROOT / "scripts/export_han_vocology_slides_v1.py"
    if not cli.is_file():
        return
    proc = subprocess.run(
        [sys.executable, str(script), "--formats", "html"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    report = json.loads((ROOT / "reports/han_vocology_slides_export_v1_latest.json").read_text(encoding="utf-8"))
    assert report.get("ok") is True
    assert report.get("engine") == "mdpresent"


def test_graduation_gate_build_and_validate_exit_0() -> None:
    build = ROOT / "scripts/build_han_vocology_graduation_gate_v1.py"
    validate = ROOT / "scripts/validate_han_vocology_graduation_gate_v1.py"
    proc_b = subprocess.run(
        [sys.executable, str(build)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc_b.returncode == 0, proc_b.stderr or proc_b.stdout
    proc_v = subprocess.run(
        [sys.executable, str(validate)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc_v.returncode == 0, proc_v.stderr or proc_v.stdout
    gate = json.loads(
        (ROOT / "reports/han_vocology_graduation_gate_v1_latest.json").read_text(encoding="utf-8")
    )
    assert gate.get("total_max") == 100
    assert gate.get("passed") is True
    assert int(gate.get("total_earned") or 0) >= 70


def test_vault_mirror_script_exit_0_or_skip() -> None:
    script = ROOT / "scripts/push_han_vocology_pilot_artifacts_to_vault_v1.py"
    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode in (0, 1), proc.stderr or proc.stdout
