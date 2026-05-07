from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_logos_shadow_alert_decision_v1.py"


def _write_gate(path: Path, decision: str) -> None:
    path.write_text(
        json.dumps(
            {
                "schema": "logos_shadow_weekly_gate_v1",
                "decision": decision,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def test_alert_turns_true_on_strict_bootstrap_mismatch(tmp_path: Path) -> None:
    strict_gate = tmp_path / "strict.json"
    bootstrap_gate = tmp_path / "bootstrap.json"
    out = tmp_path / "alert.json"
    _write_gate(strict_gate, "GO")
    _write_gate(bootstrap_gate, "WATCH")

    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--strict-gate-json",
            str(strict_gate),
            "--bootstrap-gate-json",
            str(bootstrap_gate),
            "--output-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    assert out.is_file()

    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "logos_shadow_alert_decision_v1"
    assert (doc.get("checks") or {}).get("strict_bootstrap_mismatch") is True
    assert (doc.get("checks") or {}).get("strict_hold") is False
    assert (doc.get("alert") or {}).get("should_alert") is True
    assert (doc.get("alert") or {}).get("reason") == "strict_bootstrap_mismatch"


def test_alert_stays_false_when_both_go(tmp_path: Path) -> None:
    strict_gate = tmp_path / "strict.json"
    bootstrap_gate = tmp_path / "bootstrap.json"
    out = tmp_path / "alert.json"
    _write_gate(strict_gate, "GO")
    _write_gate(bootstrap_gate, "GO")

    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--strict-gate-json",
            str(strict_gate),
            "--bootstrap-gate-json",
            str(bootstrap_gate),
            "--output-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    assert out.is_file()

    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "logos_shadow_alert_decision_v1"
    assert (doc.get("checks") or {}).get("strict_bootstrap_mismatch") is False
    assert (doc.get("checks") or {}).get("strict_hold") is False
    assert (doc.get("alert") or {}).get("should_alert") is False
    assert (doc.get("alert") or {}).get("reason") == "no_alert_rule_match"

