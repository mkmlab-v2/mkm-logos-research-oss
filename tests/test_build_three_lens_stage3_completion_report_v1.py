from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_three_lens_stage3_completion_report_v1.py"


def _row(action: str, *, logos_ok: bool = True, armed: bool = False, enabled: bool = True) -> dict:
    return {
        "ts_utc": "2026-05-08T00:00:00Z",
        "action": action,
        "enabled_evidence_all_present": True,
        "logos_non_gating_ok": logos_ok,
        "conditional_go_enabled": enabled,
        "conditional_go_armed": armed,
    }


def test_build_three_lens_stage3_completion_report_pass(tmp_path: Path) -> None:
    history = tmp_path / "history.jsonl"
    gate = tmp_path / "gate.json"
    promo = tmp_path / "promo.json"
    out = tmp_path / "report.json"

    rows = [_row("WATCH", armed=True), _row("GO", armed=True), _row("WATCH", armed=False), _row("GO", armed=True),
            _row("WATCH", armed=False), _row("GO", armed=True), _row("WATCH", armed=False)]
    history.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    gate.write_text(
        json.dumps({"decision": {"action": "WATCH", "reason": "default_watch_band"}, "metrics": {"conditional_go_armed": True, "logos_non_gating_ok": True}}, ensure_ascii=False),
        encoding="utf-8",
    )
    promo.write_text(json.dumps({"decision": "PROMOTED", "required_runs": 7}, ensure_ascii=False), encoding="utf-8")

    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--history-jsonl",
            str(history),
            "--gate-json",
            str(gate),
            "--promotion-json",
            str(promo),
            "--required-runs",
            "7",
            "--output-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "three_lens_stage3_completion_report_v1"
    assert doc["stage3_gate"]["status"] == "PASS"


def test_build_three_lens_stage3_completion_report_fail_on_violation(tmp_path: Path) -> None:
    history = tmp_path / "history.jsonl"
    gate = tmp_path / "gate.json"
    promo = tmp_path / "promo.json"
    out = tmp_path / "report.json"

    rows = [_row("WATCH", logos_ok=False, armed=False) for _ in range(7)]
    history.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    gate.write_text(
        json.dumps({"decision": {"action": "HOLD", "reason": "logos_non_gating_violation"}, "metrics": {"conditional_go_armed": False, "logos_non_gating_ok": False}}, ensure_ascii=False),
        encoding="utf-8",
    )
    promo.write_text(json.dumps({"decision": "HOLD"}, ensure_ascii=False), encoding="utf-8")

    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--history-jsonl",
            str(history),
            "--gate-json",
            str(gate),
            "--promotion-json",
            str(promo),
            "--required-runs",
            "7",
            "--output-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["stage3_gate"]["status"] == "FAIL"
    assert doc["tail_window"]["logos_non_gating_violation_count"] == 7


def test_build_three_lens_stage3_completion_report_unknown_fields_do_not_fail(tmp_path: Path) -> None:
    history = tmp_path / "history.jsonl"
    gate = tmp_path / "gate.json"
    promo = tmp_path / "promo.json"
    out = tmp_path / "report.json"

    rows = [{"ts_utc": "2026-05-08T00:00:00Z", "action": "WATCH", "enabled_evidence_all_present": True} for _ in range(7)]
    history.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    gate.write_text(
        json.dumps({"decision": {"action": "WATCH", "reason": "default_watch_band"}, "metrics": {"logos_non_gating_ok": True}}, ensure_ascii=False),
        encoding="utf-8",
    )
    promo.write_text(json.dumps({"decision": "PROMOTED", "required_runs": 7}, ensure_ascii=False), encoding="utf-8")

    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--history-jsonl",
            str(history),
            "--gate-json",
            str(gate),
            "--promotion-json",
            str(promo),
            "--required-runs",
            "7",
            "--output-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["tail_window"]["logos_non_gating_field_known_count"] == 0
    assert doc["tail_window"]["conditional_go_enabled_count"] == 0
    assert doc["stage3_gate"]["checks"]["logos_non_gating_violation_count_eq_0_or_no_known_samples"] is True
    assert doc["stage3_gate"]["checks"]["conditional_go_armed_rate_gte_0_20_or_no_enabled_samples"] is True
