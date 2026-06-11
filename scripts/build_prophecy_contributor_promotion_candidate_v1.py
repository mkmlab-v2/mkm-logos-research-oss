#!/usr/bin/env python3
"""Build contributor prophecy → registry merge *candidate* (never auto-applies general_prophecy_latest)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs/final/artifacts/prophecy_contributor_promotion_candidate_v1_latest.json"
DEFAULT_VALIDATE = ROOT / "reports/prophecy_contributor_jsonl_validate_v1_latest.json"
PRODUCTION_REGISTRY = ROOT / "docs/final/artifacts/general_prophecy_latest.json"

MIN_ROWS = 5
MIN_RESOLVED_FOR_BRIER = 3
MAX_MEAN_BRIER = 0.35


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--validate-json", type=Path, default=DEFAULT_VALIDATE)
    ap.add_argument("--sandbox-registry-json", type=Path, required=True)
    ap.add_argument("--brier-eval-json", type=Path, default=None)
    ap.add_argument("--tenant-id", default="prophecy-contributor-community-v1")
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--min-rows", type=int, default=MIN_ROWS)
    ap.add_argument("--min-resolved", type=int, default=MIN_RESOLVED_FOR_BRIER)
    ap.add_argument("--max-mean-brier", type=float, default=MAX_MEAN_BRIER)
    args = ap.parse_args()

    val_path = args.validate_json.resolve()
    sandbox_path = args.sandbox_registry_json.resolve()
    if not val_path.is_file() or not sandbox_path.is_file():
        print("error: missing validate or sandbox registry", file=sys.stderr)
        return 2

    val = _load(val_path)
    sandbox = _load(sandbox_path)
    row_count = int(val.get("row_count") or 0)
    resolved_count = int(val.get("resolved_count") or 0)
    question_count = len(sandbox.get("questions") or [])

    brier_doc: dict[str, Any] | None = None
    mean_brier: float | None = None
    brier_resolved = 0
    if args.brier_eval_json and args.brier_eval_json.is_file():
        brier_doc = _load(args.brier_eval_json)
        metrics = brier_doc.get("metrics") or {}
        mean_brier = metrics.get("mean_brier_score")
        brier_resolved = int(metrics.get("n_evaluated") or metrics.get("resolved_count") or 0)

    brier_gate = True
    if resolved_count >= args.min_resolved:
        brier_gate = (
            brier_doc is not None
            and brier_resolved >= args.min_resolved
            and mean_brier is not None
            and float(mean_brier) <= args.max_mean_brier
        )
    elif resolved_count == 0:
        brier_gate = True  # pending-only corpus — candidate for question intake, not calibration headline

    gates = {
        "validation_ok": bool(val.get("validation_ok")),
        "min_rows_met": row_count >= args.min_rows,
        "sandbox_built": question_count == row_count and question_count > 0,
        "brier_gate_met": brier_gate,
    }
    commander_may_apply = all(gates.values())

    prod_note = {"available": PRODUCTION_REGISTRY.is_file(), "path": _rel(PRODUCTION_REGISTRY)}
    doc: dict[str, Any] = {
        "schema": "prophecy_contributor_promotion_candidate_v1",
        "generated_at_utc": _utc(),
        "lane": "contributor_provided",
        "track": "btrack_research_only",
        "tenant_id": args.tenant_id,
        "promotion_ladder_step": "candidate_only",
        "auto_registry_merge_allowed": False,
        "commander_may_apply_registry_bridge": commander_may_apply,
        "inputs": {
            "validate_json": _rel(val_path),
            "validate_sha256": val.get("input_sha256"),
            "sandbox_registry_json": _rel(sandbox_path),
            "contributor_jsonl": val.get("input_jsonl"),
            "brier_eval_json": _rel(args.brier_eval_json) if args.brier_eval_json and args.brier_eval_json.is_file() else None,
        },
        "metrics": {
            "row_count": row_count,
            "resolved_count": resolved_count,
            "question_count": question_count,
            "mean_brier_score": mean_brier,
            "brier_resolved_count": brier_resolved,
        },
        "promotion_gates": gates,
        "production_registry_readonly": prod_note,
        "forbidden_actions": [
            "overwrite_general_prophecy_latest_without_human_apply",
            "claim_customer_provided_or_SEND",
            "auto_bridge_b_to_live_trading",
        ],
        "recommended_commands": {
            "human_apply": (
                "py scripts/apply_prophecy_contributor_promotion_v1.py "
                "--human-approve-promotion --reviewer commander"
            ),
        },
        "interpretation": "[HYPO] contributor bench — not Track A price hit-rate or counsel SEND headline",
    }

    out = args.out_json.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"commander_may_apply_registry_bridge": commander_may_apply, "gates": gates}, ensure_ascii=False))
    return 0 if commander_may_apply else 1


if __name__ == "__main__":
    raise SystemExit(main())
