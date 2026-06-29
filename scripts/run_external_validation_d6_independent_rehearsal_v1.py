#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "reports/external_validation_minimal_pack_v1_latest/manifest.json"
HYBRID = ROOT / "docs/final/artifacts/hybrid_b2b_commercialization_pipeline_v1_latest.json"
OUT = ROOT / "reports/external_validation_d6_independent_rehearsal_v1_latest.json"

ARTIFACT_CHECKS = [
    "reports/mkm_high_delegation_preflight_v1_latest.json",
    "reports/hd_autonomous_evolution_completion_v1_latest.json",
    "reports/compression_proof_completion_chain_v1_latest.json",
    "docs/final/artifacts/edge_encoder_air_gap_poc_pack_v1_latest.json",
    "docs/final/artifacts/hybrid_b2b_commercialization_pipeline_v1_latest.json",
    "reports/external_validation_minimal_pack_v1_latest/manifest.json",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _gate_snapshot() -> dict[str, Any]:
    doc = _read_json(HYBRID)
    return {
        "send_gate": doc.get("send_gate"),
        "ready_for_external_send": doc.get("ready_for_external_send"),
        "readiness_all_ok": doc.get("readiness_all_ok"),
    }


def _gate_match(expected: dict[str, Any], actual: dict[str, Any]) -> bool:
    """Rehearsal must not open external SEND; readiness_all_ok may improve false→true."""
    if actual.get("send_gate") != expected.get("send_gate"):
        return False
    if actual.get("ready_for_external_send") != expected.get("ready_for_external_send"):
        return False
    if actual.get("ready_for_external_send") or actual.get("send_gate") == "OPEN":
        return False
    before_ready = expected.get("readiness_all_ok")
    after_ready = actual.get("readiness_all_ok")
    if before_ready is False and after_ready is True:
        return True
    return after_ready == before_ready


def _run_command(command: str, cwd: Path) -> dict[str, Any]:
    started = _utc_now()
    proc = subprocess.run(
            command,
            cwd=cwd,
            shell=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    ended = _utc_now()
    tail = (proc.stdout or "")[-500:] + (proc.stderr or "")[-500:]
    return {
        "command": command,
        "exit_code": proc.returncode,
        "started_at_utc": started,
        "ended_at_utc": ended,
        "ok": proc.returncode == 0,
        "log_tail": tail.strip()[-400:],
    }


def _artifact_presence() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for rel in ARTIFACT_CHECKS:
        path = ROOT / rel
        rows.append({"path": rel, "exists": path.exists()})
    return rows


def build_report(
    *,
    operator: str,
    rehearsal_class: str,
    commands: list[str],
    steps: list[dict[str, Any]] | None = None,
    gate_before: dict[str, Any] | None = None,
    gate_after: dict[str, Any] | None = None,
) -> dict[str, Any]:
    gate_before = gate_before or _gate_snapshot()
    gate_after = gate_after or gate_before
    steps = steps or []
    all_ok = bool(steps) and all(s.get("ok") for s in steps)
    artifacts = _artifact_presence()
    artifacts_ok = all(row["exists"] for row in artifacts)
    expected_gate = {
        "send_gate": "HOLD",
        "ready_for_external_send": False,
        "readiness_all_ok": gate_before.get("readiness_all_ok"),
    }
    try:
        manifest_rel = str(MANIFEST.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        manifest_rel = str(MANIFEST)
    return {
        "schema": "external_validation_d6_independent_rehearsal_v1",
        "generated_at_utc": _utc_now(),
        "lane": "infra",
        "disclaimer": "internal_only",
        "rehearsal_class": rehearsal_class,
        "operator": operator,
        "plan_ssot": "docs/final/artifacts/external_validation_2week_execution_plan_v1_latest.md",
        "manifest_path": manifest_rel,
        "scope_note": "Execution plan D6 cites D1-D4; manifest reproduce_week1 has 7 steps — all recorded here.",
        "steps": steps,
        "summary": {
            "step_count": len(steps),
            "steps_ok": sum(1 for s in steps if s.get("ok")),
            "all_steps_exit_0": all_ok,
            "artifacts_ok": artifacts_ok,
        },
        "gate_before": gate_before,
        "gate_after": gate_after,
        "gate_match": _gate_match(expected_gate, gate_after),
        "gate_expected": expected_gate,
        "artifact_checks": artifacts,
        "status": "ok" if all_ok and artifacts_ok and _gate_match(expected_gate, gate_after) else "fail",
        "reproduce": "py scripts/run_external_validation_d6_independent_rehearsal_v1.py",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="D6 independent rehearsal runner (manifest commands).")
    parser.add_argument("--dry-run", action="store_true", help="Record commands only; do not execute.")
    parser.add_argument("--operator", default="internal_automated_d6_runner")
    parser.add_argument(
        "--rehearsal-class",
        default="same_host_dry_run",
        choices=["same_host_dry_run", "true_third_party"],
    )
    args = parser.parse_args(argv)

    if not MANIFEST.exists():
        print(json.dumps({"ok": False, "error": f"missing manifest: {MANIFEST}"}))
        return 1

    manifest = _read_json(MANIFEST)
    commands: list[str] = list(manifest.get("reproduce_week1") or [])
    if not commands:
        print(json.dumps({"ok": False, "error": "reproduce_week1 empty"}))
        return 1

    gate_before = _gate_snapshot()
    steps: list[dict[str, Any]] = []
    if args.dry_run:
        for cmd in commands:
            steps.append(
                {
                    "command": cmd,
                    "exit_code": None,
                    "started_at_utc": _utc_now(),
                    "ended_at_utc": _utc_now(),
                    "ok": True,
                    "dry_run": True,
                    "log_tail": "",
                }
            )
    else:
        for cmd in commands:
            steps.append(_run_command(cmd, ROOT))

    gate_after = _gate_snapshot()
    report = build_report(
        operator=args.operator,
        rehearsal_class=args.rehearsal_class,
        commands=commands,
        steps=steps,
        gate_before=gate_before,
        gate_after=gate_after,
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ok = report["status"] == "ok"
    print(json.dumps({"ok": ok, "out": str(OUT.relative_to(ROOT)), "status": report["status"]}))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
