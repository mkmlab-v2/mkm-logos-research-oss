#!/usr/bin/env python3
"""Register Layer-1-only PoC mechanical forecasts into general_prophecy_latest.json (B rail).

Adds missing poc.* questions and appends mechanical + uniform baseline forecast slots.
Does not overwrite Layer-3 narrative into probability fields.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from layer1_only_brier_bench_poc_lib_v1 import (
    DEFAULT_COHORT,
    DEFAULT_MAP,
    DEFAULT_REGISTRY,
    index_registry_questions,
    load_cohort,
    load_registry_map,
    mechanical_forecast_snapshots,
    poc_row_to_registry_question,
    utc_now,
    validate_registry,
)

ROOT = Path(__file__).resolve().parents[1]


def _forecast_already_present(question: dict[str, Any], detail_prefix: str) -> bool:
    for fc in question.get("forecasts") or []:
        if not isinstance(fc, dict):
            continue
        detail = str(fc.get("source_detail") or "")
        if detail_prefix in detail:
            return True
    return False


def register_poc(*, cohort_path: Path, map_path: Path, registry_path: Path, dry_run: bool) -> dict[str, Any]:
    cohort = load_cohort(cohort_path)
    mapping = load_registry_map(map_path)
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    if registry.get("schema") != "general_prophecy_registry_v1":
        raise ValueError("registry must be general_prophecy_registry_v1")

    by_id = index_registry_questions(registry)
    rows_by_poc = {str(r["question_id"]): r for r in cohort["forecasts"]}
    actions: list[dict[str, Any]] = []

    for poc_id, row in rows_by_poc.items():
        meta = mapping.get(poc_id)
        if meta is None:
            raise ValueError(f"no registry map entry for {poc_id}")
        reg_id = str(meta["registry_question_id"])
        if reg_id not in by_id:
            if not meta.get("register_if_missing"):
                raise ValueError(f"registry question missing and register_if_missing=false: {reg_id}")
            q = poc_row_to_registry_question(row, registry_question_id=reg_id)
            registry.setdefault("questions", []).append(q)
            by_id[reg_id] = q
            actions.append({"action": "insert_question", "question_id": reg_id, "poc_question_id": poc_id})
        else:
            q = by_id[reg_id]
            snaps = mechanical_forecast_snapshots(row)
            appended = 0
            for snap in snaps:
                prefix = str(snap["source_detail"]).split(":")[0]
                if _forecast_already_present(q, prefix if prefix != snap["source_detail"] else snap["source_detail"]):
                    continue
                q.setdefault("forecasts", []).append(snap)
                appended += 1
            if appended:
                actions.append(
                    {
                        "action": "append_forecasts",
                        "question_id": reg_id,
                        "poc_question_id": poc_id,
                        "count": appended,
                    }
                )

    registry["generated_at_utc"] = utc_now()
    validate_registry(registry)
    report = {
        "schema": "layer1_only_brier_bench_poc_register_v1",
        "generated_at_utc": utc_now(),
        "track_wall": "B",
        "auto_bridge_to_a": False,
        "dry_run": dry_run,
        "actions": actions,
        "questions_touched": len(actions),
    }
    return {"registry": registry, "report": report}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cohort", type=Path, default=DEFAULT_COHORT)
    ap.add_argument("--map", type=Path, default=DEFAULT_MAP)
    ap.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    ap.add_argument("--output-report", type=Path, default=ROOT / "reports" / "layer1_only_brier_bench_poc_register_v1_latest.json")
    ap.add_argument("--dry-run", action="store_true")
    ns = ap.parse_args()

    if not ns.registry.is_file():
        print(f"missing registry: {ns.registry}", file=sys.stderr)
        return 2

    try:
        result = register_poc(
            cohort_path=ns.cohort,
            map_path=ns.map,
            registry_path=ns.registry,
            dry_run=ns.dry_run,
        )
    except ValueError as exc:
        print(f"validation error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        name = type(exc).__name__
        print(f"{name}: {exc}", file=sys.stderr)
        return 1

    report = result["report"]
    ns.output_report.parent.mkdir(parents=True, exist_ok=True)
    ns.output_report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    if not ns.dry_run:
        ns.registry.write_text(json.dumps(result["registry"], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"registry updated: {ns.registry}", file=sys.stderr)
    else:
        print("dry-run: registry not written", file=sys.stderr)

    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
