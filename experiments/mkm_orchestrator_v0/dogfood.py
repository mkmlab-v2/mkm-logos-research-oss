from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from .ledger import EventLedger
from .measurement import DogfoodMeasurementV0, MeasurementRecorder
from .models import GateDecision, TaskContract, TaskState
from .orchestrator import MKMOrchestrator
from .receipt import EvidenceReceiptBuilder
from .shared_status import SharedStatusPublisher
from .workspace import WorktreeManager


class DogfoodRunnerError(RuntimeError):
    pass


class DogfoodRunner:
    """Bounded lifecycle wrapper for internal MKM dogfood tasks.

    Worker execution remains external to this lane. The runner establishes the
    task/worktree contract, then closes a measured task after evidence has been
    recorded. It never merges, deploys, sends, or schedules a next task.
    """

    def __init__(
        self,
        *,
        ledger: EventLedger,
        worktree_root: str | Path,
        shared_status_dir: str | Path,
    ):
        self.ledger = ledger
        self.orchestrator = MKMOrchestrator(
            ledger=ledger,
            worktrees=WorktreeManager(worktree_root),
        )
        self.measurements = MeasurementRecorder(ledger)
        self.receipts = EvidenceReceiptBuilder(ledger)
        self.publisher = SharedStatusPublisher(ledger)
        self.shared_status_dir = Path(shared_status_dir).expanduser().resolve()

    def start(
        self,
        task: TaskContract,
        *,
        cohort: str = "EVIDENCE_GATE",
    ) -> dict[str, Any]:
        if cohort not in {"BASELINE", "EVIDENCE_GATE"}:
            raise DogfoodRunnerError("invalid cohort")
        if any(
            e["event_type"] == "DOGFOOD_RUN_STARTED"
            for e in self.ledger.events(task_id=task.task_id)
        ):
            raise DogfoodRunnerError("dogfood task already started")

        self.orchestrator.create_task(task)
        binding = self.orchestrator.bind_workspace(task, create=True)
        self.ledger.append(
            "DOGFOOD_RUN_STARTED",
            {
                "cohort": cohort,
                "task_id": task.task_id,
                "workspace": asdict(binding),
                "automatic_next_task": "NO",
                "merge_authorization": "NO",
                "deployment_authorization": "NO",
                "send_gate": "HOLD",
            },
            task_id=task.task_id,
        )
        published = self.publisher.publish(self.shared_status_dir)
        return {
            "task_id": task.task_id,
            "cohort": cohort,
            "workspace": asdict(binding),
            "shared_status": published,
            "next_action": "WORKER_EXECUTION_EXTERNAL",
            "merge_authorization": "NO",
            "deployment_authorization": "NO",
            "send_gate": "HOLD",
        }

    def finalize(
        self,
        task_id: str,
        measurement: DogfoodMeasurementV0,
    ) -> dict[str, Any]:
        if measurement.task_id != task_id:
            raise DogfoodRunnerError("measurement task_id mismatch")
        events = self.ledger.events(task_id=task_id)
        started = next(
            (e for e in events if e["event_type"] == "DOGFOOD_RUN_STARTED"),
            None,
        )
        if started is None:
            raise DogfoodRunnerError("dogfood task not started")
        if any(e["event_type"] == "DOGFOOD_TASK_FINALIZED" for e in events):
            raise DogfoodRunnerError("dogfood task already finalized")
        if measurement.cohort != started["payload"]["cohort"]:
            raise DogfoodRunnerError("measurement cohort mismatch")

        gate_event = next(
            (e for e in reversed(events) if e["event_type"] == "GATE_EVALUATED"),
            None,
        )
        if gate_event is None:
            gate = self.orchestrator.evaluate(task_id)
        else:
            payload = gate_event["payload"]
            gate = {
                "task_state": payload["task_state"],
                "decision": payload["decision"],
                "reason": payload["reason"],
                "evidence_ceiling": payload["evidence_ceiling"],
                "merge_authorization": payload["merge_authorization"],
                "deployment_authorization": payload["deployment_authorization"],
                "send_gate": payload["send_gate"],
            }

        self.measurements.record(measurement)
        receipt = self.receipts.issue(task_id)

        if isinstance(gate, dict):
            task_state = gate["task_state"]
            decision = gate["decision"]
            reason = gate["reason"]
            evidence_ceiling = gate["evidence_ceiling"]
        else:
            task_state = gate.task_state.value
            decision = gate.decision.value
            reason = gate.reason
            evidence_ceiling = gate.evidence_ceiling

        if task_state == TaskState.FAIL.value:
            next_action = "HUMAN_ADJUDICATION_REQUIRED"
        elif decision == GateDecision.HUMAN_GATE.value:
            next_action = "HUMAN_GATE"
        else:
            next_action = "HOLD"

        self.ledger.append(
            "DOGFOOD_TASK_FINALIZED",
            {
                "cohort": measurement.cohort,
                "task_state": task_state,
                "gate_decision": decision,
                "gate_reason": reason,
                "evidence_ceiling": evidence_ceiling,
                "receipt_id": receipt["receipt_id"],
                "receipt_sha256": receipt["receipt_sha256"],
                "next_action": next_action,
                "automatic_next_task": "NO",
                "merge_authorization": "NO",
                "deployment_authorization": "NO",
                "send_gate": "HOLD",
            },
            task_id=task_id,
        )
        published = self.publisher.publish(self.shared_status_dir)
        summary = self.measurements.summarize()
        return {
            "task_id": task_id,
            "task_state": task_state,
            "gate_decision": decision,
            "gate_reason": reason,
            "evidence_ceiling": evidence_ceiling,
            "receipt_id": receipt["receipt_id"],
            "receipt_sha256": receipt["receipt_sha256"],
            "next_action": next_action,
            "shared_status": published,
            "dogfood_summary": summary,
            "merge_authorization": "NO",
            "deployment_authorization": "NO",
            "send_gate": "HOLD",
        }
