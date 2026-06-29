#!/usr/bin/env python3
"""Run LTM Research sandbox cycle — Research → Ingest → Produce ([HYPO] / B-track).

Never auto-edits CONCEPT_SPECS or promotes to Track A·live.

  py scripts/run_ltm_research_sandbox_cycle_v1.py --seed-id sandbox_20260613_demo --dry-run
  py scripts/run_ltm_research_sandbox_cycle_v1.py --seed-id sandbox_20260613_demo \\
    --concept-draft-json reports/ltm_research_produce_drafts/example.json \\
    --human-signoff-json reports/ltm_research_sandbox_human_signoff_latest.json
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_ROOT / "scripts"))

from check_ltm_index_filter_v1 import path_allowed_by_filter  # noqa: E402

GRAPH_SCHEMA = "ltm_research_sandbox_cycle_v1"
DEFAULT_CONTRACT = SCRIPT_ROOT / "docs/final/artifacts/ltm_research_sandbox_cycle_contract_v1.json"
DEFAULT_OUT = SCRIPT_ROOT / "reports/ltm_research_sandbox_cycle_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _run_step(step_id: str, cmd: list[str], *, cwd: Path) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return {
        "step_id": step_id,
        "command": cmd,
        "exit_code": proc.returncode,
        "stdout_tail": (proc.stdout or "")[-2000:],
        "stderr_tail": (proc.stderr or "")[-2000:],
        "ok": proc.returncode == 0,
    }


def _norm_path(path: str) -> str:
    return PurePosixPath(path.replace("\\", "/")).as_posix()


def _path_allowed(path: str, contract: dict[str, Any]) -> bool:
    del contract  # kill matrix uses filter SSOT for coordinate paths
    filt_path = SCRIPT_ROOT / "docs/final/artifacts/ltm_index_filter_v1.json"
    if not filt_path.is_file():
        return True
    filt = _load_json(filt_path)
    return path_allowed_by_filter(_norm_path(path), filt)


def _validate_seed_id(seed_id: str) -> list[str]:
    errors: list[str] = []
    if not re.match(r"^sandbox_\d{8}_[a-z0-9_]+$", seed_id):
        errors.append(
            "seed_id must match sandbox_YYYYMMDD_<topic_slug> (lowercase slug)"
        )
    return errors


def _validate_concept_draft(draft: dict[str, Any], contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if draft.get("schema") != "ltm_research_concept_draft_v1":
        errors.append("concept draft schema must be ltm_research_concept_draft_v1")
    for key in contract.get("kill_matrix", {}).get("required_draft_fields") or []:
        if key not in draft:
            errors.append(f"concept draft missing field: {key}")
    if draft.get("research_only") is not True:
        errors.append("concept draft research_only must be true")
    blob = json.dumps(draft, ensure_ascii=False).lower()
    for forbidden in contract.get("kill_matrix", {}).get("forbidden_draft_substrings") or []:
        if forbidden.lower() in blob:
            errors.append(f"concept draft forbidden substring: {forbidden}")
    fp = str(draft.get("coordinate_file_path") or "")
    if fp and not _path_allowed(fp, contract):
        errors.append(f"concept draft coordinate not allowed by ltm_index_filter: {fp}")
    promo = str(draft.get("promotion_target") or "")
    for bad in contract.get("kill_matrix", {}).get("forbidden_promotion_targets") or []:
        if bad.lower() in promo.lower():
            errors.append(f"forbidden promotion_target contains {bad!r}")
    return errors


def _load_contract(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"contract missing: {path}")
    doc = _load_json(path)
    if doc.get("schema") != "ltm_research_sandbox_cycle_contract_v1":
        raise ValueError("invalid contract schema")
    return doc


def _human_signoff_ok(path: Path) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if not path.is_file():
        return False, [f"human signoff missing: {path}"]
    doc = _load_json(path)
    if doc.get("schema") != "ltm_research_sandbox_human_signoff_v1":
        errors.append("human signoff schema mismatch")
    if doc.get("approved") is not True:
        errors.append("human signoff approved != true")
    if doc.get("acknowledge_ltm_graph_append") is not True:
        errors.append("human signoff acknowledge_ltm_graph_append != true")
    scope = doc.get("scope") if isinstance(doc.get("scope"), dict) else {}
    for key in ("track_a_merge", "live_trading", "auto_promote", "auto_edit_concept_specs"):
        if scope.get(key) is True:
            errors.append(f"human signoff scope forbids {key}=true")
    return len(errors) == 0, errors


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seed-id", required=True)
    ap.add_argument("--contract-json", type=Path, default=DEFAULT_CONTRACT)
    ap.add_argument("--trace-md", type=Path, default=None, help="Optional approval log markdown path.")
    ap.add_argument("--concept-draft-json", type=Path, default=None)
    ap.add_argument("--human-signoff-json", type=Path, default=None)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Run ingest gates only; skip produce draft write.",
    )
    ap.add_argument(
        "--skip-ingest-subprocess",
        action="store_true",
        help="Skip pytest/build subprocess gates (tests only).",
    )
    args = ap.parse_args()

    try:
        contract = _load_contract(args.contract_json.resolve())
    except (FileNotFoundError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    steps: list[dict[str, Any]] = []
    errors: list[str] = []

    seed_errors = _validate_seed_id(args.seed_id)
    if seed_errors:
        errors.extend(seed_errors)
    steps.append({"step_id": "research_seed_id", "ok": not seed_errors, "errors": seed_errors})

    template = SCRIPT_ROOT / str(contract.get("template_path") or "")
    template_ok = template.is_file()
    if not template_ok:
        errors.append(f"sandbox template missing: {template}")
    steps.append({"step_id": "research_template", "ok": template_ok, "path": str(template)})

    if args.trace_md is not None:
        trace_ok = args.trace_md.is_file()
        if not trace_ok:
            errors.append(f"trace md missing: {args.trace_md}")
        steps.append({"step_id": "research_trace", "ok": trace_ok, "path": str(args.trace_md)})

    if not args.skip_ingest_subprocess:
        for gate in contract.get("ingest_subprocess_gates") or []:
            step_id = str(gate.get("step_id") or "ingest")
            cmd = [str(c) for c in (gate.get("command") or [])]
            if not cmd:
                continue
            result = _run_step(step_id, cmd, cwd=SCRIPT_ROOT)
            steps.append(result)
            if not result["ok"]:
                errors.append(f"{step_id} exit {result['exit_code']}")

    produce_draft_path: str | None = None
    produce_ok = False
    if args.concept_draft_json is not None:
        if not args.concept_draft_json.is_file():
            errors.append(f"concept draft missing: {args.concept_draft_json}")
        else:
            draft = _load_json(args.concept_draft_json)
            draft_errors = _validate_concept_draft(draft, contract)
            steps.append(
                {
                    "step_id": "ingest_concept_draft_kill_matrix",
                    "ok": not draft_errors,
                    "errors": draft_errors,
                }
            )
            if draft_errors:
                errors.extend(draft_errors)
            else:
                signoff_path = args.human_signoff_json
                if signoff_path is None:
                    signoff_path = SCRIPT_ROOT / str(
                        contract.get("human_signoff_latest") or ""
                    )
                ok_signoff, signoff_errors = _human_signoff_ok(signoff_path.resolve())
                steps.append(
                    {
                        "step_id": "produce_human_signoff",
                        "ok": ok_signoff,
                        "path": str(signoff_path),
                        "errors": signoff_errors,
                    }
                )
                if not ok_signoff:
                    errors.extend(signoff_errors)
                elif not args.dry_run:
                    out_dir = SCRIPT_ROOT / str(contract.get("produce_draft_dir") or "reports/ltm_research_produce_drafts")
                    out_dir.mkdir(parents=True, exist_ok=True)
                    out_path = out_dir / f"{args.seed_id}_latest.json"
                    payload = {
                        "schema": "ltm_research_produce_output_v1",
                        "generated_at_utc": _utc_now(),
                        "seed_id": args.seed_id,
                        "research_only": True,
                        "concept_draft": draft,
                        "next_manual_steps": [
                            "Add ConceptSpec to scripts/mkm_long_term_memory_graph_concepts_*_v1.py",
                            "Add TopologySpec to scripts/mkm_long_term_memory_graph_topology_v1.py",
                            "py scripts/build_mkm_long_term_memory_graph_v1.py",
                            "py -m pytest tests/test_mkm_long_term_memory_graph_v1.py -q",
                            "powershell -File scripts/Invoke-MkmOpsMemoryIndexRoutine_v1.ps1 -SkipBench",
                        ],
                        "boundary_ack": contract.get("boundary_ack"),
                    }
                    out_path.write_text(
                        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8",
                    )
                    produce_draft_path = str(out_path.relative_to(SCRIPT_ROOT)).replace("\\", "/")
                    produce_ok = True
                elif args.dry_run:
                    produce_ok = True
                    steps.append(
                        {
                            "step_id": "produce_draft",
                            "ok": True,
                            "skipped": "dry_run",
                        }
                    )

    cycle_ok = len(errors) == 0
    report = {
        "schema": GRAPH_SCHEMA,
        "generated_at_utc": _utc_now(),
        "seed_id": args.seed_id,
        "research_only": True,
        "track": "B",
        "cycle_ok": cycle_ok,
        "produce_ok": produce_ok,
        "dry_run": args.dry_run,
        "ingest_gate": contract.get("ingest_gate"),
        "errors": errors,
        "steps": steps,
        "produce_draft_path": produce_draft_path,
        "contract_path": str(args.contract_json.relative_to(SCRIPT_ROOT)).replace("\\", "/"),
        "boundary_ack": contract.get("boundary_ack"),
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out_json}")
    print(f"cycle_ok={cycle_ok} produce_ok={produce_ok} errors={len(errors)}")
    if errors:
        for err in errors:
            print(f"FAIL: {err}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
