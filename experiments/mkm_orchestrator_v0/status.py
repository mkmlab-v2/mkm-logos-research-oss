from __future__ import annotations

from collections import Counter
import json
import os
from pathlib import Path
import tempfile
from typing import Any

from .ledger import EventLedger


class StatusBoard:
    """Derived current-state view. The ledger remains authoritative."""

    def __init__(self, ledger: EventLedger):
        self.ledger = ledger

    def build(self) -> dict[str, Any]:
        events = self.ledger.events()
        integrity = self.ledger.verify_chain()
        task_ids = []
        seen = set()
        for event in events:
            task_id = event.get("task_id")
            if task_id and task_id not in seen:
                seen.add(task_id)
                task_ids.append(task_id)

        tasks = [self._task_view(task_id) for task_id in task_ids]
        counts = Counter(task["current_state"] for task in tasks)
        return {
            "schema": "mkm_orchestrator_current_status_v0",
            "authoritative_source": "APPEND_ONLY_EVENT_LEDGER",
            "derived_view": True,
            "ledger": {
                "path": str(self.ledger.path),
                "integrity": integrity,
            },
            "task_count": len(tasks),
            "state_counts": dict(sorted(counts.items())),
            "tasks": tasks,
            "global_boundaries": {
                "auto_merge": "NO",
                "auto_deploy": "NO",
                "auto_send": "NO",
                "unknown_is_valid_result": True,
                "worker_claim_is_evidence": False,
                "patch_confirmation_is_independent_fresh": False,
            },
        }

    def _task_view(self, task_id: str) -> dict[str, Any]:
        rows = self.ledger.events(task_id=task_id)
        created = next((r for r in rows if r["event_type"] == "TASK_CREATED"), None)
        workspace = next(
            (r for r in reversed(rows) if r["event_type"] == "WORKSPACE_BOUND"),
            None,
        )
        worker = next(
            (r for r in reversed(rows) if r["event_type"] == "WORKER_RESULT"),
            None,
        )
        gate = next(
            (r for r in reversed(rows) if r["event_type"] == "GATE_EVALUATED"),
            None,
        )
        violations = [r for r in rows if r["event_type"] == "POLICY_VIOLATION"]
        evidence = [r for r in rows if r["event_type"] == "EVIDENCE_RECORDED"]

        if gate:
            current_state = gate["payload"]["task_state"]
            decision = gate["payload"]["decision"]
            ceiling = gate["payload"]["evidence_ceiling"]
        elif worker:
            current_state = "BUILT"
            decision = "HOLD"
            ceiling = "NOT_ADJUDICATED"
        elif workspace:
            current_state = "WORKSPACE_BOUND"
            decision = "HOLD"
            ceiling = "NOT_ADJUDICATED"
        else:
            current_state = "CREATED"
            decision = "HOLD"
            ceiling = "NOT_ADJUDICATED"

        freshness_counts = Counter(
            e["payload"]["freshness"] for e in evidence
        )
        outcome_counts = Counter(
            e["payload"]["outcome"] for e in evidence
        )
        return {
            "task_id": task_id,
            "objective": created["payload"]["objective"] if created else None,
            "authority": created["payload"]["authority"] if created else None,
            "workspace": workspace["payload"] if workspace else None,
            "last_worker_result": worker["payload"] if worker else None,
            "evidence": {
                "count": len(evidence),
                "outcomes": dict(sorted(outcome_counts.items())),
                "freshness": dict(sorted(freshness_counts.items())),
            },
            "policy_violation_count": len(violations),
            "current_state": current_state,
            "gate_decision": decision,
            "evidence_ceiling": ceiling,
            "merge_authorization": (
                gate["payload"]["merge_authorization"] if gate else "NO"
            ),
            "deployment_authorization": (
                gate["payload"]["deployment_authorization"] if gate else "NO"
            ),
            "send_gate": gate["payload"]["send_gate"] if gate else "HOLD",
        }

    def export(self, path: str | Path) -> Path:
        target = Path(path).expanduser().resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = self.build()
        fd, tmp = tempfile.mkstemp(
            prefix=".mkm-status-",
            suffix=".tmp",
            dir=target.parent,
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2, sort_keys=True)
                f.write("\n")
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, target)
        finally:
            try:
                Path(tmp).unlink(missing_ok=True)
            except OSError:
                pass
        return target
