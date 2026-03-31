# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.82, L:0.78, K:0.31, M:0.37}
# Balance: 86
# Purpose: Build manual label map template from unlabeled sasang GT-ready cohort rows.
# Keywords: sasang, label_map, template, unlabeled, cohort
#!/usr/bin/env python3
"""Build `case_id -> parent` template for unlabeled sasang cohort rows."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
PARENTS = ("TY", "SY", "TE", "SE")


def _abs(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if isinstance(row, dict):
                rows.append(row)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--cohort",
        default="data/constitution/korean_cohort/gt_cohort.from_clinical_evolution.latest.jsonl",
        help="GT-ready cohort JSONL path",
    )
    ap.add_argument(
        "--out",
        default="data/constitution/korean_cohort/sasang_case_to_parent.manual_map.latest.json",
        help="Output manual map JSON path",
    )
    args = ap.parse_args()

    cohort_path = _abs(args.cohort)
    out_path = _abs(args.out)
    if not cohort_path.is_file():
        print(f"ERROR: missing cohort file: {cohort_path}")
        return 2

    rows = _read_jsonl(cohort_path)
    case_to_parent: dict[str, str] = {}
    hints: list[dict[str, str]] = []
    for row in rows:
        case_id = str(row.get("case_id", "")).strip()
        parent = str(row.get("expected_parent", "")).strip().upper()
        if not case_id:
            continue
        if parent in PARENTS:
            # Keep existing labeled rows to avoid accidental overwrite.
            case_to_parent[case_id] = parent
            continue
        # Unlabeled rows use placeholder for operator fill.
        case_to_parent[case_id] = ""
        hints.append(
            {
                "case_id": case_id,
                "sample_id": str(row.get("sample_id", "")),
                "text_hint": str(row.get("text", ""))[:200],
                "label_options": "TY|SY|TE|SE",
            }
        )

    doc = {
        "schema": "sasang_case_to_parent_manual_map_v1",
        "note": "Fill empty values with TY/SY/TE/SE, then feed --manual-map into build_sasang_gt_from_clinical_evolution.py",
        "case_to_parent": case_to_parent,
        "unlabeled_hints": hints,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "cohort_rows": len(rows),
                "unlabeled_count": len(hints),
                "output_path": str(out_path),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

