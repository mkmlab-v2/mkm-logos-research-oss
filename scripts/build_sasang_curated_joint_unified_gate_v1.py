#!/usr/bin/env python3
"""Unified gate: CSV promote + JSONL ingest curated joint paths [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CSV_GATE = ROOT / "docs/final/artifacts/sasang_literature_curated_promote_gate_v1_latest.json"
INGEST_GATE = ROOT / "docs/final/artifacts/sasang_curated_joint_ingest_gate_v1_latest.json"
OUT = ROOT / "docs/final/artifacts/sasang_curated_joint_unified_gate_v1_latest.json"

_HOLD_STATUSES = frozenset(
    {
        "csv_missing_hold",
        "idle_no_curator_rows",
        "input_missing_hold",
        "idle_no_promotable_rows",
    }
)
_READY_STATUSES = frozenset({"ready_to_apply", "applied"})


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _combined_status(csv_status: str, ingest_status: str) -> str:
    if csv_status == "applied" or ingest_status == "applied":
        return "applied_partial_or_full"
    if csv_status in _READY_STATUSES and ingest_status in _READY_STATUSES:
        return "dual_ready_to_apply"
    if csv_status in _READY_STATUSES:
        return "csv_ready_to_apply"
    if ingest_status in _READY_STATUSES:
        return "jsonl_ready_to_apply"
    if csv_status in _HOLD_STATUSES and ingest_status in _HOLD_STATUSES:
        return "dual_idle_hold"
    return "mixed_review"


def build() -> dict[str, Any]:
    csv_g = _load(CSV_GATE)
    ingest_g = _load(INGEST_GATE)
    csv_status = str(csv_g.get("promote_status") or "missing")
    ingest_status = str(ingest_g.get("ingest_status") or "missing")
    combined = _combined_status(csv_status, ingest_status)

    checks = {
        "csv_promote_gate_ok": {"passed": csv_g.get("gate_ok") is True},
        "jsonl_ingest_gate_ok": {"passed": ingest_g.get("gate_ok") is True},
        "combined_hold_or_ready": {
            "passed": combined
            in (
                "dual_idle_hold",
                "csv_ready_to_apply",
                "jsonl_ready_to_apply",
                "dual_ready_to_apply",
                "applied_partial_or_full",
            ),
        },
        "track_a_bridge_forbidden": {"passed": True},
        "send_gate_hold": {"passed": True},
    }
    gate_ok = all(c.get("passed") for c in checks.values())
    return {
        "schema": "sasang_curated_joint_unified_gate_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "send_gate": "HOLD",
        "curated_joint_status": combined if gate_ok else "incomplete",
        "gate_ok": gate_ok,
        "checks": checks,
        "csv_promote_status": csv_status,
        "jsonl_ingest_status": ingest_status,
        "artifact_paths": {
            "csv_promote_gate": str(CSV_GATE).replace("\\", "/"),
            "jsonl_ingest_gate": str(INGEST_GATE).replace("\\", "/"),
        },
        "reproduce": "py scripts/build_sasang_curated_joint_unified_gate_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["gate_ok"], "curated_joint_status": doc["curated_joint_status"]}))
    return 0 if doc["gate_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
