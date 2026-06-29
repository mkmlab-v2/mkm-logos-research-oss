#!/usr/bin/env python3
"""Apply resolver probe outcomes to PoC cohort + general_prophecy registry (B rail).

Only applies rows with status=resolved_candidate and explicit outcome 0/1.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from layer1_only_brier_bench_poc_lib_v1 import (
    DEFAULT_COHORT,
    DEFAULT_MAP,
    DEFAULT_REGISTRY,
    load_cohort,
    load_registry_map,
    utc_now,
    validate_registry,
)

ROOT = Path(__file__).resolve().parents[1]
RESOLVE_SCRIPT = ROOT / "scripts" / "resolve_general_prophecy_question_v1.py"
DEFAULT_PROBE = ROOT / "reports" / "layer1_only_brier_bench_resolver_probe_v1_latest.json"


def _apply_poc_resolution(cohort_path: Path, *, question_id: str, outcome: int) -> None:
    doc = json.loads(cohort_path.read_text(encoding="utf-8"))
    for row in doc.get("forecasts") or []:
        if row.get("question_id") == question_id:
            row["status"] = "resolved"
            row["outcome"] = outcome
            row["resolved_at_utc"] = utc_now()
            break
    else:
        raise ValueError(f"poc question not found: {question_id}")
    cohort_path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _apply_registry_resolution(
    *,
    registry_path: Path,
    registry_question_id: str,
    outcome: int,
    evidence_uri: str | None,
    notes: str,
) -> None:
    tmp_out = registry_path.with_suffix(".resolved.tmp.json")
    cmd = [
        sys.executable,
        str(RESOLVE_SCRIPT),
        "-i",
        str(registry_path),
        "-o",
        str(tmp_out),
        "--question-id",
        registry_question_id,
        "--outcome",
        "true" if outcome == 1 else "false",
        "--notes",
        notes,
    ]
    if evidence_uri:
        cmd.extend(["--evidence-uri", evidence_uri])
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or proc.stdout or "resolve script failed")
    doc = json.loads(tmp_out.read_text(encoding="utf-8"))
    validate_registry(doc)
    tmp_out.replace(registry_path)


def sync_resolutions(
    *,
    probe_path: Path,
    cohort_path: Path,
    map_path: Path,
    registry_path: Path,
    dry_run: bool,
) -> dict[str, Any]:
    load_cohort(cohort_path)
    mapping = load_registry_map(map_path)
    probe = json.loads(probe_path.read_text(encoding="utf-8"))
    if probe.get("schema") != "layer1_only_brier_bench_resolver_probe_v1":
        raise ValueError("probe schema mismatch")

    applied: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for p in probe.get("probes") or []:
        if not isinstance(p, dict):
            continue
        qid = p.get("question_id")
        if p.get("status") != "resolved_candidate" or p.get("outcome") not in (0, 1):
            skipped.append({"question_id": qid, "status": p.get("status")})
            continue
        meta = mapping.get(str(qid))
        if meta is None:
            raise ValueError(f"no map for {qid}")
        reg_id = str(meta["registry_question_id"])
        outcome = int(p["outcome"])
        evidence = p.get("evidence_uri") if isinstance(p.get("evidence_uri"), str) else None
        notes = "layer1_only_brier_bench_poc_v1 automated resolver probe"
        if not dry_run:
            _apply_registry_resolution(
                registry_path=registry_path,
                registry_question_id=reg_id,
                outcome=outcome,
                evidence_uri=evidence,
                notes=notes,
            )
            _apply_poc_resolution(cohort_path, question_id=str(qid), outcome=outcome)
        applied.append({"poc_question_id": qid, "registry_question_id": reg_id, "outcome": outcome})

    return {
        "schema": "layer1_only_brier_bench_resolution_sync_v1",
        "generated_at_utc": utc_now(),
        "dry_run": dry_run,
        "applied": applied,
        "skipped": skipped,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--probe", type=Path, default=DEFAULT_PROBE)
    ap.add_argument("--cohort", type=Path, default=DEFAULT_COHORT)
    ap.add_argument("--map", type=Path, default=DEFAULT_MAP)
    ap.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    ap.add_argument("--output", type=Path, default=ROOT / "reports" / "layer1_only_brier_bench_resolution_sync_v1_latest.json")
    ap.add_argument("--dry-run", action="store_true")
    ns = ap.parse_args()

    for path in (ns.probe, ns.cohort, ns.map, ns.registry):
        if not path.is_file():
            print(f"missing: {path}", file=sys.stderr)
            return 2

    try:
        report = sync_resolutions(
            probe_path=ns.probe,
            cohort_path=ns.cohort,
            map_path=ns.map,
            registry_path=ns.registry,
            dry_run=ns.dry_run,
        )
    except (ValueError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    ns.output.parent.mkdir(parents=True, exist_ok=True)
    ns.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
