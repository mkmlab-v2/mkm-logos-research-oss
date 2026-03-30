#!/usr/bin/env python3
"""Project DSS enriched rows into 4D vectors and state16 slots."""

from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.core.gematria_engine import build_gematria_metadata
from scripts.core.gematria_to_4d_bridge import build_gematria_4d_bridge

IN_DSS = ROOT / "data" / "logos" / "manuscripts" / "dss_parsed_enriched.jsonl"
OUT_JSON = ROOT / "reports" / "constitution" / "btrack_pilot" / "dss_4d_projection_latest.json"


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if isinstance(obj, dict):
                rows.append(obj)
    return rows


def main() -> int:
    if not IN_DSS.is_file():
        print(f"ERROR: missing input file: {IN_DSS}")
        return 2

    rows = _load_jsonl(IN_DSS)
    projected: list[dict[str, Any]] = []
    state_counter: Counter[int] = Counter()
    dist_sum = 0.0
    dist_count = 0
    for row in rows:
        text = str(row.get("text", ""))
        meta = build_gematria_metadata(raw_text=text, compressed_text=text, reconstructed_text=text)
        bridge = build_gematria_4d_bridge(gematria_metadata=meta)
        state16 = bridge.get("state16")
        if isinstance(state16, int):
            state_counter[state16] += 1
        dist = bridge.get("distance_to_state16")
        if isinstance(dist, (int, float)):
            dist_sum += float(dist)
            dist_count += 1
        projected.append(
            {
                "id": row.get("id"),
                "source_doc": row.get("source_doc"),
                "state16": state16,
                "distance_to_state16": dist,
                "vector_4d": bridge.get("vector_4d"),
                "gematria_raw_combined_sum": meta.get("raw_combined_sum", 0),
                "text_excerpt": text[:180],
            }
        )

    coverage = len([p for p in projected if isinstance(p.get("state16"), int)]) / len(projected) if projected else 0.0
    fact = {
        "input_row_count": len(rows),
        "projected_row_count": len(projected),
        "state16_coverage_rate": round(coverage, 6),
        "avg_distance_to_state16": round(dist_sum / dist_count, 6) if dist_count else None,
        "top_state16_distribution": dict(sorted(state_counter.items(), key=lambda kv: kv[1], reverse=True)[:5]),
    }
    hypo = {
        "interpretation_note": "This projection is deterministic bridge output, not proof of historical autograph reconstruction.",
        "promotion_guard": "Use as B-track exploratory evidence only; requires separate validation before any A-track promotion.",
    }
    out = {
        "schema": "btrack_dss_4d_projection_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_input": "data/logos/manuscripts/dss_parsed_enriched.jsonl",
        "fact": fact,
        "hypo": hypo,
        "rows": projected,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {OUT_JSON}")
    print(
        f"rows={fact['input_row_count']} coverage={fact['state16_coverage_rate']:.6f} "
        f"avg_distance={fact['avg_distance_to_state16']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
