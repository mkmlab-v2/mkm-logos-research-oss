#!/usr/bin/env python3
"""Build contributor → Track A promotion *candidate* envelope (never auto-applies active report).

Reads validate + stateless PoC artifacts; compares to frozen Track A KPI read-only.
Commander apply: ``apply_compression_contributor_track_a_promotion_v1.py --human-approve-promotion``.
Codec/active-report swap still requires ``apply_multilens_ultra_compression_track_a_promotion_v1.py``.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs/final/artifacts/compression_contributor_promotion_candidate_v1_latest.json"
PLUMBING_OUT = (
    ROOT / "docs/final/artifacts/compression_contributor_promotion_candidate_plumbing_rehearsal_v1_latest.json"
)
TRACK_A_ACTIVE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
DEFAULT_VALIDATE = ROOT / "reports/compression_contributor_jsonl_validate_v1_latest.json"

# Research candidate thresholds (contributor corpus — not Golden 40 promotion gate).
MIN_ROWS = 10
MIN_MEAN_JACCARD = 0.65
MIN_PASS_RATE = 0.5


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _track_a_baseline() -> dict[str, Any]:
    if not TRACK_A_ACTIVE.is_file():
        return {"available": False}
    doc = _load(TRACK_A_ACTIVE)
    cm = doc.get("compression_metrics") or {}
    return {
        "available": True,
        "path": _rel(TRACK_A_ACTIVE),
        "global_token_saving_rate": cm.get("global_token_saving_rate"),
        "min_reconstruction_fidelity_jaccard": cm.get("min_reconstruction_fidelity_jaccard"),
        "note": "Read-only reference; contributor PoC does not auto-merge into this file.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--validate-json", type=Path, default=DEFAULT_VALIDATE)
    ap.add_argument("--poc-json", type=Path, required=True)
    ap.add_argument("--tenant-id", default="contributor-community-v1")
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--min-rows", type=int, default=MIN_ROWS)
    ap.add_argument("--min-mean-jaccard", type=float, default=MIN_MEAN_JACCARD)
    ap.add_argument("--min-pass-rate", type=float, default=MIN_PASS_RATE)
    ap.add_argument(
        "--rehearsal-only",
        action="store_true",
        help="Gate-plumbing rehearsal artifact (does not replace production candidate SSOT).",
    )
    args = ap.parse_args()
    if args.rehearsal_only and args.out_json == DEFAULT_OUT:
        args.out_json = PLUMBING_OUT

    val_path = args.validate_json.resolve()
    poc_path = args.poc_json.resolve()
    if not val_path.is_file():
        print(f"error: missing validate json: {val_path}", file=sys.stderr)
        return 2
    if not poc_path.is_file():
        print(f"error: missing poc json: {poc_path}", file=sys.stderr)
        return 2

    val = _load(val_path)
    poc = _load(poc_path)
    row_count = int(val.get("row_count") or 0)
    case_count = int(poc.get("case_count") or 0)
    passed = int(poc.get("cases_passed") or 0)
    agg = poc.get("aggregate") or {}
    mean_j = float(agg.get("mean_jaccard_proxy") or 0.0)
    mean_s = float(agg.get("mean_token_saving_rate_proxy") or 0.0)
    pass_rate = (passed / case_count) if case_count else 0.0

    gates = {
        "validation_ok": bool(val.get("validation_ok")),
        "min_rows_met": row_count >= args.min_rows,
        "poc_measured": case_count > 0,
        "pass_rate_met": pass_rate >= args.min_pass_rate,
        "mean_jaccard_met": mean_j >= args.min_mean_jaccard,
    }
    commander_may_apply = all(gates.values())
    # Never auto — human flag required at apply time.
    auto_track_a = False

    doc: dict[str, Any] = {
        "schema": "compression_contributor_promotion_candidate_v1",
        "generated_at_utc": _utc(),
        "lane": "contributor_provided",
        "track": "btrack_research_only",
        "tenant_id": args.tenant_id,
        "promotion_ladder_step": "candidate_only",
        "auto_track_a_promotion_allowed": auto_track_a,
        "commander_may_apply_track_a_bridge": commander_may_apply,
        "inputs": {
            "validate_json": _rel(val_path),
            "validate_sha256": val.get("input_sha256"),
            "poc_json": _rel(poc_path),
            "contributor_jsonl": val.get("input_jsonl"),
        },
        "metrics": {
            "row_count": row_count,
            "case_count": case_count,
            "cases_passed": passed,
            "pass_rate": round(pass_rate, 6),
            "mean_jaccard_proxy": round(mean_j, 6),
            "mean_token_saving_rate_proxy": round(mean_s, 6),
            "raw": {
                "parse_ok_rate": round((case_count - int(poc.get("parse_or_api_failures") or 0)) / max(1, case_count), 6),
                "alignment_pass_rate": round(pass_rate, 6),
                "rows": case_count,
            },
            "repair_v2": None,
            "delta": None,
            "note": "Contributor PoC uses stateless_packet proxy; not repair_v2 operational layer.",
        },
        "promotion_gates": gates,
        "track_a_baseline_readonly": _track_a_baseline(),
        "forbidden_actions": [
            "overwrite_MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_without_multilens_apply",
            "claim_customer_provided_or_SEND",
            "auto_bridge_b_to_a",
        ],
        "recommended_commands": {
            "human_apply_bridge": (
                "py scripts/apply_compression_contributor_track_a_promotion_v1.py "
                "--human-approve-promotion --reviewer commander"
            ),
            "multilens_codec_promotion_if_separate": (
                "py scripts/run_ultra_compression_promotion_sweep_v1.py && "
                "py scripts/apply_multilens_ultra_compression_track_a_promotion_v1.py "
                "--human-approve-promotion"
            ),
        },
        "boundary_ack": (
            "Candidate records B-track contributor bench evidence. "
            "Track A active report unchanged until explicit multilens apply with human approval."
        ),
    }
    if args.rehearsal_only:
        doc["rehearsal_only"] = True
        doc["promotion_ladder_step"] = "plumbing_rehearsal_candidate"
        doc["boundary_ack"] = (
            "Gate-plumbing E2E rehearsal only — pipeline proof, NOT Moat quality or Track A promotion claim. "
            "Canonical deny-valve example remains compression_contributor_example_v1.jsonl."
        )
        doc["forbidden_actions"] = list(doc["forbidden_actions"]) + [
            "cite_as_github_moat_evidence",
            "overwrite_compression_contributor_promotion_candidate_v1_latest_without_explicit_path",
        ]

    out = args.out_json.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "wrote": _rel(out),
                "commander_may_apply_track_a_bridge": commander_may_apply,
                "gates": gates,
            },
            ensure_ascii=False,
        )
    )
    return 0 if commander_may_apply else 1


if __name__ == "__main__":
    raise SystemExit(main())
