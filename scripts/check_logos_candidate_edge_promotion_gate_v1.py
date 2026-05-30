#!/usr/bin/env python3
"""Promotion gate for Logos candidate edge survivors ([HYPO] B-track).

Does not merge into canonical graph. Emits pass/fail gate JSON for promote script.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SURVIVORS = ROOT / "docs/final/artifacts/logos_candidate_edge_survivors_v1_latest.json"
DEFAULT_QUALITY = ROOT / "docs/final/artifacts/logos_candidate_edges_quality_v1_latest.json"
DEFAULT_SIGNOFF = ROOT / "docs/final/fixtures/logos_candidate_edge_promotion_signoff_v1.example.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_candidate_edge_promotion_gate_v1_latest.json"

LANE_PRESETS: dict[str, dict[str, str]] = {
    "offline_4d_knn": {
        "survivors_json": "docs/final/artifacts/logos_candidate_edge_survivors_v1_latest.json",
        "quality_json": "docs/final/artifacts/logos_candidate_edges_quality_v1_latest.json",
        "signoff_json": "docs/final/artifacts/logos_candidate_edge_promotion_signoff_v1_latest.json",
        "output_json": "docs/final/artifacts/logos_candidate_edge_promotion_gate_v1_latest.json",
    },
    "ann_lite": {
        "survivors_json": "docs/final/artifacts/logos_candidate_edge_survivors_ann_lite_v1_latest.json",
        "quality_json": "docs/final/artifacts/logos_candidate_edges_quality_ann_lite_v1_latest.json",
        "signoff_json": "docs/final/artifacts/logos_candidate_edge_promotion_signoff_ann_lite_v1_latest.json",
        "output_json": "docs/final/artifacts/logos_candidate_edge_promotion_gate_ann_lite_v1_latest.json",
    },
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _parse_utc(ts: str) -> datetime | None:
    t = str(ts or "").strip()
    if not t:
        return None
    if t.endswith("Z"):
        t = t[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(t)
    except ValueError:
        return None
    return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def evaluate_promotion_gate(
    survivors_doc: dict[str, Any],
    quality_doc: dict[str, Any],
    signoff_doc: dict[str, Any],
) -> dict[str, Any]:
    survivor_count = int((survivors_doc.get("stats") or {}).get("survivor_count") or 0)
    saturation = bool(quality_doc.get("saturation_warning"))
    expiry = _parse_utc(str(signoff_doc.get("expires_at_utc") or ""))
    now = datetime.now(timezone.utc)

    checks = {
        "survivors_present": survivor_count > 0,
        "signoff_schema_ok": signoff_doc.get("schema") == "logos_candidate_edge_promotion_signoff_v1",
        "signoff_approved": bool(signoff_doc.get("approved")),
        "signoff_not_expired": bool(expiry and expiry > now),
        "saturation_acknowledged": (not saturation) or bool(signoff_doc.get("saturation_warning_acknowledged")),
        "lora_prune_acknowledged": bool(signoff_doc.get("lora_prune_pending_acknowledged")),
        "canonical_merge_blocked_by_policy": True,
    }
    lane_id = str(
        signoff_doc.get("lane_id")
        or survivors_doc.get("lane_id")
        or quality_doc.get("lane_id")
        or "unknown"
    )
    gate_pass = all(
        checks[k]
        for k in (
            "survivors_present",
            "signoff_schema_ok",
            "signoff_approved",
            "signoff_not_expired",
            "saturation_acknowledged",
            "lora_prune_acknowledged",
        )
    )

    return {
        "schema": "logos_candidate_edge_promotion_gate_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "promotion_required": True,
        "hypothesis_tier": "B",
        "lane_id": lane_id,
        "gate_pass": gate_pass,
        "status": "PASS" if gate_pass else "HOLD",
        "checks": checks,
        "survivor_count": survivor_count,
        "saturation_warning": saturation,
        "merge_to_canonical_allowed": False,
        "recommended_next": (
            "promote_logos_candidate_edge_survivors_v1.py"
            if gate_pass
            else "resolve_signoff_or_survivor_blockers"
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--lane-id",
        choices=sorted(LANE_PRESETS.keys()),
        default=None,
        help="Preset paths for offline_4d_knn or ann_lite",
    )
    ap.add_argument("--survivors-json", type=Path, default=None)
    ap.add_argument("--quality-json", type=Path, default=None)
    ap.add_argument("--signoff-json", type=Path, default=None)
    ap.add_argument("--output-json", type=Path, default=None)
    ap.add_argument("--strict", action="store_true", help="Exit 1 when gate_pass is false")
    args = ap.parse_args()

    preset = LANE_PRESETS.get(args.lane_id or "", {})
    survivors_path = args.survivors_json or ROOT / preset.get("survivors_json", DEFAULT_SURVIVORS)
    quality_path = args.quality_json or ROOT / preset.get("quality_json", DEFAULT_QUALITY)
    signoff_path = args.signoff_json or ROOT / preset.get("signoff_json", DEFAULT_SIGNOFF)
    out_path = args.output_json or ROOT / preset.get("output_json", DEFAULT_OUT)

    survivors = _read_json(survivors_path if survivors_path.is_absolute() else ROOT / survivors_path)
    quality = _read_json(quality_path if quality_path.is_absolute() else ROOT / quality_path)
    signoff = _read_json(signoff_path if signoff_path.is_absolute() else ROOT / signoff_path)

    doc = evaluate_promotion_gate(survivors, quality, signoff)
    doc["inputs"] = {
        "lane_id": args.lane_id,
        "survivors_json": str(survivors_path).replace("\\", "/"),
        "quality_json": str(quality_path).replace("\\", "/"),
        "signoff_json": str(signoff_path).replace("\\", "/"),
    }

    out_path = out_path if out_path.is_absolute() else ROOT / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    if args.strict and not doc["gate_pass"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
