from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import uuid
from typing import Any

from .ledger import EventLedger
from .models import (
    EvidenceFreshness,
    EvidenceOutcome,
    EvidenceRecord,
    GateDecision,
    GateEvaluation,
    TaskState,
)


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def digest_json(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class EvidenceEngine:
    def __init__(self, ledger: EventLedger):
        self.ledger = ledger

    def _prior_evidence(self, task_id: str) -> list[dict[str, Any]]:
        return [
            e["payload"]
            for e in self.ledger.events(task_id=task_id)
            if e["event_type"] == "EVIDENCE_RECORDED"
        ]

    def classify_freshness(
        self,
        *,
        task_id: str,
        actor_role: str,
        suite_id: str,
        suite_digest: str,
        subject_digest: str,
    ) -> EvidenceFreshness:
        prior = self._prior_evidence(task_id)
        if actor_role == "BUILDER":
            return EvidenceFreshness.BUILDER_SELF_REPORT

        same_suite = [
            p for p in prior
            if p["suite_id"] == suite_id and p["suite_digest"] == suite_digest
        ]
        prior_fail_other_subject = any(
            p["outcome"] == EvidenceOutcome.FAIL.value
            and p["subject_digest"] != subject_digest
            for p in same_suite
        )
        if prior_fail_other_subject:
            return EvidenceFreshness.PATCH_CONFIRMATION

        exact_repeat = any(
            p["subject_digest"] == subject_digest
            and p["actor_role"] == actor_role
            and p["suite_id"] == suite_id
            and p["suite_digest"] == suite_digest
            for p in same_suite
        )
        if exact_repeat:
            return EvidenceFreshness.REPEAT_OBSERVATION

        if actor_role == "VALIDATOR":
            return EvidenceFreshness.INDEPENDENT_FRESH
        return EvidenceFreshness.NOT_ESTABLISHED

    def record(
        self,
        *,
        task_id: str,
        actor_id: str,
        actor_role: str,
        suite_id: str,
        suite_digest: str,
        subject_digest: str,
        outcome: EvidenceOutcome,
        detail: dict[str, Any],
    ) -> EvidenceRecord:
        freshness = self.classify_freshness(
            task_id=task_id,
            actor_role=actor_role,
            suite_id=suite_id,
            suite_digest=suite_digest,
            subject_digest=subject_digest,
        )
        record = EvidenceRecord(
            evidence_id="evd_" + uuid.uuid4().hex,
            task_id=task_id,
            actor_id=actor_id,
            actor_role=actor_role,
            suite_id=suite_id,
            suite_digest=suite_digest,
            subject_digest=subject_digest,
            outcome=outcome,
            freshness=freshness,
            detail_digest=digest_json(detail),
            created_at=_now(),
        )
        self.ledger.append(
            "EVIDENCE_RECORDED",
            {
                "evidence_id": record.evidence_id,
                "actor_id": record.actor_id,
                "actor_role": record.actor_role,
                "suite_id": record.suite_id,
                "suite_digest": record.suite_digest,
                "subject_digest": record.subject_digest,
                "outcome": record.outcome.value,
                "freshness": record.freshness.value,
                "detail_digest": record.detail_digest,
                "created_at": record.created_at,
            },
            task_id=task_id,
        )
        return record

    def evaluate_gate(self, task_id: str) -> GateEvaluation:
        evidence = self._prior_evidence(task_id)
        if not evidence:
            result = GateEvaluation(
                task_id=task_id,
                task_state=TaskState.HOLD,
                decision=GateDecision.HOLD,
                reason="NO_EVIDENCE",
                evidence_ceiling="NOT_ADJUDICATED",
            )
            self._record_gate(result)
            return result

        fresh_fails = [
            p for p in evidence
            if p["actor_role"] == "VALIDATOR"
            and p["outcome"] == EvidenceOutcome.FAIL.value
            and p["freshness"] == EvidenceFreshness.INDEPENDENT_FRESH.value
        ]
        if fresh_fails:
            result = GateEvaluation(
                task_id=task_id,
                task_state=TaskState.FAIL,
                decision=GateDecision.HOLD,
                reason="SEALED_INDEPENDENT_FRESH_FAIL",
                evidence_ceiling="FAIL",
            )
            self._record_gate(result)
            return result

        fresh_pass = [
            p for p in evidence
            if p["actor_role"] == "VALIDATOR"
            and p["outcome"] == EvidenceOutcome.PASS.value
            and p["freshness"] == EvidenceFreshness.INDEPENDENT_FRESH.value
        ]
        builder_pass = [
            p for p in evidence
            if p["actor_role"] == "BUILDER"
            and p["outcome"] == EvidenceOutcome.PASS.value
        ]
        if fresh_pass and builder_pass:
            result = GateEvaluation(
                task_id=task_id,
                task_state=TaskState.CANDIDATE,
                decision=GateDecision.HUMAN_GATE,
                reason="INDEPENDENT_FRESH_PASS_WITH_BUILDER_PASS",
                evidence_ceiling="BOUNDED_MERGE_CANDIDATE",
            )
            self._record_gate(result)
            return result

        result = GateEvaluation(
            task_id=task_id,
            task_state=TaskState.HOLD,
            decision=GateDecision.HOLD,
            reason="EVIDENCE_INSUFFICIENT_FOR_CANDIDATE",
            evidence_ceiling="NOT_ADJUDICATED",
        )
        self._record_gate(result)
        return result

    def _record_gate(self, result: GateEvaluation) -> None:
        self.ledger.append(
            "GATE_EVALUATED",
            {
                "task_state": result.task_state.value,
                "decision": result.decision.value,
                "reason": result.reason,
                "evidence_ceiling": result.evidence_ceiling,
                "merge_authorization": result.merge_authorization,
                "deployment_authorization": result.deployment_authorization,
                "send_gate": result.send_gate,
            },
            task_id=result.task_id,
        )
