#!/usr/bin/env python3
"""Apply NotebookLM-derived score overrides to Dark Flow B-track eval JSON."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE = ROOT / "docs" / "final" / "artifacts" / "darkflow_btrack_eval_template_v1.json"
DEFAULT_OVERRIDE = ROOT / "docs" / "final" / "artifacts" / "darkflow_notebooklm_override_template_v1.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "darkflow_btrack_eval_latest.json"

SCORE_FIELDS = ("evidence_score", "replication_score", "systematic_risk", "predictive_consistency", "notes")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _to_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def main() -> int:
    ap = argparse.ArgumentParser(description="Apply NotebookLM overrides to Dark Flow eval template.")
    ap.add_argument("--base-json", type=Path, default=DEFAULT_BASE)
    ap.add_argument("--override-json", type=Path, default=DEFAULT_OVERRIDE)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if not args.base_json.exists():
        raise FileNotFoundError(f"Missing base json: {args.base_json}")
    if not args.override_json.exists():
        raise FileNotFoundError(f"Missing override json: {args.override_json}")

    base = _load(args.base_json)
    override = _load(args.override_json)

    hypotheses = base.get("hypotheses", [])
    if not isinstance(hypotheses, list):
        raise ValueError("base json hypotheses must be a list")
    rows_by_id: dict[str, dict[str, Any]] = {}
    for row in hypotheses:
        if isinstance(row, dict) and "id" in row:
            rows_by_id[str(row["id"])] = row

    overrides = override.get("overrides", [])
    if not isinstance(overrides, list):
        raise ValueError("override json overrides must be a list")

    updated_ids: list[str] = []
    for item in overrides:
        if not isinstance(item, dict):
            continue
        hid = str(item.get("id", "")).strip()
        if not hid or hid not in rows_by_id:
            continue
        target = rows_by_id[hid]
        for field in SCORE_FIELDS:
            if field not in item:
                continue
            if field == "notes":
                target[field] = str(item[field])
            else:
                target[field] = round(_to_float(item[field], _to_float(target.get(field), 0.0)), 6)
        updated_ids.append(hid)

    base["generated_at_utc"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    base["source_track"] = "B"
    base["observation_mode"] = "RESEARCH_ONLY"
    base["notebooklm_override"] = {
        "applied": True,
        "override_json": str(args.override_json),
        "updated_hypothesis_ids": sorted(set(updated_ids)),
        "updated_count": len(set(updated_ids)),
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(base, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(args.output_json))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
