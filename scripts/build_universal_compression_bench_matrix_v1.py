#!/usr/bin/env python3
"""Build Universal Compression Bench Matrix input (B-track, separate from Golden 40)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "docs/final/artifacts/universal_compression_bench_matrix_registry_v1.json"
OUT_INPUT = ROOT / "docs/final/artifacts/UNIVERSAL_COMPRESSION_BENCH_MATRIX_INPUT_V1.json"
OUT_BUILD = ROOT / "reports/constitution/btrack_pilot/comp_universal_bench_matrix_build_v1.json"
FORBIDDEN = (
    ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json",
    ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json",
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_cases(path: Path, domain_tag: str, lane_id: str) -> list[dict[str, Any]]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    cases = doc.get("compression_cases") or []
    out: list[dict[str, Any]] = []
    for row in cases:
        if not isinstance(row, dict):
            continue
        cid = str(row.get("id") or "")
        if not cid:
            continue
        item = dict(row)
        item["id"] = f"{lane_id}__{cid}"
        item["domain_tag"] = domain_tag
        item["lane_id"] = lane_id
        item["matrix_bench"] = "universal_matrix_v1"
        item["research_only"] = True
        out.append(item)
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--include-golden",
        action="store_true",
        help="Copy Golden 40 cases into matrix (default: lanes only; Golden stays separate).",
    )
    parser.add_argument("--registry", type=Path, default=REGISTRY)
    args = parser.parse_args()

    reg = json.loads(args.registry.read_text(encoding="utf-8"))
    lanes = [ln for ln in reg.get("lanes") or [] if ln.get("enabled")]
    merged: list[dict[str, Any]] = []
    lane_stats: list[dict[str, Any]] = []

    if args.include_golden:
        golden_path = ROOT / str(reg["golden_set_frozen"]["input_path"])
        golden_cases = _load_cases(golden_path, "golden_full_v2_40", "golden_full_v2_40")
        merged.extend(golden_cases)
        lane_stats.append(
            {
                "lane_id": "golden_full_v2_40",
                "domain_tag": "golden_full_v2_40",
                "cases": len(golden_cases),
                "input_path": str(golden_path.relative_to(ROOT)).replace("\\", "/"),
            }
        )

    for lane in sorted(lanes, key=lambda x: int(x.get("priority") or 0)):
        rel = str(lane["input_path"])
        path = ROOT / rel
        if not path.is_file():
            lane_stats.append(
                {
                    "lane_id": lane["lane_id"],
                    "domain_tag": lane["domain_tag"],
                    "cases": 0,
                    "skipped": True,
                    "reason": "input_missing",
                    "input_path": rel,
                }
            )
            continue
        batch = _load_cases(path, str(lane["domain_tag"]), str(lane["lane_id"]))
        merged.extend(batch)
        lane_stats.append(
            {
                "lane_id": lane["lane_id"],
                "domain_tag": lane["domain_tag"],
                "cases": len(batch),
                "input_path": rel,
            }
        )

    matrix_doc = {
        "schema": "universal_compression_bench_matrix_input_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "bench_label": "universal_matrix_v1",
        "golden_included": bool(args.include_golden),
        "golden_frozen_pointer": reg["golden_set_frozen"]["input_path"],
        "case_count": len(merged),
        "compression_cases": merged,
    }
    OUT_INPUT.parent.mkdir(parents=True, exist_ok=True)
    OUT_INPUT.write_text(json.dumps(matrix_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    build_doc = {
        "schema": "comp_universal_bench_matrix_build_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "registry": str(args.registry.relative_to(ROOT)).replace("\\", "/"),
        "matrix_input": str(OUT_INPUT.relative_to(ROOT)).replace("\\", "/"),
        "case_count": len(merged),
        "lane_stats": lane_stats,
        "forbidden_write_paths": [str(p.relative_to(ROOT)).replace("\\", "/") for p in FORBIDDEN],
        "golden_do_not_modify": True,
    }
    OUT_BUILD.parent.mkdir(parents=True, exist_ok=True)
    OUT_BUILD.write_text(json.dumps(build_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "wrote_input": OUT_INPUT.name,
                "wrote_build": OUT_BUILD.name,
                "case_count": len(merged),
                "lanes_enabled": len(lanes),
            },
            ensure_ascii=False,
        )
    )
    return 0 if merged else 1


if __name__ == "__main__":
    raise SystemExit(main())
