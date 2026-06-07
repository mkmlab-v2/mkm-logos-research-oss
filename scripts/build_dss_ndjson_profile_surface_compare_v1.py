#!/usr/bin/env python3
"""Compare default (3-file) vs ext3-only NDJSON surface profiles · isolated AB readout."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DEFAULT_SURFACE = ROOT / "docs/final/artifacts/news_observation_v1_dss_ndjson_full_surface_latest.jsonl"
DEFAULT_EXT3_SURFACE = ROOT / "docs/final/artifacts/news_observation_v1_dss_ndjson_ext3_only_full_surface_latest.jsonl"
DEFAULT_DEFAULT_AB = ROOT / "reports/biblical_resonance_isolated_production_ab_latest.json"
DEFAULT_EXT3_AB = ROOT / "reports/biblical_resonance_isolated_production_ab_ext3_only_latest.json"
DEFAULT_OUT = ROOT / "reports/dss_ndjson_profile_surface_compare_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _row_count(path: Path) -> int:
    if not path.is_file():
        return 0
    return sum(1 for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip())


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--default-surface-jsonl", type=Path, default=DEFAULT_DEFAULT_SURFACE)
    ap.add_argument("--ext3-surface-jsonl", type=Path, default=DEFAULT_EXT3_SURFACE)
    ap.add_argument("--default-isolated-ab-json", type=Path, default=DEFAULT_DEFAULT_AB)
    ap.add_argument("--ext3-isolated-ab-json", type=Path, default=DEFAULT_EXT3_AB)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    default_ab = _load(args.default_isolated_ab_json)
    ext3_ab = _load(args.ext3_isolated_ab_json)

    def _arm(doc: dict[str, Any], key: str) -> dict[str, Any]:
        block = doc.get(key) if isinstance(doc.get(key), dict) else {}
        return {
            "matched_rows": block.get("matched_rows"),
            "composite_score": block.get("composite_score"),
        }

    default_repair = _arm(default_ab, "repair_v2")
    ext3_repair = _arm(ext3_ab, "repair_v2")
    default_delta = default_ab.get("delta") if isinstance(default_ab.get("delta"), dict) else {}
    ext3_delta = ext3_ab.get("delta") if isinstance(ext3_ab.get("delta"), dict) else {}

    def _eff(surface_rows: int, delta_matched: float | None) -> float | None:
        if surface_rows <= 0 or delta_matched is None:
            return None
        return round(float(delta_matched) / float(surface_rows), 6)

    default_rows = _row_count(args.default_surface_jsonl)
    ext3_rows = _row_count(args.ext3_surface_jsonl)

    payload = {
        "schema": "dss_ndjson_profile_surface_compare_v1",
        "generated_at_utc": _utc_now(),
        "research_rail": "B",
        "hypothesis_tier": "[HYPO]",
        "profiles": {
            "default_3file": {
                "surface_jsonl": str(args.default_surface_jsonl),
                "surface_rows": default_rows,
                "isolated_ab_json": str(args.default_isolated_ab_json),
                "repair_v2": default_repair,
                "delta_repair_minus_raw": default_delta,
                "matched_per_surface_row": _eff(default_rows, default_delta.get("matched_rows")),
            },
            "ext3_only": {
                "surface_jsonl": str(args.ext3_surface_jsonl),
                "surface_rows": ext3_rows,
                "isolated_ab_json": str(args.ext3_isolated_ab_json),
                "repair_v2": ext3_repair,
                "delta_repair_minus_raw": ext3_delta,
                "matched_per_surface_row": _eff(ext3_rows, ext3_delta.get("matched_rows")),
            },
        },
        "recommended_profile": (
            "ext3_only"
            if _eff(ext3_rows, ext3_delta.get("matched_rows")) is not None
            and _eff(default_rows, default_delta.get("matched_rows")) is not None
            and _eff(ext3_rows, ext3_delta.get("matched_rows"))
            >= _eff(default_rows, default_delta.get("matched_rows"))
            else "default_3file_max_coverage"
        ),
        "interpretation": {
            "status": "research_only_not_promotion_proof",
            "note": "ext3_only drops ext2_weighted leg; compare isolated AB for cleaner Hebrew-priority readout.",
        },
        "track_a_promotion": "blocked",
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(args.output_json)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
