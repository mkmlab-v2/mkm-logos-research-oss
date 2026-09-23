from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments"))

from mkm_orchestrator_v0.dogfood import DogfoodRunner
from mkm_orchestrator_v0.ledger import EventLedger
from mkm_orchestrator_v0.measurement import DogfoodMeasurementV0
from mkm_orchestrator_v0.models import AuthorityContract, EvidenceOutcome, TaskContract, WorkerResult
from mkm_orchestrator_v0.receipt import observe_workspace
from mkm_orchestrator_v0.validator import IndependentValidatorContract


def run(cwd: Path, args: list[str], *, check: bool = True, input_bytes: bytes | None = None):
    return subprocess.run(
        args,
        cwd=str(cwd),
        input=input_bytes,
        capture_output=True,
        check=check,
    )


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def verify_commit(repo: Path, revision: str) -> str:
    cp = run(repo, ["git", "rev-parse", "--verify", f"{revision}^{{commit}}"])
    return cp.stdout.decode("ascii", errors="replace").strip()


class CommitRangeReplayWorker:
    def __init__(
        self,
        *,
        worker_id: str,
        repo: Path,
        base_revision: str,
        result_revision: str,
        allowed_paths: tuple[str, ...],
    ):
        self.worker_id = worker_id
        self.repo = repo
        self.base_revision = base_revision
        self.result_revision = result_revision
        self.allowed_paths = allowed_paths
        self.patch_sha256 = ""

    def run(self, task, workspace):
        patch = run(
            self.repo,
            [
                "git", "diff", "--binary", "--no-ext-diff",
                self.base_revision, self.result_revision, "--", *self.allowed_paths,
            ],
        ).stdout
        self.patch_sha256 = sha256_bytes(patch)
        if not patch:
            raise RuntimeError("replay patch is empty")
        worktree = Path(workspace.worktree_path)
        run(
            worktree,
            ["git", "apply", "--binary", "--whitespace=nowarn", "-"],
            input_bytes=patch,
        )
        observed = observe_workspace(worktree)
        if observed.get("state") != "FACT":
            raise RuntimeError("replayed workspace observation not established")
        return WorkerResult(
            worker_id=self.worker_id,
            task_id=task.task_id,
            status="PASS",
            subject_digest=observed["subject_digest"],
            changed_files=tuple(observed["changed_files"]),
            summary="commit-range replay applied",
            metadata={
                "backend": "github_commit_range_replay",
                "base_revision": self.base_revision,
                "replayed_result_revision": self.result_revision,
                "patch_sha256": self.patch_sha256,
            },
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    manifest_path = Path(args.manifest).resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    repo = ROOT.resolve()
    base = verify_commit(repo, manifest["base_revision"])
    result_revision = verify_commit(repo, manifest["result_revision"])

    allowed_paths = tuple(manifest["allowed_paths"])
    suite_paths = list(manifest["suite_paths"])
    task = TaskContract(
        task_id=manifest["task_id"],
        objective=manifest["objective"],
        authority=AuthorityContract(
            repository_id=manifest["repository_id"],
            repository_path=str(repo),
            base_revision=base,
            source_kind="WORKING_MIRROR",
            mutation_authorized=True,
        ),
        allowed_paths=allowed_paths,
        required_suites=("replay.pytest.v0",),
        auto_next=False,
    )

    with tempfile.TemporaryDirectory(prefix="mkm-dogfood-replay-") as tmp:
        temp = Path(tmp)
        ledger = EventLedger(temp / "state" / "ledger.sqlite3")
        runner = DogfoodRunner(
            ledger=ledger,
            worktree_root=temp / "worktrees",
            shared_status_dir=temp / "shared",
        )
        started = runner.start(
            task,
            cohort=manifest["cohort"],
            measurement_mode="REPLAY",
        )
        worker = CommitRangeReplayWorker(
            worker_id=f"replay:{manifest['task_id']}",
            repo=repo,
            base_revision=base,
            result_revision=result_revision,
            allowed_paths=allowed_paths,
        )
        worker_result = runner.orchestrator.dispatch(
            task,
            runner.orchestrator.worktrees.plan(task),
            worker,
        )
        runner.orchestrator.record_builder_evidence(
            worker_result,
            suite_id="replay.patch.apply.v0",
            suite_digest=worker.patch_sha256,
            outcome=EvidenceOutcome.PASS,
            detail={
                "classification": "BUILDER_SELF_REPORT",
                "replayed_result_revision": result_revision,
            },
        )

        worktree = Path(started["workspace"]["worktree_path"])
        argv = [
            sys.executable,
            "-B",
            "-m",
            "pytest",
            *suite_paths,
            "-q",
            "-p",
            "no:cacheprovider",
        ]
        suite_digest = sha256_bytes(
            json.dumps(argv, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        )
        t0 = time.monotonic()
        cp = run(worktree, argv, check=False)
        duration_ms = int((time.monotonic() - t0) * 1000)

        observed = observe_workspace(worktree)
        validator = IndependentValidatorContract(ledger)
        evidence = validator.record_test_result(
            task_id=task.task_id,
            validator_id=f"validator:{manifest['task_id']}",
            suite_id="replay.pytest.v0",
            suite_digest=suite_digest,
            subject_digest=observed["subject_digest"],
            returncode=cp.returncode,
            stdout_sha256=sha256_bytes(cp.stdout),
            stderr_sha256=sha256_bytes(cp.stderr),
            duration_ms=duration_ms,
        )
        finalized = runner.finalize(
            task.task_id,
            DogfoodMeasurementV0(
                task_id=task.task_id,
                cohort=manifest["cohort"],
                measurement_mode="REPLAY",
                review_minutes=0,
                human_interventions=0,
                worker_cost_usd=0,
            ),
        )

        payload = {
            "schema": "mkm_actual_change_replay_dogfood_v0",
            "manifest": manifest,
            "base_revision_verified": base,
            "result_revision_verified": result_revision,
            "worker_result": {
                "status": worker_result.status,
                "subject_digest": worker_result.subject_digest,
                "changed_files": list(worker_result.changed_files),
                "patch_sha256": worker.patch_sha256,
            },
            "validator": {
                "returncode": cp.returncode,
                "outcome": evidence.outcome.value,
                "freshness": evidence.freshness.value,
                "duration_ms": duration_ms,
            },
            "finalized": finalized,
            "ledger_integrity": ledger.verify_chain(),
        }

        checks = [
            cp.returncode == 0,
            evidence.outcome.value == "PASS",
            finalized["task_state"] == "CANDIDATE",
            finalized["gate_decision"] == "HUMAN_GATE",
            finalized["measurement_mode"] == "REPLAY",
            finalized["dogfood_summary"]["prospective_measurement_count"] == 0,
            finalized["dogfood_summary"]["replay_measurement_count"] == 1,
            finalized["merge_authorization"] == "NO",
            finalized["deployment_authorization"] == "NO",
            finalized["send_gate"] == "HOLD",
            payload["ledger_integrity"]["valid"] is True,
        ]
        payload["semantic_success"] = all(checks)
        out = Path(args.out).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if payload["semantic_success"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
