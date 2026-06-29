#!/usr/bin/env python3
"""Golden-40 ACTIVE bench — raw vs repair_v2 dual report (operational layer only).

Reads the frozen Track A ACTIVE eval artifact and applies a deterministic
repair_v2 pass on reconstructed text (must_keep safety-net + whitespace norm).
raw remains primary for promotion gates; repair_v2 is operational evidence.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.report_multilens_performance_eval import (  # noqa: E402
    _ensure_sensitive_tokens_preserved,
    _jaccard,
    _sensitive_integrity,
    _sensitive_violation,
)

DEFAULT_ACTIVE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
DEFAULT_INPUT = ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
DEFAULT_OUT = ROOT / "reports/compression_golden40_active_dual_report_v1_latest.json"
SCHEMA = "compression_golden40_active_dual_report_v1"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _normalize_ws(text: str) -> str:
    return " ".join(text.split())


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _must_keep_for_case(run_config: dict[str, Any], route: dict[str, Any] | None) -> set[str]:
    terms: set[str] = set()
    for item in run_config.get("must_keep_terms") or []:
        if isinstance(item, str) and item.strip():
            terms.add(item.strip())
    if isinstance(route, dict):
        for item in route.get("must_keep") or []:
            if isinstance(item, str) and item.strip():
                terms.add(item.strip())
    return terms


def _parse_ok(reconstructed: str) -> bool:
    return bool(reconstructed.strip())


def _alignment_pass(
    *,
    parse_ok: bool,
    jaccard: float,
    sensitive_leak: bool,
    sensitive_integrity: float,
    min_jaccard: float,
    min_sensitive_integrity: float,
) -> bool:
    return (
        parse_ok
        and not sensitive_leak
        and jaccard >= min_jaccard
        and sensitive_integrity >= min_sensitive_integrity
    )


def _aggregate(rows: list[dict[str, Any]], prefix: str) -> dict[str, Any]:
    n = len(rows)
    if n == 0:
        return {
            "parse_ok_rate": None,
            "alignment_pass_rate": None,
            "mean_token_saving_rate": None,
            "mean_reconstruction_fidelity_jaccard": None,
            "repair_applied_count": 0,
            "rows": 0,
        }
    parse_ok = sum(1 for r in rows if r.get(f"{prefix}_parse_ok")) / n
    align = sum(1 for r in rows if r.get(f"{prefix}_alignment_pass")) / n
    saving = sum(float(r["token_saving_rate"]) for r in rows) / n
    jacc = sum(float(r[f"{prefix}_jaccard"]) for r in rows) / n
    repair_count = sum(1 for r in rows if r.get(f"{prefix}_repair_applied"))
    return {
        "parse_ok_rate": round(parse_ok, 6),
        "alignment_pass_rate": round(align, 6),
        "mean_token_saving_rate": round(saving, 6),
        "mean_reconstruction_fidelity_jaccard": round(jacc, 6),
        "repair_applied_count": repair_count,
        "rows": n,
    }


def build_report(
    *,
    active_path: Path,
    input_path: Path,
    min_jaccard: float,
    min_sensitive_integrity: float,
) -> dict[str, Any]:
    active = _load(active_path)
    inp = _load(input_path)
    run_config = active.get("run_config") if isinstance(active.get("run_config"), dict) else {}
    quality_gate = active.get("quality_gate") if isinstance(active.get("quality_gate"), dict) else {}
    comp = active.get("compression_metrics") if isinstance(active.get("compression_metrics"), dict) else {}
    cases = comp.get("cases") if isinstance(comp.get("cases"), list) else []

    raw_by_id: dict[str, str] = {}
    for c in inp.get("compression_cases") or []:
        if isinstance(c, dict) and c.get("id"):
            raw_by_id[str(c["id"])] = str(c.get("raw_text") or "")

    per_case: list[dict[str, Any]] = []
    for case in cases:
        if not isinstance(case, dict):
            continue
        case_id = str(case.get("id") or "")
        raw_text = raw_by_id.get(case_id, "")
        recon = str(case.get("reconstructed_text_effective") or "")
        comp_text = str(case.get("compressed_text_effective") or "")
        route = case.get("route") if isinstance(case.get("route"), dict) else None
        must_keep = _must_keep_for_case(run_config, route)

        raw_j = float(case.get("reconstruction_fidelity_jaccard") or 0.0)
        raw_leak = bool(case.get("sensitive_leak"))
        raw_integrity = float(case.get("sensitive_integrity") or 0.0)
        raw_parse = _parse_ok(recon)
        raw_align = _alignment_pass(
            parse_ok=raw_parse,
            jaccard=raw_j,
            sensitive_leak=raw_leak,
            sensitive_integrity=raw_integrity,
            min_jaccard=min_jaccard,
            min_sensitive_integrity=min_sensitive_integrity,
        )

        repaired = _normalize_ws(_ensure_sensitive_tokens_preserved(raw_text, recon, must_keep))
        repair_applied = repaired != recon
        repair_j = _jaccard(raw_text, repaired) if raw_text else raw_j
        repair_leak = _sensitive_violation(raw_text, repaired, must_keep) if raw_text else raw_leak
        repair_integrity = (
            _sensitive_integrity(raw_text, repaired, must_keep) if raw_text else raw_integrity
        )
        repair_parse = _parse_ok(repaired)
        repair_align = _alignment_pass(
            parse_ok=repair_parse,
            jaccard=repair_j,
            sensitive_leak=repair_leak,
            sensitive_integrity=repair_integrity,
            min_jaccard=min_jaccard,
            min_sensitive_integrity=min_sensitive_integrity,
        )

        row = {
            "id": case_id,
            "token_saving_rate": float(case.get("token_saving_rate") or 0.0),
            "raw_jaccard": raw_j,
            "raw_parse_ok": raw_parse,
            "raw_alignment_pass": raw_align,
            "raw_sensitive_leak": raw_leak,
            "repair_v2_jaccard": repair_j,
            "repair_v2_parse_ok": repair_parse,
            "repair_v2_alignment_pass": repair_align,
            "repair_v2_sensitive_leak": repair_leak,
            "repair_v2_repair_applied": repair_applied,
        }
        per_case.append(row)

    raw_agg = _aggregate(per_case, "raw")
    repair_agg = _aggregate(per_case, "repair_v2")
    raw_agg["sensitive_leak_count"] = sum(1 for r in per_case if r.get("raw_sensitive_leak"))
    repair_agg["sensitive_leak_count"] = sum(1 for r in per_case if r.get("repair_v2_sensitive_leak"))
    repair_agg["note"] = (
        "operational (post-processor included): must_keep append + whitespace normalize on "
        "reconstructed_text_effective; token saving unchanged (compression already applied)"
    )

    delta_align = None
    if raw_agg["alignment_pass_rate"] is not None and repair_agg["alignment_pass_rate"] is not None:
        delta_align = round(repair_agg["alignment_pass_rate"] - raw_agg["alignment_pass_rate"], 6)

    policy_min = quality_gate.get("ultra_saving_policy_min")
    global_saving = comp.get("global_token_saving_rate")

    return {
        "schema": SCHEMA,
        "generated_at_utc": _utc(),
        "cohort": "golden40_active_track_a",
        "research_only": True,
        "track_a_promotion_primary": "raw",
        "sources": {
            "active_report": str(active_path.relative_to(ROOT)).replace("\\", "/"),
            "eval_input": str(input_path.relative_to(ROOT)).replace("\\", "/"),
        },
        "thresholds": {
            "min_jaccard_for_alignment_pass": min_jaccard,
            "min_sensitive_integrity_for_alignment_pass": min_sensitive_integrity,
            "ultra_saving_policy_min_reference": policy_min,
        },
        "frozen_active_kpi_reference": {
            "global_token_saving_rate": global_saving,
            "global_token_saving_pct_display": round(float(global_saving) * 100, 2)
            if isinstance(global_saving, (int, float))
            else None,
            "avg_reconstruction_fidelity_jaccard": comp.get("avg_reconstruction_fidelity_jaccard"),
            "sensitive_violation_count": comp.get("sensitive_violation_count"),
            "quality_gate_compression_ok": quality_gate.get("compression_ok"),
        },
        "raw": raw_agg,
        "repair_v2": repair_agg,
        "delta": {
            "alignment_pass_rate_delta_repair_v2_minus_raw": delta_align,
            "mean_reconstruction_fidelity_jaccard_delta_repair_v2_minus_raw": round(
                (repair_agg["mean_reconstruction_fidelity_jaccard"] or 0.0)
                - (raw_agg["mean_reconstruction_fidelity_jaccard"] or 0.0),
                6,
            )
            if raw_agg["mean_reconstruction_fidelity_jaccard"] is not None
            and repair_agg["mean_reconstruction_fidelity_jaccard"] is not None
            else None,
            "parse_ok_rate_delta_repair_v2_minus_raw": round(
                (repair_agg["parse_ok_rate"] or 0.0) - (raw_agg["parse_ok_rate"] or 0.0),
                6,
            )
            if raw_agg["parse_ok_rate"] is not None and repair_agg["parse_ok_rate"] is not None
            else None,
        },
        "per_case": per_case,
        "disclaimer": (
            "repair_v2 is operational resilience evidence on Golden-40 ACTIVE reconstructions; "
            "do not treat repair-only uplift as core model proof or Track A promotion gate."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--active-report", type=Path, default=DEFAULT_ACTIVE)
    ap.add_argument("--eval-input", type=Path, default=DEFAULT_INPUT)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--min-jaccard", type=float, default=0.5)
    ap.add_argument("--min-sensitive-integrity", type=float, default=0.999)
    args = ap.parse_args(argv)

    if not args.active_report.is_file():
        print(f"ERROR: missing active report: {args.active_report}", file=sys.stderr)
        return 2
    if not args.eval_input.is_file():
        print(f"ERROR: missing eval input: {args.eval_input}", file=sys.stderr)
        return 2

    doc = build_report(
        active_path=args.active_report,
        input_path=args.eval_input,
        min_jaccard=args.min_jaccard,
        min_sensitive_integrity=args.min_sensitive_integrity,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(args.output), "rows": doc["raw"]["rows"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
