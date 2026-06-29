#!/usr/bin/env python3
"""Attested-only snapshot classification gate [HYPO]."""

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
SNAPSHOT = ROOT / "data/myeongni/sasang_saju_joint_benchmark_attested_only_v1.jsonl"
SMOKE = ROOT / "reports/sasang_joint_benchmark_attested_only_classification_smoke_v1_latest.json"
OUT = ROOT / "docs/final/artifacts/sasang_attested_only_classification_gate_v1_latest.json"
MIN_EVALUATED = 5


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build(*, run_smoke: bool) -> dict[str, Any]:
    if run_smoke:
        proc = subprocess.run(
            [
                PY,
                str(ROOT / "scripts/build_sasang_joint_benchmark_non_dummy_classification_smoke_v1.py"),
                "--dataset",
                str(SNAPSHOT),
                "--out",
                str(SMOKE),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            return {"gate_ok": False, "classification_status": "smoke_failed"}

    smoke = _load(SMOKE)
    evaluated = int(smoke.get("rows_with_birth_evaluated") or 0)
    passed = int(smoke.get("passed") or 0)
    classification_ok = smoke.get("classification_ok") is True
    gate_ok = classification_ok and evaluated >= MIN_EVALUATED
    return {
        "schema": "sasang_attested_only_classification_gate_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "classification_status": "eval_ok" if gate_ok else "incomplete",
        "gate_ok": gate_ok,
        "rows_evaluated": evaluated,
        "rows_passed": passed,
        "smoke_ref": str(SMOKE).replace("\\", "/"),
        "snapshot_ref": str(SNAPSHOT).replace("\\", "/"),
        "reproduce": "py scripts/build_sasang_attested_only_classification_gate_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-smoke-run", action="store_true")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build(run_smoke=not args.skip_smoke_run)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc.get("gate_ok"), "classification_status": doc.get("classification_status")}))
    return 0 if doc.get("gate_ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
