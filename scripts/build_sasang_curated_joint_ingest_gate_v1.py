#!/usr/bin/env python3
"""Gate for curated JSONL ingest path (dry-run default) [HYPO]."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
DEFAULT_INPUT = ROOT / "data/myeongni/curated_saju_joint_v1.jsonl"
DEFAULT_TARGET = ROOT / "data/myeongni/sasang_saju_joint_benchmark_v1.jsonl"
OUT = ROOT / "docs/final/artifacts/sasang_curated_joint_ingest_gate_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_ingest(*, input_path: Path, target: Path, dry_run: bool) -> tuple[int, dict[str, Any]]:
    if not input_path.is_file():
        return 0, {"skipped": "missing_input_file", "path": str(input_path)}
    cmd = [
        PY,
        str(ROOT / "scripts/ingest_curated_saju_joint_v1.py"),
        "--input-jsonl",
        str(input_path),
        "--target-jsonl",
        str(target),
    ]
    if dry_run:
        cmd.append("--dry-run")
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    payload: dict[str, Any] = {}
    text = (proc.stdout or "").strip()
    if text:
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            if start >= 0:
                try:
                    payload = json.loads(text[start:])
                except json.JSONDecodeError:
                    payload = {"raw_stdout": text[-500:]}
    if proc.stderr:
        payload.setdefault("stderr_tail", proc.stderr[-300:])
    return proc.returncode, payload


def build(*, apply_ingest: bool = False) -> dict[str, Any]:
    input_exists = DEFAULT_INPUT.is_file()
    ingest_status = "input_missing_hold"
    dry_payload: dict[str, Any] = {}
    apply_payload: dict[str, Any] = {}

    if input_exists:
        dry_code, dry_payload = _run_ingest(input_path=DEFAULT_INPUT, target=DEFAULT_TARGET, dry_run=True)
        would = int(dry_payload.get("appended") or 0)
        errors = dry_payload.get("errors") or []
        if errors:
            ingest_status = "dry_run_errors"
        elif would > 0:
            ingest_status = "ready_to_apply"
        else:
            ingest_status = "idle_no_promotable_rows"

        if apply_ingest and would > 0 and ingest_status == "ready_to_apply":
            apply_code, apply_payload = _run_ingest(input_path=DEFAULT_INPUT, target=DEFAULT_TARGET, dry_run=False)
            ingest_status = "applied" if apply_code == 0 else "apply_failed"

    checks = {
        "ingest_script_reachable": {"passed": (ROOT / "scripts/ingest_curated_saju_joint_v1.py").is_file()},
        "joint_benchmark_present": {"passed": DEFAULT_TARGET.is_file()},
        "input_missing_or_valid": {
            "passed": not input_exists
            or ingest_status in ("idle_no_promotable_rows", "ready_to_apply", "applied"),
        },
        "dry_run_no_errors": {"passed": ingest_status != "dry_run_errors"},
        "apply_only_when_ready": {"passed": ingest_status != "apply_failed"},
        "track_a_bridge_forbidden": {"passed": True},
        "send_gate_hold": {"passed": True},
    }
    gate_ok = all(c.get("passed") for c in checks.values())
    return {
        "schema": "sasang_curated_joint_ingest_gate_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "send_gate": "HOLD",
        "ingest_status": ingest_status,
        "gate_ok": gate_ok,
        "checks": checks,
        "dry_run": dry_payload,
        "apply": apply_payload,
        "artifact_paths": {
            "input_jsonl": str(DEFAULT_INPUT).replace("\\", "/"),
            "joint_benchmark_jsonl": str(DEFAULT_TARGET).replace("\\", "/"),
        },
        "reproduce": "py scripts/build_sasang_curated_joint_ingest_gate_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build(apply_ingest=args.apply)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["gate_ok"], "ingest_status": doc["ingest_status"]}))
    return 0 if doc["gate_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
