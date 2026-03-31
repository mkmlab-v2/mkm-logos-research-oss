#!/usr/bin/env python3
"""Emit warning flag file when strict alert profile is on hold."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
REPORT_DIR = ROOT / "reports" / "constitution" / "btrack_pilot"
DEFAULT_INDEX = REPORT_DIR / "symbol_c_validation_run_index_latest.json"
DEFAULT_HISTORY_ROOT = REPORT_DIR / "history" / "symbol_c_validation"
DEFAULT_URGENT_MIRROR = REPORT_DIR / "urgent_queue_latest.json"
DEFAULT_ACTIONS_TEMPLATE_STABLE = (
    ROOT / "data" / "logos" / "btrack_pilot" / "gates" / "symbol_c_validation_warning_actions_template_stable.json"
)
DEFAULT_ACTIONS_TEMPLATE_STRICT = (
    ROOT / "data" / "logos" / "btrack_pilot" / "gates" / "symbol_c_validation_warning_actions_template_strict.json"
)
DEFAULT_SLA_TEMPLATE = ROOT / "data" / "logos" / "btrack_pilot" / "gates" / "symbol_c_validation_review_sla_template.json"


def _abs(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def _jread(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _jwrite(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _jread_or_none(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _select_actions_template(profile: str, stable_path: Path, strict_path: Path) -> Path:
    return stable_path if profile == "stable" else strict_path


def _artifact_path_for_run(target_dir: Path, stem_base: str, run_id: str) -> str:
    p = target_dir / f"{stem_base}_{run_id}.json"
    return str(p)


def _normalize_actions(raw_actions: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not isinstance(raw_actions, list):
        return out
    for i, item in enumerate(raw_actions):
        if isinstance(item, dict):
            out.append(
                {
                    "id": item.get("id", f"action-{i+1}"),
                    "priority": item.get("priority", "P2"),
                    "owner": item.get("owner", "unassigned"),
                    "status": item.get("status", "pending"),
                    "action": item.get("action", ""),
                }
            )
            continue
        if isinstance(item, str):
            out.append(
                {
                    "id": f"action-{i+1}",
                    "priority": "P2",
                    "owner": "unassigned",
                    "status": "pending",
                    "action": item,
                }
            )
    return out


def _priority_rank(priority: Any) -> int:
    p = str(priority or "P9").strip().upper()
    if p.startswith("P") and p[1:].isdigit():
        return int(p[1:])
    return 9


def _compute_due_at_utc(base_dt: datetime, due_hours: int) -> str:
    due_dt = base_dt + timedelta(hours=max(1, int(due_hours)))
    return due_dt.isoformat()


def _apply_sla(actions: list[dict[str, Any]], sla_template: dict[str, Any], base_dt: datetime) -> list[dict[str, Any]]:
    priority_due_hours = sla_template.get("priority_due_hours", {})
    default_due_hours = int(sla_template.get("default_due_hours", 168))
    out: list[dict[str, Any]] = []
    for a in actions:
        p = str(a.get("priority", "P2")).upper()
        due_hours = default_due_hours
        if isinstance(priority_due_hours, dict):
            raw = priority_due_hours.get(p, default_due_hours)
            try:
                due_hours = int(raw)
            except (TypeError, ValueError):
                due_hours = default_due_hours
        due_at_utc = _compute_due_at_utc(base_dt, due_hours)
        x = dict(a)
        x["due_hours"] = due_hours
        x["due_at_utc"] = due_at_utc
        out.append(x)
    return out


def _build_review_queue(
    run_id: str,
    alert_profile: str,
    alert: dict[str, Any],
    actions: list[dict[str, Any]],
    sla_template: dict[str, Any],
) -> dict[str, Any]:
    now_utc = datetime.now(timezone.utc)
    with_sla = _apply_sla(actions, sla_template, now_utc)
    ordered = sorted(with_sla, key=lambda a: (_priority_rank(a.get("priority")), str(a.get("id", ""))))
    return {
        "meta": {
            "kind": "symbol_c_validation_review_queue",
            "run_id": run_id,
            "alert_profile": alert_profile,
            "generated_from": "warning_flag",
            "generated_at_utc": now_utc.isoformat(),
        },
        "alert_failures": alert.get("failures", []),
        "sla": {
            "default_due_hours": sla_template.get("default_due_hours", 168),
            "priority_due_hours": sla_template.get("priority_due_hours", {}),
        },
        "tasks": ordered,
    }


def _build_urgent_queue(review_queue: dict[str, Any]) -> dict[str, Any]:
    tasks = review_queue.get("tasks", [])
    p1_tasks = []
    if isinstance(tasks, list):
        for t in tasks:
            if isinstance(t, dict) and str(t.get("priority", "")).upper() == "P1":
                p1_tasks.append(t)
    meta = review_queue.get("meta", {}) if isinstance(review_queue.get("meta"), dict) else {}
    return {
        "meta": {
            "kind": "symbol_c_validation_urgent_queue",
            "run_id": meta.get("run_id"),
            "alert_profile": meta.get("alert_profile"),
            "generated_from": "review_queue",
            "generated_at_utc": meta.get("generated_at_utc"),
        },
        "task_count": len(p1_tasks),
        "tasks": p1_tasks,
    }


def _recent_history_run_ids(history_root: Path, top_n: int = 3) -> list[str]:
    if not history_root.is_dir():
        return []
    dirs = [p for p in history_root.iterdir() if p.is_dir()]
    dirs.sort(key=lambda p: p.name, reverse=True)
    return [p.name for p in dirs[: max(1, int(top_n))]]


def _recent_history_compact_decisions(history_root: Path, top_n: int = 3) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for run_id in _recent_history_run_ids(history_root, top_n=top_n):
        run_dir = history_root / run_id
        summary_path = run_dir / "run_decision_summary.json"
        stable_decision = "unknown"
        strict_decision = "unknown"
        top_overlap_rate: float | None = None
        if summary_path.is_file():
            payload = _jread_or_none(summary_path) or {}
            if isinstance(payload, dict):
                stable_decision = str(payload.get("stable_decision", "unknown"))
                strict_decision = str(payload.get("strict_decision", "unknown"))
                raw_overlap = payload.get("top_overlap_rate")
                if isinstance(raw_overlap, (int, float)):
                    top_overlap_rate = float(raw_overlap)
        out.append(
            {
                "run_id": run_id,
                "stable_decision": stable_decision,
                "strict_decision": strict_decision,
                "top_overlap_rate": top_overlap_rate,
                "delta_vs_prev_overlap": None,
            }
        )
    # out is ordered latest -> older; compute delta against immediate older run
    for i in range(len(out) - 1):
        curr = out[i].get("top_overlap_rate")
        prev = out[i + 1].get("top_overlap_rate")
        if isinstance(curr, (int, float)) and isinstance(prev, (int, float)):
            out[i]["delta_vs_prev_overlap"] = float(curr) - float(prev)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Emit warning flag json for strict hold decision")
    ap.add_argument("--run-index-json", default=str(DEFAULT_INDEX))
    ap.add_argument("--history-root", default=str(DEFAULT_HISTORY_ROOT))
    ap.add_argument("--alert-profile", default="strict")
    ap.add_argument("--actions-template-stable", default=str(DEFAULT_ACTIONS_TEMPLATE_STABLE))
    ap.add_argument("--actions-template-strict", default=str(DEFAULT_ACTIONS_TEMPLATE_STRICT))
    ap.add_argument("--sla-template", default=str(DEFAULT_SLA_TEMPLATE))
    ap.add_argument("--urgent-mirror-json", default=str(DEFAULT_URGENT_MIRROR))
    args = ap.parse_args()

    index_path = _abs(args.run_index_json)
    history_root = _abs(args.history_root)
    alert_profile = str(args.alert_profile).strip().lower() or "strict"
    actions_template_path = _select_actions_template(
        alert_profile,
        _abs(args.actions_template_stable),
        _abs(args.actions_template_strict),
    )
    actions_template = _jread_or_none(actions_template_path) or {}
    sla_template = _jread_or_none(_abs(args.sla_template)) or {}
    urgent_mirror_path = _abs(args.urgent_mirror_json)
    if not index_path.is_file():
        print(f"WARN: run index missing: {index_path}")
        return 0

    idx = _jread(index_path)
    profiles = idx.get("alert_profiles", {})
    stable_alert = profiles.get("stable", {}) if isinstance(profiles, dict) else {}
    strict_alert = profiles.get("strict", {}) if isinstance(profiles, dict) else {}
    alert = profiles.get(alert_profile, {}) if isinstance(profiles, dict) else {}
    decision = str(alert.get("decision", "hold")).lower()
    latest_dir = idx.get("status", {}).get("latest_history_dir")
    if not isinstance(latest_dir, str) or not latest_dir:
        print("WARN: latest_history_dir missing in run index status")
        return 0

    target_dir = history_root / latest_dir
    if not target_dir.is_dir():
        print(f"WARN: latest history dir missing: {target_dir}")
        return 0

    flag_path = target_dir / "warning_flag.json"
    review_queue_path = target_dir / "review_queue.json"
    urgent_queue_path = target_dir / "urgent_queue.json"
    decision_summary_path = target_dir / "run_decision_summary.json"

    decision_summary = {
        "meta": {
            "kind": "symbol_c_validation_run_decision_summary",
            "run_id": latest_dir,
            "source_run_index_json": str(index_path),
        },
        "stable_decision": str(stable_alert.get("decision", "unknown")).lower(),
        "strict_decision": str(strict_alert.get("decision", "unknown")).lower(),
        "top_overlap_rate": idx.get("status", {}).get("top_overlap_rate"),
    }
    _jwrite(decision_summary_path, decision_summary)
    print(f"OK: run decision summary updated path={decision_summary_path}")
    if decision != "hold":
        if flag_path.exists():
            flag_path.unlink(missing_ok=True)
            print(f"OK: warning cleared (decision={decision}) path={flag_path}")
        else:
            print(f"OK: no warning emitted (decision={decision})")
        if review_queue_path.exists():
            review_queue_path.unlink(missing_ok=True)
            print(f"OK: review queue cleared (decision={decision}) path={review_queue_path}")
        if urgent_queue_path.exists():
            urgent_queue_path.unlink(missing_ok=True)
            print(f"OK: urgent queue cleared (decision={decision}) path={urgent_queue_path}")
        if urgent_mirror_path.exists():
            urgent_mirror_path.unlink(missing_ok=True)
            print(f"OK: urgent mirror cleared (decision={decision}) path={urgent_mirror_path}")
        return 0

    actions = _normalize_actions(actions_template.get("recommended_actions", []))
    payload = {
        "meta": {
            "kind": "symbol_c_validation_warning_flag",
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "alert_profile": alert_profile,
            "source_run_index_json": str(index_path),
            "run_id": latest_dir,
            "actions_template": str(actions_template_path),
        },
        "alert": alert,
        "artifacts": {
            "packet_json": _artifact_path_for_run(target_dir, "symbol_c_validation_packet", latest_dir),
            "packet_baseline_json": _artifact_path_for_run(
                target_dir, "symbol_c_validation_packet_baseline", latest_dir
            ),
            "queue_compare_json": _artifact_path_for_run(
                target_dir, "symbol_c_validation_queue_compare", latest_dir
            ),
            "checklist_stable_json": _artifact_path_for_run(
                target_dir, "symbol_c_validation_checklist_stable", latest_dir
            ),
            "checklist_exploratory_json": _artifact_path_for_run(
                target_dir, "symbol_c_validation_checklist_exploratory", latest_dir
            ),
        },
        "recommended_actions": actions,
    }
    _jwrite(flag_path, payload)
    review_queue = _build_review_queue(latest_dir, alert_profile, alert, actions, sla_template)
    _jwrite(review_queue_path, review_queue)
    urgent_queue = _build_urgent_queue(review_queue)
    urgent_queue["history"] = {
        "recent_run_ids": _recent_history_run_ids(history_root, top_n=3),
        "latest_run_id": latest_dir,
        "compact_decisions": _recent_history_compact_decisions(history_root, top_n=3),
    }
    _jwrite(urgent_queue_path, urgent_queue)
    _jwrite(urgent_mirror_path, urgent_queue)
    print("WARN: strict hold detected, warning flag emitted")
    print(f"path={flag_path}")
    print(f"review_queue={review_queue_path}")
    print(f"urgent_queue={urgent_queue_path}")
    print(f"urgent_mirror={urgent_mirror_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
