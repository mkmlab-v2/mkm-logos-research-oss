from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def test_parse_external_baseline_range_and_manual_source_type(tmp_path: Path) -> None:
    artifacts = tmp_path / "docs" / "final" / "artifacts"
    external = artifacts / "external_seed.jsonl"
    internal = artifacts / "internal_edges.jsonl"
    report = artifacts / "report.json"
    norm = artifacts / "norm.jsonl"

    _write_jsonl(
        external,
        [
            {"source_ref": "Gen.1.1", "target_ref": "Ps.8.3"},
            {"source_ref": "Isa.7.14", "target_ref": "Matt.1.23"},
        ],
    )
    _write_jsonl(
        internal,
        [
            {"source": "Gen.1::Gen.1.1-Gen.1.3", "target": "Ps.8::Ps.8.3-Ps.8.5", "similarity": 0.9},
            {"source": "Isa.7::Isa.7.14-Isa.7.16", "target": "Matt.1::Matt.1.23-Matt.1.25", "similarity": 0.8},
        ],
    )

    subprocess.run(
        [
            "py",
            str(ROOT / "scripts" / "parse_external_baseline_v1.py"),
            "--external-input",
            str(external),
            "--internal-edges-jsonl",
            str(internal),
            "--range-mode",
            "start",
            "--normalized-out-jsonl",
            str(norm),
            "--report-out-json",
            str(report),
        ],
        cwd=str(ROOT),
        check=True,
    )

    doc = json.loads(report.read_text(encoding="utf-8"))
    assert doc["inputs"]["external_source_type"] == "manual_editorial"
    assert doc["baseline_classification"] == "manual_editorial_heuristic"
    assert doc["counts"]["overlap_pair_count"] >= 2

    first = json.loads(norm.read_text(encoding="utf-8").splitlines()[0])
    assert first["source_type"] == "manual_editorial"


def test_dual_mode_report_contains_threshold_and_exploration_fields(tmp_path: Path) -> None:
    artifacts = tmp_path / "docs" / "final" / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    start_sweep = artifacts / "start.json"
    expand_sweep = artifacts / "expand.json"
    thresholds = artifacts / "thresholds.json"
    dual_report = artifacts / "dual_report.json"

    start_sweep.write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "top_k": 100,
                        "coverage_overlap": 0.0003,
                        "precision_at_k": 0.02,
                        "delta_random_baseline": 0.003,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    expand_sweep.write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "top_k": 100,
                        "coverage_overlap": 0.0001,
                        "precision_at_k": 0.03,
                        "delta_random_baseline": 0.01,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    thresholds.write_text(
        json.dumps(
            {
                "thresholds": {
                    "coverage_overlap_min_watch": 0.000257,
                    "coverage_overlap_min_promising": 0.004849,
                    "delta_random_baseline_min_watch": 0.0,
                    "delta_random_baseline_min_promising": 0.00017,
                    "precision_at_k_min_watch": 0.001,
                }
            }
        ),
        encoding="utf-8",
    )

    subprocess.run(
        [
            "py",
            str(ROOT / "scripts" / "build_external_baseline_dual_mode_report_v1.py"),
            "--start-sweep-json",
            str(start_sweep),
            "--expand-sweep-json",
            str(expand_sweep),
            "--thresholds-json",
            str(thresholds),
            "--output-json",
            str(dual_report),
        ],
        cwd=str(ROOT),
        check=True,
    )

    doc = json.loads(dual_report.read_text(encoding="utf-8"))
    op = doc["operating_mode"]["best_row_by_delta_then_precision"]
    ex = doc["exploratory_mode"]["best_row_by_delta_then_precision"]
    assert op["threshold_label"] in {"below_watch", "watch", "promising"}
    assert ex["threshold_label"] in {"below_watch", "watch", "promising"}
    assert ex["exploration_signal"] in {"none", "weak_delta", "strong_delta"}


def test_threshold_recalibration_hint_activates_on_monitor_streak(tmp_path: Path) -> None:
    artifacts = tmp_path / "docs" / "final" / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    brief = artifacts / "brief.json"
    history = artifacts / "history.json"
    hint = artifacts / "hint.json"

    brief.write_text(json.dumps({"recommended_next_action": "monitor_only"}), encoding="utf-8")

    subprocess.run(
        [
            "py",
            str(ROOT / "scripts" / "build_external_baseline_threshold_recalibration_hint_v1.py"),
            "--exploration-brief-json",
            str(brief),
            "--history-json",
            str(history),
            "--streak-trigger",
            "2",
            "--output-json",
            str(hint),
        ],
        cwd=str(ROOT),
        check=True,
    )
    subprocess.run(
        [
            "py",
            str(ROOT / "scripts" / "build_external_baseline_threshold_recalibration_hint_v1.py"),
            "--exploration-brief-json",
            str(brief),
            "--history-json",
            str(history),
            "--streak-trigger",
            "2",
            "--output-json",
            str(hint),
        ],
        cwd=str(ROOT),
        check=True,
    )

    h = json.loads(hint.read_text(encoding="utf-8"))
    assert h["monitor_only_streak"] >= 2
    assert h["hint_active"] is True
    assert h["recommended_action"] == "propose_threshold_recalibration"


def test_threshold_apply_gate_requires_resolution_and_approval(tmp_path: Path) -> None:
    artifacts = tmp_path / "docs" / "final" / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    hint = artifacts / "hint.json"
    resolution = artifacts / "resolution.json"
    approval = artifacts / "approval.json"
    proposal = artifacts / "proposal.json"
    gate = artifacts / "gate.json"

    hint.write_text(json.dumps({"hint_active": True}), encoding="utf-8")
    resolution.write_text(json.dumps({"resolution_state": "completed"}), encoding="utf-8")
    proposal.write_text(json.dumps({"proposed_thresholds": {"coverage_overlap_min_watch": 0.1}}), encoding="utf-8")

    subprocess.run(
        [
            "py",
            str(ROOT / "scripts" / "build_external_baseline_threshold_apply_gate_v1.py"),
            "--hint-json",
            str(hint),
            "--resolution-json",
            str(resolution),
            "--approval-json",
            str(approval),
            "--proposal-json",
            str(proposal),
            "--output-json",
            str(gate),
        ],
        cwd=str(ROOT),
        check=True,
    )
    g = json.loads(gate.read_text(encoding="utf-8"))
    assert g["can_apply_thresholds"] is False

    approval.write_text(
        json.dumps(
            {
                "approved": True,
                "approved_by": "tester",
                "approved_reason": "unit-test",
                "expires_at_utc": "2099-01-01T00:00:00Z",
            }
        ),
        encoding="utf-8",
    )
    subprocess.run(
        [
            "py",
            str(ROOT / "scripts" / "build_external_baseline_threshold_apply_gate_v1.py"),
            "--hint-json",
            str(hint),
            "--resolution-json",
            str(resolution),
            "--approval-json",
            str(approval),
            "--proposal-json",
            str(proposal),
            "--output-json",
            str(gate),
        ],
        cwd=str(ROOT),
        check=True,
    )
    g2 = json.loads(gate.read_text(encoding="utf-8"))
    assert g2["can_apply_thresholds"] is True

    approval.write_text(
        json.dumps(
            {
                "approved": True,
                "approved_by": "tester",
                "approved_reason": "expired-case",
                "expires_at_utc": "2000-01-01T00:00:00Z",
            }
        ),
        encoding="utf-8",
    )
    subprocess.run(
        [
            "py",
            str(ROOT / "scripts" / "build_external_baseline_threshold_apply_gate_v1.py"),
            "--hint-json",
            str(hint),
            "--resolution-json",
            str(resolution),
            "--approval-json",
            str(approval),
            "--proposal-json",
            str(proposal),
            "--output-json",
            str(gate),
        ],
        cwd=str(ROOT),
        check=True,
    )
    g3 = json.loads(gate.read_text(encoding="utf-8"))
    assert g3["checks"]["approval_not_expired"] is False
    assert g3["can_apply_thresholds"] is False


def test_apply_thresholds_resets_approval_and_writes_log(tmp_path: Path) -> None:
    artifacts = tmp_path / "docs" / "final" / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    proposal = artifacts / "proposal.json"
    thresholds = artifacts / "thresholds.json"
    approval = artifacts / "approval.json"
    apply_log = artifacts / "apply_log.jsonl"

    proposal.write_text(json.dumps({"proposed_thresholds": {"coverage_overlap_min_watch": 0.123}}), encoding="utf-8")
    thresholds.write_text(json.dumps({"thresholds": {"coverage_overlap_min_watch": 0.001}}), encoding="utf-8")
    approval.write_text(
        json.dumps(
            {
                "approved": True,
                "approved_by": "tester",
                "approved_reason": "unit-test-apply",
                "expires_at_utc": "2099-01-01T00:00:00Z",
            }
        ),
        encoding="utf-8",
    )

    subprocess.run(
        [
            "py",
            str(ROOT / "scripts" / "apply_external_baseline_thresholds_from_proposal_v1.py"),
            "--proposal-json",
            str(proposal),
            "--thresholds-json",
            str(thresholds),
            "--approval-json",
            str(approval),
            "--apply-log-jsonl",
            str(apply_log),
        ],
        cwd=str(ROOT),
        check=True,
    )

    t = json.loads(thresholds.read_text(encoding="utf-8"))
    a = json.loads(approval.read_text(encoding="utf-8"))
    log_lines = apply_log.read_text(encoding="utf-8").splitlines()
    assert t["thresholds"]["coverage_overlap_min_watch"] == 0.123
    assert a["approved"] is False
    assert len(log_lines) == 1


def test_one_shot_approval_consumption_reblocks_gate(tmp_path: Path) -> None:
    artifacts = tmp_path / "docs" / "final" / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    hint = artifacts / "hint.json"
    resolution = artifacts / "resolution.json"
    approval = artifacts / "approval.json"
    proposal = artifacts / "proposal.json"
    thresholds = artifacts / "thresholds.json"
    apply_log = artifacts / "apply_log.jsonl"
    gate = artifacts / "gate.json"

    hint.write_text(json.dumps({"hint_active": True}), encoding="utf-8")
    resolution.write_text(json.dumps({"resolution_state": "completed"}), encoding="utf-8")
    proposal.write_text(json.dumps({"proposed_thresholds": {"coverage_overlap_min_watch": 0.2}}), encoding="utf-8")
    thresholds.write_text(json.dumps({"thresholds": {"coverage_overlap_min_watch": 0.01}}), encoding="utf-8")
    approval.write_text(
        json.dumps(
            {
                "approved": True,
                "approved_by": "tester",
                "approved_reason": "one-shot",
                "expires_at_utc": "2099-01-01T00:00:00Z",
            }
        ),
        encoding="utf-8",
    )

    subprocess.run(
        [
            "py",
            str(ROOT / "scripts" / "build_external_baseline_threshold_apply_gate_v1.py"),
            "--hint-json",
            str(hint),
            "--resolution-json",
            str(resolution),
            "--approval-json",
            str(approval),
            "--proposal-json",
            str(proposal),
            "--output-json",
            str(gate),
        ],
        cwd=str(ROOT),
        check=True,
    )
    before = json.loads(gate.read_text(encoding="utf-8"))
    assert before["can_apply_thresholds"] is True

    subprocess.run(
        [
            "py",
            str(ROOT / "scripts" / "apply_external_baseline_thresholds_from_proposal_v1.py"),
            "--proposal-json",
            str(proposal),
            "--thresholds-json",
            str(thresholds),
            "--approval-json",
            str(approval),
            "--apply-log-jsonl",
            str(apply_log),
        ],
        cwd=str(ROOT),
        check=True,
    )
    subprocess.run(
        [
            "py",
            str(ROOT / "scripts" / "build_external_baseline_threshold_apply_gate_v1.py"),
            "--hint-json",
            str(hint),
            "--resolution-json",
            str(resolution),
            "--approval-json",
            str(approval),
            "--proposal-json",
            str(proposal),
            "--output-json",
            str(gate),
        ],
        cwd=str(ROOT),
        check=True,
    )
    after = json.loads(gate.read_text(encoding="utf-8"))
    assert after["checks"]["approval_granted"] is False
    assert after["can_apply_thresholds"] is False
