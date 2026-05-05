#!/usr/bin/env python3
"""Build compact boundary table from kmh synthetic boundary sweep."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_SWEEP = ART / "emotion_state_kmh_single_variable_boundary_sweep_latest.json"
DEFAULT_OUT = ART / "emotion_state_kmh_boundary_flip_table_latest.json"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sweep-json", type=Path, default=DEFAULT_SWEEP)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    sweep = _read_json(args.sweep_json)
    points = sweep.get("points") if isinstance(sweep.get("points"), list) else []

    by_fpr: dict[float, list[dict[str, Any]]] = {}
    for p in points:
        if not isinstance(p, dict):
            continue
        try:
            fpr = float(p.get("synthetic_layer5_fpr"))
            z = float(p.get("z_km"))
        except Exception:
            continue
        row = dict(p)
        row["_z"] = z
        by_fpr.setdefault(fpr, []).append(row)

    table = []
    for fpr in sorted(by_fpr.keys()):
        rows = sorted(by_fpr[fpr], key=lambda x: x["_z"])
        changed = [r for r in rows if bool(r.get("decision_changed"))]
        if not changed:
            table.append(
                {
                    "synthetic_layer5_fpr": fpr,
                    "decision_changed": False,
                    "min_z_km_for_b_go_when_a_hold": None,
                    "max_z_km_for_b_hold_when_a_go": None,
                    "change_count": 0,
                }
            )
            continue

        min_z_b_go = None
        max_z_b_hold = None
        for r in changed:
            da = str(r.get("decision_a"))
            db = str(r.get("decision_b"))
            z = float(r["_z"])
            if da == "HOLD_PRECHECK_FAILED" and db == "GO_LIVE_CANDIDATE":
                min_z_b_go = z if min_z_b_go is None else min(min_z_b_go, z)
            if da == "GO_LIVE_CANDIDATE" and db == "HOLD_PRECHECK_FAILED":
                max_z_b_hold = z if max_z_b_hold is None else max(max_z_b_hold, z)

        table.append(
            {
                "synthetic_layer5_fpr": fpr,
                "decision_changed": True,
                "min_z_km_for_b_go_when_a_hold": min_z_b_go,
                "max_z_km_for_b_hold_when_a_go": max_z_b_hold,
                "change_count": len(changed),
            }
        )

    out = {
        "schema": "emotion_state_kmh_boundary_flip_table_v1",
        "generated_at_utc": _iso_now(),
        "inputs": {"sweep_json": str(args.sweep_json).replace("\\", "/")},
        "summary": {
            "fpr_rows": len(table),
            "rows_with_decision_change": sum(1 for r in table if r.get("decision_changed")),
        },
        "table": table,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output_json": str(args.output_json), "rows": len(table)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
