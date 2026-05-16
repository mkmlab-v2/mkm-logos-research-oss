#!/usr/bin/env python3
"""Compression Shadow Auditor — artifact contract + loss-pattern queue (B-track).

Runs pytest on ultra compression artifacts, reads frozen KPI/loss reports, and
appends research debug rows to a JSONL queue. Does not auto-promote to Track A.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.report_multilens_performance_eval import ULTRA_TOKEN_SAVING_POLICY_MIN

KPI_SUMMARY = ROOT / "reports" / "constitution" / "btrack_pilot" / "ultra_compression_kpi_summary_latest.json"
ACTIVE_REPORT = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
LOSS_PATTERNS = ROOT / "reports" / "constitution" / "btrack_pilot" / "compression_jaccard_loss_patterns_latest.json"
OUT_LATEST = ROOT / "reports" / "constitution" / "btrack_pilot" / "compression_shadow_auditor_latest.json"
OUT_LOG = ROOT / "reports" / "constitution" / "btrack_pilot" / "compression_shadow_auditor_log.jsonl"
DEBUG_QUEUE = ROOT / "reports" / "constitution" / "btrack_pilot" / "compression_research_metaphor_debug_queue.jsonl"
PYTEST_TARGET = "tests/test_ultra_compression_artifacts.py"
LOSS_SCRIPT = ROOT / "scripts" / "report_compression_jaccard_loss_patterns.py"
BENCH_SCRIPT = ROOT / "scripts" / "run_ultra_compression_default.py"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _queue_row(
    *,
    reason: str,
    severity: str,
    case_id: str | None = None,
    domain: str | None = None,
    shard_id: str | None = None,
    metrics: dict[str, Any] | None = None,
    evidence_paths: list[str] | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    return {
        "schema": "compression_research_metaphor_debug_queue_v1",
        "ts_utc": _now_iso(),
        "reason": reason,
        "severity": severity,
        "case_id": case_id,
        "domain": domain,
        "shard_id": shard_id,
        "metrics": metrics or {},
        "evidence_paths": evidence_paths or [],
        "note": note,
        "hypothesis_tier": "B",
        "track_wall": "b_track_research_only",
        "research_metaphor_domain": "research_metaphor_compression_fidelity_gate",
    }


def _run_pytest(quiet: bool) -> tuple[int, str]:
    cmd = [sys.executable, "-m", "pytest", PYTEST_TARGET, "-q", "--tb=line"]
    proc = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    tail = (proc.stdout or "") + (proc.stderr or "")
    if not quiet:
        print(tail.strip())
    return proc.returncode, tail[-4000:]


def _run_script(script: Path, extra: list[str], quiet: bool) -> int:
    cmd = [sys.executable, str(script), *extra]
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    if not quiet and proc.stdout:
        print(proc.stdout.strip())
    if proc.returncode != 0 and proc.stderr:
        print(proc.stderr.strip(), file=sys.stderr)
    return proc.returncode


def _scan_active_report(
    active: dict[str, Any],
    *,
    jaccard_warn_below: float,
    jaccard_critical_below: float,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    cases = (active.get("compression_metrics") or {}).get("cases") or []
    for row in cases:
        if not isinstance(row, dict):
            continue
        cid = str(row.get("id", ""))
        jac = float(row.get("reconstruction_fidelity_jaccard", 0.0))
        route = row.get("route") if isinstance(row.get("route"), dict) else {}
        domain = route.get("domain")
        shard_id = route.get("shard_id")
        if jac < jaccard_critical_below:
            sev = "critical"
            reason = "jaccard_critical_below"
        elif jac < jaccard_warn_below:
            sev = "warn"
            reason = "jaccard_below_warn_threshold"
        else:
            continue
        rows.append(
            _queue_row(
                reason=reason,
                severity=sev,
                case_id=cid,
                domain=str(domain) if domain is not None else None,
                shard_id=str(shard_id) if shard_id is not None else None,
                metrics={
                    "reconstruction_fidelity_jaccard": jac,
                    "token_saving_rate": row.get("token_saving_rate"),
                },
                evidence_paths=[_rel(ACTIVE_REPORT)],
            )
        )
    return rows


def _scan_kpi(kpi: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    active = kpi.get("active_kpi") or {}
    if not bool(active.get("ultra_saving_policy_ok")):
        rows.append(
            _queue_row(
                reason="ultra_saving_policy_fail",
                severity="critical",
                metrics={
                    "global_token_saving_rate": active.get("global_token_saving_rate"),
                    "ultra_saving_policy_min": active.get("ultra_saving_policy_min", ULTRA_TOKEN_SAVING_POLICY_MIN),
                    "ultra_saving_policy_ok": active.get("ultra_saving_policy_ok"),
                },
                evidence_paths=[_rel(KPI_SUMMARY)],
            )
        )
    if not bool(active.get("sensitive_integrity_ok")):
        rows.append(
            _queue_row(
                reason="sensitive_integrity_fail",
                severity="critical",
                metrics={"avg_sensitive_integrity": active.get("avg_sensitive_integrity")},
                evidence_paths=[_rel(KPI_SUMMARY)],
            )
        )
    if not bool(active.get("jaccard_guardrail_ok")):
        rows.append(
            _queue_row(
                reason="jaccard_guardrail_fail",
                severity="warn",
                metrics={
                    "avg_reconstruction_fidelity_jaccard": active.get("avg_reconstruction_fidelity_jaccard"),
                    "jaccard_drop_pp": active.get("jaccard_drop_pp"),
                },
                evidence_paths=[_rel(KPI_SUMMARY)],
            )
        )
    return rows


def _scan_loss_worst(loss: dict[str, Any], *, top_n: int) -> list[dict[str, Any]]:
    cases = list(loss.get("cases") or [])
    ranked = sorted(
        cases,
        key=lambda r: (
            float(r.get("reconstruction_fidelity_jaccard", 1.0)),
            -int(r.get("words_lost_count", 0)),
        ),
    )
    rows: list[dict[str, Any]] = []
    for row in ranked[:top_n]:
        jac = float(row.get("reconstruction_fidelity_jaccard", 1.0))
        rows.append(
            _queue_row(
                reason="loss_pattern_worst_case",
                severity="info",
                case_id=str(row.get("id", "")),
                domain=str(row.get("domain")) if row.get("domain") is not None else None,
                shard_id=str(row.get("shard_id")) if row.get("shard_id") is not None else None,
                metrics={
                    "reconstruction_fidelity_jaccard": jac,
                    "words_lost_count": row.get("words_lost_count"),
                    "token_saving_rate": row.get("token_saving_rate"),
                },
                evidence_paths=[_rel(LOSS_PATTERNS)],
                note="ranked worst by jaccard then words_lost",
            )
        )
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description="Compression Shadow Auditor (RQ-018).")
    ap.add_argument("--jaccard-warn-below", type=float, default=0.70)
    ap.add_argument("--jaccard-critical-below", type=float, default=0.50)
    ap.add_argument("--loss-worst-top-n", type=int, default=5)
    ap.add_argument("--skip-pytest", action="store_true")
    ap.add_argument("--refresh-loss-patterns", action="store_true")
    ap.add_argument("--refresh-bench", action="store_true", help="Run run_ultra_compression_default before audit.")
    ap.add_argument("--dry-run", action="store_true", help="Do not append debug queue rows.")
    ap.add_argument("--stdout-only", action="store_true", help="Print summary JSON to stdout only.")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--out-json", type=Path, default=OUT_LATEST)
    ap.add_argument("--queue-jsonl", type=Path, default=DEBUG_QUEUE)
    args = ap.parse_args()

    if args.refresh_bench:
        code = _run_script(BENCH_SCRIPT, [], args.quiet)
        if code != 0:
            return 2

    if args.refresh_loss_patterns or not LOSS_PATTERNS.is_file():
        code = _run_script(LOSS_SCRIPT, ["--sla-track", "universal"], args.quiet)
        if code != 0:
            return 2

    pytest_rc = 0
    pytest_tail = ""
    pytest_quiet = args.quiet or args.stdout_only
    if not args.skip_pytest:
        pytest_rc, pytest_tail = _run_pytest(pytest_quiet)
        if pytest_rc != 0:
            if not args.dry_run:
                _append_jsonl(
                    args.queue_jsonl,
                    _queue_row(
                        reason="pytest_ultra_compression_artifacts_fail",
                        severity="critical",
                        metrics={"pytest_exit_code": pytest_rc},
                        evidence_paths=[PYTEST_TARGET],
                        note=pytest_tail[-500:] if pytest_tail else None,
                    ),
                )

    queue_new: list[dict[str, Any]] = []
    missing: list[str] = []

    if KPI_SUMMARY.is_file():
        queue_new.extend(_scan_kpi(_read_json(KPI_SUMMARY)))
    else:
        missing.append(_rel(KPI_SUMMARY))

    if ACTIVE_REPORT.is_file():
        queue_new.extend(
            _scan_active_report(
                _read_json(ACTIVE_REPORT),
                jaccard_warn_below=float(args.jaccard_warn_below),
                jaccard_critical_below=float(args.jaccard_critical_below),
            )
        )
    else:
        missing.append(_rel(ACTIVE_REPORT))

    if LOSS_PATTERNS.is_file():
        queue_new.extend(_scan_loss_worst(_read_json(LOSS_PATTERNS), top_n=max(0, int(args.loss_worst_top_n))))
    else:
        missing.append(_rel(LOSS_PATTERNS))

    if missing and not args.dry_run:
        _append_jsonl(
            args.queue_jsonl,
            _queue_row(
                reason="missing_artifact",
                severity="warn",
                metrics={"missing_paths": missing},
                note="re-run with --refresh-bench or weekly governance chain",
            ),
        )

    if not args.dry_run:
        for row in queue_new:
            _append_jsonl(args.queue_jsonl, row)

    critical = sum(1 for r in queue_new if r.get("severity") == "critical")
    warn = sum(1 for r in queue_new if r.get("severity") == "warn")
    if pytest_rc != 0:
        critical += 1

    audit_ok = pytest_rc == 0 and critical == 0 and not missing
    exit_code = 0 if audit_ok else (2 if critical > 0 or pytest_rc != 0 else 1)

    summary = {
        "schema": "compression_shadow_auditor_v1",
        "ts_utc": _now_iso(),
        "audit_ok": audit_ok,
        "exit_code": exit_code,
        "pytest": {"exit_code": pytest_rc, "target": PYTEST_TARGET},
        "policy_floor_min": ULTRA_TOKEN_SAVING_POLICY_MIN,
        "thresholds": {
            "jaccard_warn_below": float(args.jaccard_warn_below),
            "jaccard_critical_below": float(args.jaccard_critical_below),
            "loss_worst_top_n": int(args.loss_worst_top_n),
        },
        "sources": {
            "kpi_summary": _rel(KPI_SUMMARY) if KPI_SUMMARY.is_file() else None,
            "active_report": _rel(ACTIVE_REPORT) if ACTIVE_REPORT.is_file() else None,
            "loss_patterns": _rel(LOSS_PATTERNS) if LOSS_PATTERNS.is_file() else None,
        },
        "queue": {
            "appended_count": 0 if args.dry_run else len(queue_new) + (1 if pytest_rc != 0 and not args.skip_pytest else 0),
            "critical_count": critical,
            "warn_count": warn,
            "path": _rel(args.queue_jsonl),
        },
        "missing_artifacts": missing,
        "dry_run": bool(args.dry_run),
    }

    if not args.stdout_only:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        _append_jsonl(
            OUT_LOG,
            {
                "schema": "compression_shadow_auditor_log_v1",
                "ts_utc": summary["ts_utc"],
                "exit_code": exit_code,
                "audit_ok": audit_ok,
                "out_json": _rel(args.out_json),
            },
        )
        if not args.quiet:
            print(f"WROTE: {args.out_json}")
            if not args.dry_run:
                print(f"QUEUE: {args.queue_jsonl} (+{summary['queue']['appended_count']} rows)")

    if args.stdout_only:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    elif not args.quiet:
        print(json.dumps({"audit_ok": audit_ok, "exit_code": exit_code}, ensure_ascii=False))

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
