from __future__ import annotations

import json
import subprocess
from pathlib import Path


def test_check_canon_singularity_rehearsal_status_ps1_as_json():
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "check_canon_singularity_rehearsal_status.ps1"
    cmd = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script),
        "-AsJson",
    ]
    cp = subprocess.run(cmd, check=False, cwd=root, capture_output=True, text=True)
    assert cp.returncode == 0
    data = json.loads(cp.stdout)
    assert "task" in data
    assert "promotion_gate" in data
    assert "delta_cutoff_autotune" in data
    assert "delta_governance_gate" in data
    assert "delta_autotune_history_latest" in data
    assert "drift_gate" in data
    assert "freeze_v2_stability_gate" in data
    assert "promotion_go_no_go" in data
    assert "ops_alert_summary" in data
    assert "recommended_action" in data
    assert "strict_auto_run" in data


def test_check_canon_singularity_rehearsal_status_ps1_writes_artifacts(tmp_path: Path):
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "check_canon_singularity_rehearsal_status.ps1"
    out = tmp_path / "latest.json"
    hist = tmp_path / "history.jsonl"
    cmd = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script),
        "-OutputJson",
        str(out),
        "-HistoryJsonl",
        str(hist),
        "-AppendHistory",
    ]
    cp = subprocess.run(cmd, check=False, cwd=root, capture_output=True, text=True)
    assert cp.returncode == 0
    assert out.exists()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert "generated_at_utc" in data
    assert hist.exists()
    lines = [x for x in hist.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(lines) >= 1


def test_check_canon_singularity_rehearsal_status_ps1_alert_severity_high(tmp_path: Path):
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "check_canon_singularity_rehearsal_status.ps1"
    ws = tmp_path / "ws"
    artifacts = ws / "docs" / "final" / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    (artifacts / "original_corpus_regime_singularity_canon_strict_freeze_drift_gate_v1.json").write_text(
        json.dumps({"status": "alert", "metrics": {"drift_count": 2}, "generated_at_utc": "2026-04-23T00:00:00Z"}),
        encoding="utf-8",
    )
    hist = tmp_path / "hist.jsonl"
    hist.write_text(
        json.dumps(
            {
                "drift_gate": {"status": "alert"},
                "ops_alert_summary": {"ops_alert": True},
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    out = tmp_path / "latest.json"
    cmd = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script),
        "-WorkspaceRoot",
        str(ws),
        "-OutputJson",
        str(out),
        "-HistoryJsonl",
        str(hist),
    ]
    cp = subprocess.run(cmd, check=False, cwd=root, capture_output=True, text=True)
    assert cp.returncode == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["drift_gate"]["status"] == "alert"
    assert data["ops_alert_summary"]["ops_alert"] is True
    assert data["ops_alert_summary"]["severity"] == "high"
    assert data["recommended_action"]["kind"] == "run_strict_rehearsal"
    assert "run_canon_singularity_strict_rehearsal_v1.ps1" in data["recommended_action"]["command"]


def test_check_canon_singularity_rehearsal_status_ps1_auto_run_strict_on_alert(tmp_path: Path):
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "check_canon_singularity_rehearsal_status.ps1"
    ws = tmp_path / "ws"
    artifacts = ws / "docs" / "final" / "artifacts"
    scripts_dir = ws / "scripts"
    artifacts.mkdir(parents=True, exist_ok=True)
    scripts_dir.mkdir(parents=True, exist_ok=True)

    # Create alert drift artifact
    (artifacts / "original_corpus_regime_singularity_canon_strict_freeze_drift_gate_v1.json").write_text(
        json.dumps({"status": "alert", "metrics": {"drift_count": 1}, "generated_at_utc": "2026-04-23T00:00:00Z"}),
        encoding="utf-8",
    )
    # Stub strict rehearsal script
    (scripts_dir / "run_canon_singularity_strict_rehearsal_v1.ps1").write_text(
        "param([switch]$SkipVaultSync)\nexit 0\n",
        encoding="utf-8",
    )

    out = tmp_path / "latest.json"
    cmd = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script),
        "-WorkspaceRoot",
        str(ws),
        "-OutputJson",
        str(out),
        "-AutoRunStrictOnAlert",
    ]
    cp = subprocess.run(cmd, check=False, cwd=root, capture_output=True, text=True)
    assert cp.returncode == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["strict_auto_run"]["enabled"] is True
    assert data["strict_auto_run"]["triggered"] is True
    assert data["strict_auto_run"]["status"] == "pass"


def test_check_canon_singularity_rehearsal_status_ps1_alert_on_freeze_stability_fail(tmp_path: Path):
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "check_canon_singularity_rehearsal_status.ps1"
    ws = tmp_path / "ws"
    artifacts = ws / "docs" / "final" / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    (artifacts / "original_corpus_regime_singularity_canon_strict_freeze_drift_gate_v1.json").write_text(
        json.dumps({"status": "stable", "metrics": {"drift_count": 0}, "generated_at_utc": "2026-04-23T00:00:00Z"}),
        encoding="utf-8",
    )
    (artifacts / "original_corpus_regime_singularity_canon_strict_baseline_freeze_v2_stability_gate_v1.json").write_text(
        json.dumps({"status": "fail", "metrics": {"window_size": 4, "frozen_rate": 0.5}, "generated_at_utc": "2026-04-23T00:00:00Z"}),
        encoding="utf-8",
    )
    out = tmp_path / "latest.json"
    cmd = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script),
        "-WorkspaceRoot",
        str(ws),
        "-OutputJson",
        str(out),
    ]
    cp = subprocess.run(cmd, check=False, cwd=root, capture_output=True, text=True)
    assert cp.returncode == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["drift_gate"]["status"] == "stable"
    assert data["freeze_v2_stability_gate"]["status"] == "fail"
    assert data["ops_alert_summary"]["ops_alert"] is True
    assert data["recommended_action"]["kind"] == "run_strict_rehearsal"
    assert data["recommended_action"]["reason"] == "freeze_v2_stability_fail"


def test_check_canon_singularity_rehearsal_status_ps1_alert_on_go_no_go_no_go(tmp_path: Path):
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "check_canon_singularity_rehearsal_status.ps1"
    ws = tmp_path / "ws"
    artifacts = ws / "docs" / "final" / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    (artifacts / "original_corpus_regime_singularity_canon_strict_freeze_drift_gate_v1.json").write_text(
        json.dumps({"status": "stable", "metrics": {"drift_count": 0}, "generated_at_utc": "2026-04-23T00:00:00Z"}),
        encoding="utf-8",
    )
    (artifacts / "original_corpus_regime_singularity_canon_strict_baseline_freeze_v2_stability_gate_v1.json").write_text(
        json.dumps({"status": "pass", "metrics": {"window_size": 7, "frozen_rate": 1.0}, "generated_at_utc": "2026-04-23T00:00:00Z"}),
        encoding="utf-8",
    )
    (artifacts / "original_corpus_regime_singularity_canon_promotion_go_no_go_v1.json").write_text(
        json.dumps({"verdict": "no_go", "hold_reasons": ["promotion_gate_ok"], "generated_at_utc": "2026-04-23T00:00:00Z"}),
        encoding="utf-8",
    )
    out = tmp_path / "latest.json"
    cmd = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script),
        "-WorkspaceRoot",
        str(ws),
        "-OutputJson",
        str(out),
    ]
    cp = subprocess.run(cmd, check=False, cwd=root, capture_output=True, text=True)
    assert cp.returncode == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["promotion_go_no_go"]["verdict"] == "no_go"
    assert data["ops_alert_summary"]["ops_alert"] is True
    assert data["recommended_action"]["reason"] == "promotion_go_no_go_no_go"

