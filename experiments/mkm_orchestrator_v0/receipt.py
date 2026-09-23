from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
from typing import Any

from .ledger import EventLedger


class EvidenceReceiptError(RuntimeError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _sha(value: Any) -> str:
    raw = value if isinstance(value, bytes) else _canonical(value)
    return hashlib.sha256(raw).hexdigest()


def _git_bytes(root: Path, args: list[str]) -> bytes:
    cp = subprocess.run(
        ["git", *args],
        cwd=str(root),
        capture_output=True,
        timeout=20,
        shell=False,
    )
    if cp.returncode != 0:
        raise EvidenceReceiptError("git observation failed")
    return cp.stdout


def observe_workspace(path: str | Path) -> dict[str, Any]:
    root = Path(path).expanduser().resolve()
    if not root.is_dir():
        return {
            "state": "UNKNOWN",
            "reason": "WORKSPACE_NOT_PRESENT",
        }
    try:
        top = _git_bytes(root, ["rev-parse", "--show-toplevel"]).decode(
            "utf-8", errors="replace"
        ).strip()
        head = _git_bytes(root, ["rev-parse", "HEAD"]).decode(
            "ascii", errors="replace"
        ).strip()
        tracked = _git_bytes(
            root,
            ["diff", "--binary", "--no-ext-diff", "HEAD"],
        )
        changed_tracked = [
            p for p in _git_bytes(root, ["diff", "--name-only", "-z", "HEAD"])
            .decode("utf-8", errors="surrogateescape")
            .split("\0")
            if p
        ]
        untracked = [
            p for p in _git_bytes(
                root,
                ["ls-files", "--others", "--exclude-standard", "-z"],
            )
            .decode("utf-8", errors="surrogateescape")
            .split("\0")
            if p
        ]
    except (OSError, subprocess.SubprocessError, EvidenceReceiptError):
        return {
            "state": "UNKNOWN",
            "reason": "GIT_OBSERVATION_FAILED",
        }

    untracked_facts = []
    for rel in sorted(untracked):
        candidate = root / rel
        try:
            if candidate.is_symlink():
                digest = _sha(os.readlink(candidate).encode("utf-8", errors="replace"))
                kind = "symlink"
            elif candidate.is_file():
                digest = _sha(candidate.read_bytes())
                kind = "file"
            else:
                digest = _sha(b"[NON_FILE]")
                kind = "other"
        except OSError:
            digest = "UNKNOWN"
            kind = "unreadable"
        untracked_facts.append({
            "path": rel.replace("\\", "/"),
            "kind": kind,
            "sha256": digest,
        })

    diff_digest = _sha({
        "tracked_binary_diff_sha256": _sha(tracked),
        "untracked": untracked_facts,
    })
    changed_files = sorted(
        {p.replace("\\", "/") for p in changed_tracked + untracked}
    )
    subject_digest = _sha({
        "head": head,
        "diff_sha256": diff_digest,
        "changed_files": changed_files,
    })
    return {
        "state": "FACT",
        "repo_root": str(Path(top).resolve()),
        "result_revision": head,
        "changed_files": changed_files,
        "diff_sha256": diff_digest,
        "subject_digest": subject_digest,
        "untracked_file_count": len(untracked_facts),
    }


class EvidenceReceiptBuilder:
    """Builds a re-checkable normalized receipt from ledger + current workspace."""

    SCHEMA = "mkm_evidence_receipt_v0"
    SCHEMA_VERSION = 1

    def __init__(self, ledger: EventLedger):
        self.ledger = ledger

    def build(self, task_id: str) -> dict[str, Any]:
        rows = self.ledger.events(task_id=task_id)
        if not rows:
            raise EvidenceReceiptError("task has no ledger events")

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
        evidence = [
            {
                "seq": r["seq"],
                **r["payload"],
            }
            for r in rows
            if r["event_type"] == "EVIDENCE_RECORDED"
        ]

        created_payload = created["payload"] if created else {}
        authority = created_payload.get("authority") or {
            "state": "UNKNOWN",
            "reason": "AUTHORITY_NOT_ESTABLISHED",
        }
        workspace_payload = workspace["payload"] if workspace else {}
        worktree_path = workspace_payload.get("worktree_path")
        observed = (
            observe_workspace(worktree_path)
            if worktree_path
            else {"state": "UNKNOWN", "reason": "WORKSPACE_NOT_BOUND"}
        )

        worker_payload = worker["payload"] if worker else None
        worker_claim = {
            "state": "NOT_ESTABLISHED",
            "reason": "NO_WORKER_RESULT",
        }
        claim_consistency = {
            "state": "NOT_ESTABLISHED",
            "reason": "WORKER_OR_WORKSPACE_OBSERVATION_MISSING",
        }
        if worker_payload:
            worker_claim = {
                "state": "WORKER_CLAIM_ONLY",
                "worker_id": worker_payload.get("worker_id", "UNKNOWN"),
                "worker_backend": (
                    worker_payload.get("metadata", {}).get("backend")
                    or "UNKNOWN"
                ),
                "status": worker_payload.get("status", "UNKNOWN"),
                "subject_digest": worker_payload.get("subject_digest", "UNKNOWN"),
                "changed_files": worker_payload.get("changed_files", []),
                "summary": worker_payload.get("summary", ""),
            }
            if observed.get("state") == "FACT":
                same_subject = (
                    worker_payload.get("subject_digest")
                    == observed.get("subject_digest")
                )
                same_files = sorted(worker_payload.get("changed_files", [])) == sorted(
                    observed.get("changed_files", [])
                )
                claim_consistency = {
                    "state": "FACT",
                    "result": "MATCH" if same_subject and same_files else "MISMATCH",
                    "subject_digest_match": same_subject,
                    "changed_files_match": same_files,
                }

        gate_payload = gate["payload"] if gate else {}
        chain = self.ledger.verify_chain()
        head_hash = chain.get("head_hash")
        covered_seq = rows[-1]["seq"]

        core = {
            "schema": self.SCHEMA,
            "schema_version": self.SCHEMA_VERSION,
            "task_id": task_id,
            "objective": created_payload.get("objective", "[UNKNOWN]"),
            "authority": authority,
            "base_revision": (
                workspace_payload.get("base_revision")
                or (
                    authority.get("base_revision")
                    if isinstance(authority, dict)
                    else None
                )
                or "UNKNOWN"
            ),
            "workspace": (
                {
                    "state": "FACT",
                    "branch_name": workspace_payload.get("branch_name"),
                    "worktree_path": workspace_payload.get("worktree_path"),
                    "repository_path": workspace_payload.get("repository_path"),
                }
                if workspace
                else {"state": "UNKNOWN", "reason": "WORKSPACE_NOT_BOUND"}
            ),
            "observed_result": observed,
            "worker_claim": worker_claim,
            "worker_claim_consistency": claim_consistency,
            "evidence": evidence,
            "freshness_classes": sorted(
                {e.get("freshness", "NOT_ESTABLISHED") for e in evidence}
            ),
            "evidence_ceiling": gate_payload.get(
                "evidence_ceiling", "NOT_ADJUDICATED"
            ),
            "authorization": {
                "gate_decision": gate_payload.get("decision", "HOLD"),
                "merge": gate_payload.get("merge_authorization", "NO"),
                "deployment": gate_payload.get("deployment_authorization", "NO"),
                "send": gate_payload.get("send_gate", "HOLD"),
            },
            "ledger": {
                "integrity": chain,
                "covered_seq": covered_seq,
                "covered_head_hash": head_hash,
            },
        }
        receipt_sha256 = _sha(core)
        return {
            **core,
            "receipt_id": "rcp_" + receipt_sha256[:24],
            "receipt_sha256": receipt_sha256,
        }

    def issue(self, task_id: str) -> dict[str, Any]:
        receipt = self.build(task_id)
        self.ledger.append(
            "EVIDENCE_RECEIPT_ISSUED",
            {
                "receipt_id": receipt["receipt_id"],
                "receipt_sha256": receipt["receipt_sha256"],
                "covered_seq": receipt["ledger"]["covered_seq"],
                "covered_head_hash": receipt["ledger"]["covered_head_hash"],
                "schema": receipt["schema"],
                "schema_version": receipt["schema_version"],
            },
            task_id=task_id,
        )
        return receipt
