#!/usr/bin/env python3
"""Build ops action queue from xai_contract_failures_top5_latest.json."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IN = ROOT / "docs" / "final" / "artifacts" / "xai_contract_failures_top5_latest.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "xai_action_queue_ops_latest.json"
DEFAULT_POLICY = ROOT / "docs" / "final" / "artifacts" / "xai_ops_owner_sla_policy_v1.json"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", "-i", type=Path, default=DEFAULT_IN)
    ap.add_argument("--output", "-o", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--policy-json", type=Path, default=DEFAULT_POLICY)
    ap.add_argument("--default-owner", type=str, default="xai-ops")
    ap.add_argument("--due-days", type=int, default=2)
    ns = ap.parse_args()

    doc = json.loads(ns.input.read_text(encoding="utf-8")) if ns.input.is_file() else {}
    policy = json.loads(ns.policy_json.read_text(encoding="utf-8")) if ns.policy_json.is_file() else {}
    owner_map = policy.get("owner_map") if isinstance(policy.get("owner_map"), dict) else {}
    sla_hours = policy.get("sla_hours_by_priority") if isinstance(policy.get("sla_hours_by_priority"), dict) else {}
    default_owner = str(policy.get("default_owner") or ns.default_owner)
    queue = doc.get("action_queue") if isinstance(doc.get("action_queue"), list) else []
    now = _utc_now()
    due = now + timedelta(days=max(1, ns.due_days))

    tasks: list[dict[str, Any]] = []
    for item in queue:
        if not isinstance(item, dict):
            continue
        qid = item.get("question_id")
        missing = item.get("missing_fields") if isinstance(item.get("missing_fields"), list) else []
        pr = str(item.get("priority") or "high").lower()
        owner = str(owner_map.get(str(item.get("domain_tag") or ""), default_owner))
        due_hours = int(sla_hours.get(pr, max(24, ns.due_days * 24)))
        due_at = now + timedelta(hours=due_hours)
        tasks.append(
            {
                "task_id": f"xai_fix_{qid}",
                "owner": owner,
                "priority": pr,
                "question_id": qid,
                "domain_tag": item.get("domain_tag"),
                "missing_fields": missing,
                "action": "Patch runtime answer fields and rerun xai gate.",
                "status": "open",
                "created_at_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "due_at_utc": due_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "sla_hours": due_hours,
            }
        )

    out = {
        "schema": "xai_action_queue_ops_v1",
        "generated_at_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_top5_path": str(ns.input.resolve()).replace("\\", "/") if ns.input.exists() else str(ns.input),
        "policy_path": str(ns.policy_json.resolve()).replace("\\", "/") if ns.policy_json.exists() else str(ns.policy_json),
        "task_count": len(tasks),
        "tasks": tasks,
    }
    if len(tasks) == 0:
        fallback_due = now + timedelta(hours=24)
        out["tasks"] = [
            {
                "task_id": "xai_healthcheck_sample3",
                "owner": default_owner,
                "priority": "low",
                "question_id": None,
                "domain_tag": "operations",
                "missing_fields": [],
                "action": "Run manual quality spot-check on 3 random questions and confirm contract adherence.",
                "status": "open",
                "created_at_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "due_at_utc": fallback_due.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "sla_hours": 24,
                "is_fallback_health_check": True,
            }
        ]
        out["task_count"] = 1
        out["note"] = "No contract failures detected; fallback health-check task created."
    ns.output.parent.mkdir(parents=True, exist_ok=True)
    ns.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(ns.output.resolve()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
