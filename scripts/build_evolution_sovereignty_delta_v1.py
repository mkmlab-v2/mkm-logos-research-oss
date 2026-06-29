#!/usr/bin/env python3
"""Record lens sovereignty verdict/metric deltas for evolution spine (B-track, HITL-only).

Compares current lens_sovereignty_report_v1_2 against last snapshot; appends jsonl on change.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = ROOT / "docs/final/artifacts/lens_sovereignty_report_v1_2_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/evolution_sovereignty_delta_latest.json"
DEFAULT_HISTORY = ROOT / "reports/evolution_sovereignty_delta_v1.jsonl"
DEFAULT_QUEUE = ROOT / "docs/final/artifacts/evolution_sovereignty_hitl_queue_v1_latest.json"
DEFAULT_SNAPSHOT = ROOT / "docs/final/artifacts/evolution_sovereignty_snapshot_v1.json"

SCHEMA = "evolution_sovereignty_delta_v1"
QUEUE_SCHEMA = "evolution_sovereignty_hitl_queue_v1"

WATCH_FIELDS = (
    "daily_wf_verdict",
    "role_contract_verdict",
    "supplementary_verdict",
    "best_lens_arm_id",
    "best_lens_soft_hit_rate_wf",
    "role_pass_count",
    "supplementary_pass_count",
    "promotion_ready",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        o = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return o if isinstance(o, dict) else {}


def extract_snapshot(report: dict[str, Any]) -> dict[str, Any]:
    daily = report.get("daily_kospi_wf") if isinstance(report.get("daily_kospi_wf"), dict) else {}
    best = daily.get("best_lens") if isinstance(daily.get("best_lens"), dict) else {}
    role_lines = report.get("role_verdict_lines")
    role_pass_count = 0
    if isinstance(role_lines, list) and role_lines:
        line = str(role_lines[0])
        if "passes (" in line:
            try:
                role_pass_count = int(line.split("passes (")[1].split("/")[0])
            except (IndexError, ValueError):
                role_pass_count = 0
    supp_passes = report.get("supplementary_passes")
    return {
        "schema": "evolution_sovereignty_snapshot_v1",
        "source_report_schema": report.get("schema"),
        "source_generated_at_utc": report.get("generated_at_utc"),
        "daily_wf_verdict": daily.get("verdict") or report.get("daily_wf_verdict"),
        "role_contract_verdict": report.get("role_contract_verdict"),
        "supplementary_verdict": report.get("supplementary_verdict"),
        "best_lens_arm_id": best.get("arm_id"),
        "best_lens_soft_hit_rate_wf": best.get("soft_hit_rate_wf"),
        "role_pass_count": role_pass_count,
        "supplementary_pass_count": len(supp_passes) if isinstance(supp_passes, list) else 0,
        "promotion_ready": bool(report.get("promotion_ready")),
    }


def _diff_snapshots(prev: dict[str, Any], curr: dict[str, Any]) -> dict[str, dict[str, Any]]:
    changes: dict[str, dict[str, Any]] = {}
    for key in WATCH_FIELDS:
        old = prev.get(key)
        new = curr.get(key)
        if old != new:
            changes[key] = {"from": old, "to": new}
    return changes


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def _merge_hitl_queue(
    queue_path: Path,
    *,
    changes: dict[str, dict[str, Any]],
    ts: str,
) -> dict[str, Any]:
    existing = _load_json(queue_path)
    items = list(existing.get("items") or []) if isinstance(existing.get("items"), list) else []
    for field, delta in changes.items():
        items.append(
            {
                "id": f"{ts.replace(':', '').replace('-', '')}_{field}",
                "kind": "sovereignty_verdict_transition",
                "field": field,
                "from": delta.get("from"),
                "to": delta.get("to"),
                "requires_human_approval": True,
                "auto_apply": False,
                "suggested_action": "commander_review_in_chat",
                "recorded_at_utc": ts,
            }
        )
    # keep last 50 pending-style rows
    items = items[-50:]
    doc = {
        "schema": QUEUE_SCHEMA,
        "updated_at_utc": ts,
        "research_only": True,
        "items": items,
    }
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    queue_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return doc


def build_delta(
    *,
    report_path: Path,
    snapshot_path: Path,
    history_path: Path,
    queue_path: Path,
    out_path: Path,
) -> dict[str, Any]:
    report = _load_json(report_path)
    curr = extract_snapshot(report)
    prev = _load_json(snapshot_path)
    if prev.get("schema") != "evolution_sovereignty_snapshot_v1":
        prev = {}

    changes = _diff_snapshots(prev, curr) if prev else {k: {"from": None, "to": curr.get(k)} for k in WATCH_FIELDS}
    first_run = not bool(prev)
    delta_detected = bool(changes) and not first_run

    ts = _utc_now()
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": ts,
        "research_only": True,
        "report_path": str(report_path.resolve()),
        "first_run": first_run,
        "delta_detected": delta_detected,
        "changes": changes if delta_detected else ({} if not first_run else changes),
        "current_snapshot": curr,
        "previous_snapshot": prev if prev else None,
    }

    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text(json.dumps(curr, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if delta_detected:
        row = {
            "ts_utc": ts,
            "delta_detected": True,
            "changes": changes,
            "current_snapshot": curr,
            "previous_snapshot": prev,
        }
        _append_jsonl(history_path, row)
        payload["hitl_queue"] = _merge_hitl_queue(queue_path, changes=changes, ts=ts)
    elif first_run:
        payload["note"] = "baseline snapshot stored; no history append on first run"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workspace-root", type=Path, default=ROOT)
    ap.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    ap.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    ap.add_argument("--history", type=Path, default=DEFAULT_HISTORY)
    ap.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ns = ap.parse_args()
    root = ns.workspace_root.resolve()

    def _p(p: Path) -> Path:
        return p if p.is_absolute() else root / p

    if not _p(ns.report).is_file():
        print(f"MISSING report: {_p(ns.report)}")
        return 1

    doc = build_delta(
        report_path=_p(ns.report),
        snapshot_path=_p(ns.snapshot),
        history_path=_p(ns.history),
        queue_path=_p(ns.queue),
        out_path=_p(ns.out_json),
    )
    print(
        f"WROTE: {_p(ns.out_json).resolve()} "
        f"delta_detected={doc['delta_detected']} first_run={doc['first_run']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
