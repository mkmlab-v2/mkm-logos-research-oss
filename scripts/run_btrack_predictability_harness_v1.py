#!/usr/bin/env python3
"""B-track predictability harness: input gate -> Brier/ECE eval -> append-only drift log.

Serializes existing general_prophecy tooling; does not ingest Logos GraphRAG or price lanes.
research_only · no Track A / live trading auto-merge.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IN = ROOT / "docs" / "final" / "artifacts" / "general_prophecy_latest.json"
DEFAULT_BRIER_OUT = ROOT / "docs" / "final" / "artifacts" / "general_prophecy_brier_eval_latest.json"
DEFAULT_HARNESS_OUT = ROOT / "reports" / "btrack_predictability_harness_v1_latest.json"
DEFAULT_DRIFT_LOG = ROOT / "reports" / "general_prophecy_brier_drift_log_v1.jsonl"
HARNESS_SCHEMA = "btrack_predictability_harness_v1"
DRIFT_SCHEMA = "btrack_predictability_brier_drift_v1"

_VALIDATE = ROOT / "scripts" / "validate_general_prophecy_predictability_input_v1.py"
_EVAL = ROOT / "scripts" / "eval_general_prophecy_brier_score.py"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _append_drift_log(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def _run_validate(registry: Path, *, no_jsonschema: bool) -> tuple[int, dict[str, Any]]:
    cmd = [sys.executable, str(_VALIDATE), "-i", str(registry), "--stdout-only"]
    if no_jsonschema:
        cmd.append("--no-jsonschema")
    r = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=120)
    if r.returncode not in (0, 2) or not r.stdout.strip():
        return r.returncode or 1, {
            "gate_pass": False,
            "stderr": (r.stderr or "")[:500],
            "stdout": (r.stdout or "")[:500],
        }
    return r.returncode, json.loads(r.stdout)


def _run_brier(
    registry: Path,
    output: Path,
    *,
    ece_bins: int,
    ece_min_per_tag: int,
) -> tuple[int, dict[str, Any] | None]:
    cmd = [
        sys.executable,
        str(_EVAL),
        "-i",
        str(registry),
        "-o",
        str(output),
        "--no-rows",
        "--no-print-output-path",
    ]
    if ece_bins > 0:
        cmd.extend(["--ece-bins", str(ece_bins), "--ece-min-per-tag", str(ece_min_per_tag)])
    r = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=180)
    if r.returncode != 0:
        return r.returncode, None
    if not output.is_file():
        return 1, None
    return 0, _load(output)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", "-i", type=Path, default=DEFAULT_IN)
    ap.add_argument("--brier-output", type=Path, default=DEFAULT_BRIER_OUT)
    ap.add_argument("--harness-output", type=Path, default=DEFAULT_HARNESS_OUT)
    ap.add_argument("--drift-log", type=Path, default=DEFAULT_DRIFT_LOG)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--skip-append", action="store_true")
    ap.add_argument("--no-jsonschema", action="store_true")
    ap.add_argument("--allow-gate-fail", action="store_true", help="Continue to Brier even if some rows rejected")
    ap.add_argument("--ece-bins", type=int, default=10)
    ap.add_argument("--ece-min-per-tag", type=int, default=5)
    args = ap.parse_args()

    if not args.input.is_file():
        print(f"missing registry: {args.input}", file=sys.stderr)
        return 1

    plan = {
        "validate": str(_VALIDATE),
        "eval_brier": str(_EVAL),
        "registry": str(args.input.resolve()),
        "brier_output": str(args.brier_output.resolve()),
        "drift_log": str(args.drift_log.resolve()),
    }
    if args.dry_run:
        print(json.dumps({"ok": True, "dry_run": True, "plan": plan}, ensure_ascii=False))
        return 0

    steps: list[dict[str, Any]] = []
    v_code, gate_doc = _run_validate(args.input, no_jsonschema=args.no_jsonschema)
    steps.append({"step": "validate_input", "exit_code": v_code, "gate_pass": gate_doc.get("gate_pass")})
    if v_code == 2 and not args.allow_gate_fail:
        out = {
            "schema": HARNESS_SCHEMA,
            "generated_at_utc": _utc_now(),
            "research_rail": "B",
            "track_wall": "no_track_a_auto_merge",
            "harness_pass": False,
            "inputs": {"registry_path": str(args.input.resolve())},
            "steps": steps,
            "gate": gate_doc,
        }
        args.harness_output.parent.mkdir(parents=True, exist_ok=True)
        args.harness_output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(str(args.harness_output.resolve()))
        return 2
    if v_code not in (0, 2):
        return v_code

    b_code, brier_doc = _run_brier(
        args.input,
        args.brier_output,
        ece_bins=max(0, int(args.ece_bins)),
        ece_min_per_tag=max(1, int(args.ece_min_per_tag)),
    )
    steps.append({"step": "eval_brier", "exit_code": b_code, "output_path": str(args.brier_output)})
    if b_code != 0 or brier_doc is None:
        return b_code or 1

    metrics = brier_doc.get("metrics") if isinstance(brier_doc.get("metrics"), dict) else {}
    drift_row = {
        "schema": DRIFT_SCHEMA,
        "generated_at_utc": _utc_now(),
        "registry_path": str(args.input.resolve()),
        "brier_eval_path": str(args.brier_output.resolve()),
        "mean_brier_score": metrics.get("mean_brier_score"),
        "n_evaluated": metrics.get("n_evaluated"),
        "pending_count": metrics.get("pending_count"),
        "overdue_count": metrics.get("overdue_count"),
        "ece_weighted": (metrics.get("ece_binary") or {}).get("weighted_ece")
        if isinstance(metrics.get("ece_binary"), dict)
        else None,
        "gate_pass": gate_doc.get("gate_pass"),
        "gate_rejected_count": (gate_doc.get("counts") or {}).get("rejected"),
    }
    if not args.skip_append:
        _append_drift_log(args.drift_log, drift_row)
        steps.append({"step": "append_drift_log", "exit_code": 0, "path": str(args.drift_log)})

    harness_pass = b_code == 0 and bool(gate_doc.get("gate_pass"))
    out = {
        "schema": HARNESS_SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_rail": "B",
        "track_wall": "no_track_a_auto_merge",
        "harness_pass": harness_pass,
        "inputs": {"registry_path": str(args.input.resolve())},
        "steps": steps,
        "gate": {
            "gate_pass": gate_doc.get("gate_pass"),
            "counts": gate_doc.get("counts"),
            "rejected": gate_doc.get("rejected"),
        },
        "metrics": {
            "mean_brier_score": metrics.get("mean_brier_score"),
            "n_evaluated": metrics.get("n_evaluated"),
            "pending_count": metrics.get("pending_count"),
            "ece_binary": metrics.get("ece_binary"),
        },
        "drift_row": drift_row,
        "note": "Logos GraphRAG/cosine not predictability; Brier on resolved binary L1 only",
    }
    args.harness_output.parent.mkdir(parents=True, exist_ok=True)
    args.harness_output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(args.harness_output.resolve()))
    return 0 if harness_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
