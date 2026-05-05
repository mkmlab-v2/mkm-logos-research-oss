#!/usr/bin/env python3
"""Apply human-audit decisions to review queue and rerun integrated gates."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "docs" / "final" / "artifacts" / "layer5_incident_review_queue_v1_latest.jsonl"
AUDIT_CSV = ROOT / "docs" / "final" / "artifacts" / "layer5_human_audit_review_template_v1.csv"
SUMMARY = ROOT / "docs" / "final" / "artifacts" / "layer5_human_audit_apply_summary_latest.json"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    with path.open("r", encoding="utf-8-sig") as fh:
        for line in fh:
            s = line.strip()
            if not s:
                continue
            try:
                obj = json.loads(s)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                rows.append(obj)
    return rows


def _read_audit_csv(path: Path) -> dict[str, str]:
    decisions: dict[str, str] = {}
    if not path.is_file():
        return decisions
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            cid = str((row.get("case_id") or "")).strip()
            dec = str((row.get("audit_decision") or "")).strip().lower()
            if not cid or dec not in {"approve", "reject"}:
                continue
            decisions[cid] = dec
    return decisions


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def _run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{proc.stdout}\n{proc.stderr}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--queue-jsonl", type=Path, default=QUEUE)
    ap.add_argument("--audit-csv", type=Path, default=AUDIT_CSV)
    ap.add_argument("--summary-json", type=Path, default=SUMMARY)
    ap.add_argument("--sample-size", type=int, default=50)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    decisions = _read_audit_csv(args.audit_csv)
    rows = _read_jsonl(args.queue_jsonl)

    approve_count = reject_count = 0
    for row in rows:
        cid = str(row.get("case_id") or "")
        dec = decisions.get(cid)
        if dec == "approve":
            row["review_status"] = "approved"
            approve_count += 1
        elif dec == "reject":
            row["review_status"] = "rejected"
            reject_count += 1
    _write_jsonl(args.queue_jsonl, rows)

    _run(
        [
            "py",
            "scripts/promote_layer5_approved_goldset_v1.py",
            "--input-jsonl",
            "docs/final/artifacts/layer5_incident_review_queue_v1_latest.jsonl",
            "--output-jsonl",
            "docs/final/artifacts/layer5_incident_goldset_human_v1_latest.jsonl",
            "--summary-json",
            "docs/final/artifacts/layer5_incident_goldset_human_summary_latest.json",
            "--sample-size",
            str(args.sample_size),
            "--seed",
            str(args.seed),
        ]
    )
    _run(
        [
            "py",
            "scripts/benchmark_layer5_policy_gate_v1.py",
            "--input-jsonl",
            "docs/final/artifacts/layer5_incident_goldset_human_v1_latest.jsonl",
            "--sample-size",
            str(args.sample_size),
            "--seed",
            str(args.seed),
            "--output-json",
            "docs/final/artifacts/layer5_policy_gate_benchmark_latest.json",
        ]
    )
    _run(
        [
            "py",
            "scripts/benchmark_layer1_router_v1.py",
            "--input-jsonl",
            "docs/final/artifacts/layer5_incident_goldset_human_v1_latest.jsonl",
            "--output-json",
            "docs/final/artifacts/layer1_router_benchmark_latest.json",
            "--min-router-accuracy",
            "0.95",
        ]
    )
    _run(
        [
            "py",
            "scripts/build_layer1_layer5_integrated_gate_report_v1.py",
            "--layer1-json",
            "docs/final/artifacts/layer1_router_benchmark_latest.json",
            "--layer5-json",
            "docs/final/artifacts/layer5_policy_gate_benchmark_latest.json",
            "--output-json",
            "docs/final/artifacts/layer1_layer5_integrated_gate_report_latest.json",
            "--min-approved-samples",
            "50",
        ]
    )

    summary = {
        "schema": "layer5_human_audit_apply_summary_v1",
        "queue_jsonl": str(args.queue_jsonl).replace("\\", "/"),
        "audit_csv": str(args.audit_csv).replace("\\", "/"),
        "applied_approve_count": approve_count,
        "applied_reject_count": reject_count,
        "decisions_total": len(decisions),
        "note": "Post-apply benchmarks and integrated gate were refreshed.",
    }
    args.summary_json.parent.mkdir(parents=True, exist_ok=True)
    args.summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "approve": approve_count, "reject": reject_count, "summary_json": str(args.summary_json)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
