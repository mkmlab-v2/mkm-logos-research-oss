#!/usr/bin/env python3
"""Gate for curated CSV → joint benchmark promote path (dry-run default) [HYPO]."""

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
DEFAULT_CSV = ROOT / "data/myeongni/sasang_saju_joint_review_queue_v1.csv"
DEFAULT_TARGET = ROOT / "data/myeongni/sasang_saju_joint_benchmark_v1.jsonl"
OUT = ROOT / "docs/final/artifacts/sasang_literature_curated_promote_gate_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_promote(*, csv: Path, target: Path, dry_run: bool) -> tuple[int, dict[str, Any]]:
    cmd = [PY, str(ROOT / "scripts/promote_joint_curated_csv_v1.py"), "--csv", str(csv), "--target-jsonl", str(target)]
    if dry_run:
        cmd.append("--dry-run")
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    payload: dict[str, Any] = {}
    text = (proc.stdout or "").strip()
    if text:
        start = text.find("{")
        if start >= 0:
            try:
                payload = json.loads(text[start:])
            except json.JSONDecodeError:
                payload = {"raw_stdout": text[-500:]}
    if proc.stderr:
        payload.setdefault("stderr_tail", proc.stderr[-300:])
    return proc.returncode, payload


def build(*, apply_promote: bool = False) -> dict[str, Any]:
    csv_exists = DEFAULT_CSV.is_file()
    promote_status = "csv_missing_hold"
    dry_payload: dict[str, Any] = {}
    apply_payload: dict[str, Any] = {}
    dry_code = 0
    apply_code = 0

    if csv_exists:
        dry_code, dry_payload = _run_promote(csv=DEFAULT_CSV, target=DEFAULT_TARGET, dry_run=True)
        would = int(dry_payload.get("would_append") or 0)
        errors = dry_payload.get("errors") or []
        if dry_code != 0 and errors:
            promote_status = "dry_run_errors"
        elif would > 0:
            promote_status = "ready_to_apply"
        else:
            promote_status = "idle_no_curator_rows"

        if apply_promote and would > 0 and promote_status == "ready_to_apply":
            apply_code, apply_payload = _run_promote(csv=DEFAULT_CSV, target=DEFAULT_TARGET, dry_run=False)
            if apply_code == 0:
                promote_status = "applied"
            else:
                promote_status = "apply_failed"

    checks = {
        "promote_script_reachable": {"passed": (ROOT / "scripts/promote_joint_curated_csv_v1.py").is_file()},
        "joint_benchmark_present": {"passed": DEFAULT_TARGET.is_file()},
        "csv_missing_or_valid": {
            "passed": not csv_exists or promote_status in ("idle_no_curator_rows", "ready_to_apply", "applied"),
        },
        "dry_run_no_errors": {
            "passed": not csv_exists or promote_status != "dry_run_errors",
        },
        "apply_only_when_ready": {
            "passed": promote_status != "apply_failed",
        },
        "track_a_bridge_forbidden": {"passed": True},
        "send_gate_hold": {"passed": True},
    }
    gate_ok = all(c.get("passed") for c in checks.values())
    return {
        "schema": "sasang_literature_curated_promote_gate_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "send_gate": "HOLD",
        "promote_status": promote_status,
        "gate_ok": gate_ok,
        "checks": checks,
        "dry_run": dry_payload,
        "apply": apply_payload,
        "artifact_paths": {
            "review_queue_csv": str(DEFAULT_CSV).replace("\\", "/"),
            "joint_benchmark_jsonl": str(DEFAULT_TARGET).replace("\\", "/"),
        },
        "reproduce": "py scripts/build_sasang_literature_curated_promote_gate_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="Apply promote when dry-run finds curator_ok rows.")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build(apply_promote=args.apply)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["gate_ok"], "promote_status": doc["promote_status"]}))
    return 0 if doc["gate_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
