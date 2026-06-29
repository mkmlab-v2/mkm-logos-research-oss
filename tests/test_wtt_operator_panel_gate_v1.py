"""WTT operator panel lane — build, validate, gate [HYPO]."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "scripts/build_wtt_operator_panel_sessions_v1.py"
VALIDATE = ROOT / "scripts/validate_wtt_pilot_jsonl_v1.py"
GATE = ROOT / "scripts/check_wtt_operator_panel_gate_v1.py"
HUMAN_GATE = ROOT / "scripts/run_wtt_human_gate_interactive_v1.py"


def test_build_operator_panel_corpus_has_30_rows(tmp_path: Path) -> None:
    out = tmp_path / "panel.jsonl"
    proc = subprocess.run(
        [sys.executable, str(BUILD), "--out", str(out), "--meta-out", str(tmp_path / "meta.json")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    lines = [ln for ln in out.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 30
    row = json.loads(lines[0])
    assert row["customer_provided"] is False
    assert "operator_panel" in row["labels"]


def test_validate_operator_panel_lane_strict(tmp_path: Path) -> None:
    out = tmp_path / "panel.jsonl"
    subprocess.run(
        [sys.executable, str(BUILD), "--out", str(out), "--meta-out", str(tmp_path / "meta.json")],
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
            "30",
            "--lane-operator-panel",
            "--strict",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_operator_panel_gate_end_to_end(tmp_path: Path) -> None:
    tenant = "test-operator-panel-v1"
    src = tmp_path / "source.jsonl"
    subprocess.run(
        [sys.executable, str(BUILD), "--out", str(src), "--meta-out", str(tmp_path / "meta.json")],
        cwd=str(ROOT),
        check=True,
    )
    intake = ROOT / f"data/wtt/intake/{tenant}.jsonl"
    prov = ROOT / f"data/wtt/provenance/{tenant}.provenance.json"
    intake.unlink(missing_ok=True)
    prov.unlink(missing_ok=True)

    consent = ROOT / "docs/final/artifacts/fixtures/internal_panel_consent_v1.example.txt"
    proc = subprocess.run(
        [
            sys.executable,
            str(HUMAN_GATE),
            "--tenant-id",
            tenant,
            "--source-jsonl",
            str(src),
            "--lane",
            "operator_panel",
            "--consent-source-ref",
            str(consent.relative_to(ROOT)).replace("\\", "/"),
            "--consent-type",
            "other",
            "--min-approve",
            "30",
            "--approve-all",
            "--public-facing-ok",
            "--out",
            str(tmp_path / "gate.json"),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout

    gate_proc = subprocess.run(
        [
            sys.executable,
            str(GATE),
            "--tenant-id",
            tenant,
            "--intake-jsonl",
            str(intake),
            "--provenance",
            str(prov),
            "--strict",
            "--out",
            str(tmp_path / "gate_report.json"),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert gate_proc.returncode == 0, gate_proc.stderr or gate_proc.stdout
    report = json.loads((tmp_path / "gate_report.json").read_text(encoding="utf-8"))
    assert report["operator_panel_n30_gate_met"] is True
    assert report["not_eligible_for_send"] is True

    intake.unlink(missing_ok=True)
    prov.unlink(missing_ok=True)


def test_scan_pii_warn_korean_name() -> None:
    sys.path.insert(0, str(ROOT / "scripts"))
    from validate_wtt_pilot_jsonl_v1 import scan_pii_warn_in_text  # noqa: E402

    hits = scan_pii_warn_in_text("담당자 이기륜 연결해 주세요")
    assert any(h.get("fragment") == "이기륜" for h in hits)
    masked = scan_pii_warn_in_text("케이스 이*민 종료")
    assert not any(h.get("fragment", "").startswith("이") for h in masked)
