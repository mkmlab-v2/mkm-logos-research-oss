#!/usr/bin/env python3
"""MKM-Orchestrator bounded automation poll (todo_queue_v1)."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from shutil import which


def _process_exists(pid: int) -> bool:
    if pid <= 0:
        return False
    if sys.platform == "win32":
        try:
            out = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            return str(pid) in (out.stdout or "")
        except OSError:
            return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _audit(workspace_root: Path, event: str, task_id: str = "", **detail: object) -> None:
    reports = workspace_root / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    log_path = reports / "mkm_orchestrator_audit.jsonl"
    row = {
        "schema": "mkm_orchestrator_audit_v1",
        "ts_utc": _utc_now(),
        "event": event,
        "workspace_root": str(workspace_root),
    }
    if task_id:
        row["task_id"] = task_id
    row.update({k: v for k, v in detail.items() if v is not None})
    with log_path.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(row, ensure_ascii=False) + "\n")


def _approval_required(task: dict) -> bool:
    if task.get("sensitivity_level") == "high":
        return True
    appr = task.get("approval") or {}
    return appr.get("required") is True


def _write_queue(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    path.write_text(text, encoding="utf-8")


def _write_approval_backlog_snapshot(workspace_root: Path, data: dict) -> None:
    """One-glance file for HITL batching: awaiting_approval + pending tasks that need approval."""
    reports = workspace_root / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    out = reports / "mkm_orchestrator_approval_backlog_latest.json"
    backlog: list[dict] = []
    for t in data.get("tasks") or []:
        state = t.get("state", "")
        tid = t.get("task_id", "")
        appr = t.get("approval") or {}
        approved = appr.get("resolution") == "approved"
        need = _approval_required(t)
        if approved:
            continue
        if state == "awaiting_approval":
            backlog.append(
                {
                    "task_id": tid,
                    "title": t.get("title", ""),
                    "state": state,
                    "sensitivity_level": t.get("sensitivity_level", ""),
                    "idempotency_key": appr.get("idempotency_key", ""),
                    "prompt_sent_at_utc": appr.get("prompt_sent_at_utc", ""),
                }
            )
        elif state == "pending" and need:
            backlog.append(
                {
                    "task_id": tid,
                    "title": t.get("title", ""),
                    "state": "pending_needs_approval",
                    "sensitivity_level": t.get("sensitivity_level", ""),
                    "idempotency_key": appr.get("idempotency_key", ""),
                    "note": "Not yet promoted; next poll will set awaiting_approval",
                }
            )
    doc = {
        "schema_version": "mkm_orchestrator_approval_backlog_v1",
        "generated_at_utc": _utc_now(),
        "queue_generated_at_utc": data.get("generated_at_utc"),
        "pending_approval": backlog,
    }
    out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _notify_telegram_hitl(
    workspace_root: Path, task_id: str, title: str, idempotency_key: str
) -> None:
    """Subprocess: optional Telegram prompt (MKM_ORCHESTRATOR_TELEGRAM_NOTIFY=1 + TELEGRAM_*)."""
    script = workspace_root / "scripts" / "mkm_orchestrator_telegram_v1.py"
    if not script.is_file():
        return
    try:
        r = subprocess.run(
            [
                sys.executable,
                str(script),
                "notify",
                "--workspace-root",
                str(workspace_root),
                "--task-id",
                task_id,
                "--title",
                title,
                "--idempotency-key",
                idempotency_key,
            ],
            cwd=str(workspace_root),
            timeout=45,
            capture_output=True,
            text=True,
        )
        if r.returncode != 0 and (r.stdout or r.stderr):
            _audit(
                workspace_root,
                "telegram_notify_subprocess_nonzero",
                task_id=task_id,
                stderr=(r.stderr or r.stdout or "")[:300],
            )
    except subprocess.TimeoutExpired:
        _audit(workspace_root, "telegram_notify_timeout", task_id=task_id)
    except OSError as exc:
        _audit(workspace_root, "telegram_notify_os_error", task_id=task_id, error=str(exc)[:200])


def _run_process(
    workspace_root: Path,
    runner_kind: str,
    path_rel: str,
    args: list[str],
    timeout_sec: int,
) -> int:
    script_path = (workspace_root / path_rel.replace("/", os.sep)).resolve()
    if not script_path.is_file():
        return 127

    if runner_kind == "powershell":
        if not path_rel:
            return 127
        cmd = [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script_path),
            *args,
        ]
    elif runner_kind == "python":
        if not path_rel:
            return 127
        exe = which("py") or which("py.exe") or which("python")
        if not exe:
            return 126
        cmd = [exe, str(script_path), *args]
    elif runner_kind == "cursor_cli":
        exe = which("cursor") or which("cursor.exe") or which("cursor.cmd")
        if not exe:
            return 126
        cmd = [exe, "agent", *args]
    else:
        return 126

    try:
        r = subprocess.run(
            cmd,
            cwd=str(workspace_root),
            timeout=timeout_sec,
            capture_output=False,
        )
        return int(r.returncode)
    except subprocess.TimeoutExpired:
        return 124


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace-root", type=Path, default=Path("C:/workspace"))
    parser.add_argument(
        "--queue",
        type=Path,
        default=None,
        help="Queue JSON (default: docs/final/artifacts/todo_queue_latest.json)",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max-tasks", type=int, default=1)
    parser.add_argument("--skip-lock", action="store_true")
    parser.add_argument(
        "--skip-heavy",
        action="store_true",
        help="Skip runtime_class=heavy tasks in this invocation.",
    )
    parser.add_argument(
        "--heavy-only",
        action="store_true",
        help="Run only runtime_class=heavy tasks (implies allow-heavy).",
    )
    parser.add_argument(
        "--no-approval-snapshot",
        action="store_true",
        help="Do not write reports/mkm_orchestrator_approval_backlog_latest.json",
    )
    args = parser.parse_args()

    workspace_root = args.workspace_root.resolve()
    queue_path = args.queue
    if queue_path is None:
        queue_path = workspace_root / "docs" / "final" / "artifacts" / "todo_queue_latest.json"
    else:
        queue_path = queue_path.resolve()

    lock_path = workspace_root / "reports" / "mkm_orchestrator_poll.lock"

    if not args.skip_lock:
        if lock_path.is_file():
            try:
                old_pid = int(lock_path.read_text(encoding="utf-8").strip())
                if old_pid > 0 and _process_exists(old_pid):
                    _audit(workspace_root, "lock_held", pid=old_pid)
                    print(f"[orchestrator] Lock held by PID {old_pid}. Exit 0.")
                    return 0
            except (ValueError, OSError):
                pass
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock_path.write_text(str(os.getpid()), encoding="utf-8")

    try:
        _audit(workspace_root, "poll_start")

        if not queue_path.is_file():
            _audit(workspace_root, "queue_missing", queue_path=str(queue_path))
            print(f"[orchestrator] Queue file missing: {queue_path}")
            print("Copy docs/final/artifacts/todo_queue_example_v1.json or pass --queue.")
            return 1

        data = json.loads(queue_path.read_text(encoding="utf-8"))
        if data.get("schema_version") != "todo_queue_v1":
            _audit(workspace_root, "queue_schema_mismatch", got=data.get("schema_version"))
            print("ERROR: schema_version must be todo_queue_v1", file=sys.stderr)
            return 1

        tasks: list[dict] = data.get("tasks") or []
        ran = 0

        for task in tasks:
            if ran >= args.max_tasks:
                break

            tid = task.get("task_id", "")
            state = task.get("state", "")
            runtime_class = str(task.get("runtime_class") or "quick")

            if args.heavy_only and runtime_class != "heavy":
                continue
            if runtime_class == "heavy" and args.skip_heavy and not args.heavy_only:
                _audit(workspace_root, "heavy_task_skipped", task_id=tid)
                continue

            if state in ("done", "cancelled", "failed"):
                continue
            if state == "running":
                _audit(
                    workspace_root,
                    "stale_running_skip",
                    task_id=tid,
                    note="Fix queue manually if stuck",
                )
                continue

            need_app = _approval_required(task)
            appr = task.setdefault("approval", {})
            approved = appr.get("resolution") == "approved"

            if state == "awaiting_approval" and not approved:
                continue

            # pending + needs approval + not approved -> promote
            if state == "pending" and need_app and not approved:
                _audit(
                    workspace_root,
                    "dry_run_needs_approval" if args.dry_run else "needs_approval",
                    task_id=tid,
                )
                print(
                    f"[orchestrator] Task {tid} needs HITL. "
                    f"py scripts/approve_mkm_orchestrator_task_v1.py --task-id {tid} | "
                    f"batch: same script --batch-approve"
                )
                if args.dry_run:
                    # Do not increment ran: same as real run (promote does not count as an execution)
                    continue
                appr["required"] = True
                appr.setdefault("idempotency_key", f"{tid}-v1")
                task["state"] = "awaiting_approval"
                ts = _utc_now()
                appr.setdefault("prompt_sent_at_utc", ts)
                task["updated_at_utc"] = ts
                data["generated_at_utc"] = ts
                _write_queue(queue_path, data)
                _notify_telegram_hitl(
                    workspace_root,
                    tid,
                    str(task.get("title") or tid),
                    str(appr.get("idempotency_key") or f"{tid}-v1"),
                )
                continue

            can_run = False
            if state == "pending" and not need_app:
                can_run = True
            elif state == "pending" and need_app and approved:
                can_run = True
            elif state == "awaiting_approval" and approved:
                can_run = True

            if not can_run:
                continue

            runner = task.get("runner") or {}
            kind = runner.get("kind", "")
            path_rel = runner.get("path_rel", "")
            rargs = list(runner.get("args") or [])
            timeout_sec = int(runner.get("timeout_seconds") or 3600)
            run_kind = kind
            run_path_rel = path_rel
            run_args = rargs
            run_timeout_sec = timeout_sec
            fallback_kind = kind
            fallback_path_rel = path_rel
            fallback_args = rargs
            fallback_timeout_sec = timeout_sec
            auto_cursor_selected = False

            if runtime_class == "heavy" and runner.get("use_cursor_cli_auto") is True:
                cargs = list(runner.get("cursor_cli_args") or [])
                ctimeout = int(runner.get("cursor_timeout_seconds") or timeout_sec)
                cexe = which("cursor") or which("cursor.exe") or which("cursor.cmd")
                if cargs and cexe:
                    run_kind = "cursor_cli"
                    run_path_rel = ""
                    run_args = cargs
                    run_timeout_sec = ctimeout
                    auto_cursor_selected = True
                    _audit(workspace_root, "cursor_cli_auto_selected", task_id=tid)
                else:
                    _audit(
                        workspace_root,
                        "cursor_cli_auto_skipped",
                        task_id=tid,
                        note="missing cursor executable or cursor_cli_args",
                    )

            full_path = (workspace_root / path_rel.replace("/", os.sep)).resolve()
            if run_kind != "cursor_cli" and not full_path.is_file():
                _audit(workspace_root, "task_runner_missing", task_id=tid, path=str(full_path))
                task["state"] = "failed"
                ts = _utc_now()
                task["updated_at_utc"] = ts
                data["generated_at_utc"] = ts
                lr = task.setdefault("last_run", {})
                lr["finished_at_utc"] = ts
                lr["exit_code"] = 127
                _write_queue(queue_path, data)
                continue

            if args.dry_run:
                _audit(
                    workspace_root,
                    "dry_run_would_run",
                    task_id=tid,
                    runner=run_kind,
                    path=run_path_rel,
                )
                target = "<cursor agent>" if run_kind == "cursor_cli" else str(full_path)
                print(f"[orchestrator] DRY-RUN would run {tid} [{run_kind}] -> {target}")
                ran += 1
                continue

            ts = _utc_now()
            task["state"] = "running"
            task["updated_at_utc"] = ts
            data["generated_at_utc"] = ts
            lr = task.setdefault("last_run", {})
            lr["started_at_utc"] = ts
            _write_queue(queue_path, data)

            _audit(workspace_root, "task_run_start", task_id=tid, path_rel=run_path_rel, runner=run_kind)

            exit_code = _run_process(workspace_root, run_kind, run_path_rel, run_args, run_timeout_sec)
            final_runner = run_kind

            if (
                auto_cursor_selected
                and exit_code != 0
                and fallback_kind in ("python", "powershell")
            ):
                fallback_path = (workspace_root / fallback_path_rel.replace("/", os.sep)).resolve()
                if fallback_path.is_file():
                    _audit(
                        workspace_root,
                        "cursor_cli_auto_fallback_start",
                        task_id=tid,
                        original_exit_code=exit_code,
                        fallback_runner=fallback_kind,
                    )
                    fallback_code = _run_process(
                        workspace_root, fallback_kind, fallback_path_rel, fallback_args, fallback_timeout_sec
                    )
                    _audit(
                        workspace_root,
                        "cursor_cli_auto_fallback_end",
                        task_id=tid,
                        fallback_exit_code=fallback_code,
                    )
                    exit_code = fallback_code
                    final_runner = fallback_kind

            if exit_code == 124:
                _audit(workspace_root, "task_timeout", task_id=tid, timeout_seconds=run_timeout_sec)

            end_ts = _utc_now()
            lr["finished_at_utc"] = end_ts
            lr["exit_code"] = exit_code
            task["updated_at_utc"] = end_ts
            data["generated_at_utc"] = end_ts
            task["state"] = "done" if exit_code == 0 else "failed"
            _write_queue(queue_path, data)

            _audit(workspace_root, "task_run_end", task_id=tid, exit_code=exit_code, runner=final_runner)
            ran += 1

        if not args.no_approval_snapshot:
            try:
                _write_approval_backlog_snapshot(workspace_root, data)
            except OSError:
                pass

        if ran == 0:
            _audit(workspace_root, "no_eligible_task")

        return 0
    finally:
        if not args.skip_lock and lock_path.is_file():
            try:
                lock_path.unlink(missing_ok=True)
            except OSError:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
