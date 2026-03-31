# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.87, L:0.84, K:0.33, M:0.41}
# Balance: 88
# Purpose: Build sasang GT-ready cohort JSONL from clinical_evolution feature/label files.
# Keywords: sasang, ground truth, clinical_evolution, cohort, jsonl
#!/usr/bin/env python3
"""Build a sasang GT-ready cohort from clinical_evolution inputs.

This script normalizes `case_id` to `sample_id` and emits rows compatible with
the sasang clinical evaluator except `expected_parent`, which may be missing.
`expected_parent` can be injected from:
1) manual map JSON (case_id -> TY/SY/TE/SE), and/or
2) optional heuristic profile from symptom features.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
PARENTS = {"TY", "SY", "TE", "SE"}


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


def _load_manual_map(path: Path | None) -> dict[str, str]:
    if path is None:
        return {}
    doc = json.loads(path.read_text(encoding="utf-8"))
    raw = doc.get("case_to_parent", doc)
    out: dict[str, str] = {}
    if isinstance(raw, dict):
        for k, v in raw.items():
            case_id = str(k).strip()
            parent = str(v).strip().upper()
            if case_id and parent in PARENTS:
                out[case_id] = parent
    return out


def _heuristic_parent(feature_row: dict[str, Any]) -> str | None:
    # Very light heuristic for plumbing only; never clinical claim.
    sym = feature_row.get("symptoms_weekly")
    if not isinstance(sym, dict):
        return None
    flush = float(sym.get("facial_flushing", 0) or 0)
    cold = float(sym.get("cold_hands_feet", sym.get("cold_intolerance", 0)) or 0)
    insomnia = float(sym.get("insomnia", 0) or 0)
    dysuria = float(sym.get("dysuria_frequency", 0) or 0)

    if flush >= 7 and insomnia >= 7:
        return "SY"
    if cold >= 7 and dysuria >= 4:
        return "SE"
    if cold <= 4 and flush <= 4:
        return "TE"
    # TY left intentionally rare in heuristic mode.
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--features",
        default="data/clinical_evolution/features.jsonl",
        help="clinical_evolution feature JSONL with case_id",
    )
    ap.add_argument(
        "--labels",
        default="data/clinical_evolution/labels.jsonl",
        help="clinical_evolution labels JSONL (optional metadata attach)",
    )
    ap.add_argument(
        "--manual-map",
        default="",
        help="Optional JSON case->parent map. Shape: {\"case_id\":\"SY\"} or {\"case_to_parent\":{...}}",
    )
    ap.add_argument(
        "--use-heuristic-parent",
        action="store_true",
        help="Fill expected_parent by heuristic when manual map is absent.",
    )
    ap.add_argument(
        "--out",
        default="data/constitution/korean_cohort/gt_cohort.from_clinical_evolution.latest.jsonl",
        help="Output GT-ready JSONL path",
    )
    args = ap.parse_args()

    features_path = _abs(args.features)
    labels_path = _abs(args.labels)
    out_path = _abs(args.out)
    map_path = _abs(args.manual_map) if args.manual_map else None

    if not features_path.is_file():
        print(f"ERROR: missing features file: {features_path}")
        return 2
    if not labels_path.is_file():
        print(f"WARN: labels file missing: {labels_path} (continuing with features only)")
    if map_path and not map_path.is_file():
        print(f"ERROR: missing manual-map file: {map_path}")
        return 2

    features = _read_jsonl(features_path)
    labels = _read_jsonl(labels_path) if labels_path.is_file() else []
    manual_map = _load_manual_map(map_path)

    # attach latest label event by case_id for traceability
    label_by_case: dict[str, dict[str, Any]] = {}
    for row in labels:
        case_id = str(row.get("case_id", "")).strip()
        if not case_id:
            continue
        label_by_case[case_id] = row

    out_rows: list[dict[str, Any]] = []
    manual_used = 0
    heuristic_used = 0
    missing_parent = 0
    for row in features:
        case_id = str(row.get("case_id", "")).strip()
        if not case_id:
            continue
        sample_id = case_id.upper()

        parent = manual_map.get(case_id)
        if parent:
            manual_used += 1
        elif args.use_heuristic_parent:
            parent = _heuristic_parent(row)
            if parent:
                heuristic_used += 1

        if parent not in PARENTS:
            parent = None
            missing_parent += 1

        text_parts = []
        symptoms = row.get("symptoms_weekly")
        if isinstance(symptoms, dict) and symptoms:
            text_parts.append(
                "symptoms: " + ", ".join(f"{k}={v}" for k, v in sorted(symptoms.items(), key=lambda x: x[0]))
            )
        biometrics = row.get("biometrics")
        if isinstance(biometrics, dict) and biometrics:
            text_parts.append(
                "biometrics: " + ", ".join(f"{k}={v}" for k, v in sorted(biometrics.items(), key=lambda x: x[0]))
            )

        latest_event = label_by_case.get(case_id, {})
        event_type = latest_event.get("event_type")
        if event_type:
            text_parts.append(f"event_type={event_type}")

        out_rows.append(
            {
                "sample_id": sample_id,
                "text": " | ".join(text_parts) if text_parts else f"case_id={case_id}",
                "expected_parent": parent if parent else "UNLABELED",
                "cohort": "CLINICAL_EVOLUTION_DERIVED_V1",
                "annotation_version": "v1",
                "label_source": "manual_map" if manual_map.get(case_id) else ("heuristic" if parent else "missing"),
                "case_id": case_id,
            }
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in out_rows), encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "features_rows": len(features),
                "labels_rows": len(labels),
                "written_rows": len(out_rows),
                "manual_parent_rows": manual_used,
                "heuristic_parent_rows": heuristic_used,
                "missing_parent_rows": missing_parent,
                "output_path": str(out_path),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

