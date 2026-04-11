#!/usr/bin/env python3
"""Build KPI summary from report_schema_v2 label/grounded fields."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
IN_PATH = ROOT / "docs" / "final" / "artifacts" / "report_schema_v2_latest.json"
OUT_PATH = ROOT / "docs" / "final" / "artifacts" / "report_schema_v2_label_kpi_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def main() -> int:
    doc = _load_json(IN_PATH)
    if not doc:
        raise SystemExit(f"missing input: {IN_PATH}")

    claims = doc.get("claims")
    if not isinstance(claims, list):
        raise SystemExit("report_schema_v2_latest.json: claims must be array")

    label_counter: Counter[str] = Counter()
    grounded_true = 0
    grounded_false = 0
    for c in claims:
        if not isinstance(c, dict):
            continue
        label = str(c.get("label") or "UNKNOWN").upper()
        label_counter[label] += 1
        grounded = c.get("grounded")
        if grounded is True:
            grounded_true += 1
        elif grounded is False:
            grounded_false += 1

    total = max(1, len(claims))
    payload = {
        "schema": "report_schema_v2_label_kpi_v1",
        "generated_at_utc": _utc_now(),
        "source_report_schema_v2": str(IN_PATH),
        "totals": {
            "claim_count": len(claims),
            "grounded_true": grounded_true,
            "grounded_false": grounded_false,
            "grounded_true_rate": round(grounded_true / total, 6),
            "grounded_false_rate": round(grounded_false / total, 6),
        },
        "label_distribution": dict(label_counter),
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(OUT_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
