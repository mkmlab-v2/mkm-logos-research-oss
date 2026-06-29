#!/usr/bin/env python3
"""Evaluate Tier A baseline proximity overlap gate + serialize report [HYPO]."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _debunked_bottom3_all_fake(ingest: dict[str, Any]) -> bool:
    debunked_bottom = list(ingest.get("debunked_bottom3") or [])
    if not debunked_bottom:
        return True
    return all(str(s.get("provenance_hint") or "") == "debunked_fake" for s in debunked_bottom)


def _label_proximity_pairs(
    proximity: dict[str, Any] | None,
    *,
    strong_min: int,
) -> dict[str, Any]:
    prox = proximity or {}
    pairs = list(prox.get("pairs") or [])
    strong = [p for p in pairs if int(p.get("keyword_overlap") or 0) >= strong_min]
    weak = [p for p in pairs if int(p.get("keyword_overlap") or 0) < strong_min]
    return {
        "overlap_count": int(prox.get("overlap_count") or 0),
        "window_sec": prox.get("window_sec"),
        "pairs": pairs,
        "strong_pair_count": len(strong),
        "weak_pair_count": len(weak),
        "strong_pairs": strong,
        "weak_pairs": weak,
    }


def eval_tier_a_overlap_gate(
    diff_report: dict[str, Any],
    gate_cfg: dict[str, Any],
    *,
    ssot_path: str | None = None,
) -> dict[str, Any]:
    diff = diff_report.get("diff") or {}
    ingest = diff_report.get("ingest") or {}
    strong_min = int(gate_cfg.get("pair_strong_keyword_overlap_min") or 1)

    scholarly = _label_proximity_pairs(
        diff.get("scholarly_top3_proximity"),
        strong_min=strong_min,
    )
    multilens = _label_proximity_pairs(
        diff.get("multilens_top3_proximity"),
        strong_min=strong_min,
    )

    scholarly_pairs_ok = scholarly["overlap_count"] >= int(
        gate_cfg.get("scholarly_top3_proximity_min_pairs") or 2
    )
    multilens_pairs_ok = multilens["overlap_count"] >= int(
        gate_cfg.get("multilens_top3_proximity_min_pairs") or 2
    )
    scholarly_lane_ok = int(ingest.get("debunked_in_scholarly_lane") or 0) <= int(
        gate_cfg.get("scholarly_lane_debunked_max") or 0
    )
    debunked_bottom_ok = _debunked_bottom3_all_fake(ingest)

    checks = {
        "scholarly_top3_proximity_min_pairs": scholarly_pairs_ok,
        "multilens_top3_proximity_min_pairs": multilens_pairs_ok,
        "scholarly_lane_debunked_max": scholarly_lane_ok,
        "debunked_bottom3_all_fake": debunked_bottom_ok,
    }
    tier_a_pass = all(checks.values())

    id_overlap_note = (
        "merge_artifact: segment ids/timestamps differ after block merge; "
        "id_overlap not used as gate"
        if gate_cfg.get("id_overlap_used_as_gate") is False
        else None
    )

    return {
        "schema": "media_youtube_baseline_overlap_gate_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "tier": "A",
        "tier_b_skipped": True,
        "ssot_path": ssot_path,
        "baseline_fixture": gate_cfg.get("baseline_fixture"),
        "diff_report_pointer": None,
        "gate_spec": gate_cfg,
        "measured": {
            "scholarly_top3_proximity": scholarly,
            "multilens_top3_proximity": multilens,
            "scholarly_top3_id_overlap": diff.get("scholarly_top3_id_overlap"),
            "multilens_top3_id_overlap": diff.get("multilens_top3_id_overlap"),
            "debunked_in_scholarly_lane": ingest.get("debunked_in_scholarly_lane"),
            "id_overlap_gate_status": "informational_only" if id_overlap_note else "gate_enabled",
            "id_overlap_note": id_overlap_note,
        },
        "checks": checks,
        "tier_a_pass": tier_a_pass,
    }


def write_overlap_report(
    report: dict[str, Any],
    out_path: Path,
    *,
    diff_report_rel: str | None = None,
) -> Path:
    if diff_report_rel:
        report = dict(report)
        report["diff_report_pointer"] = diff_report_rel
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out_path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--diff-report", type=Path, required=True)
    ap.add_argument("--ssot", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--strict", action="store_true", help="Exit 1 if tier_a_pass is false")
    args = ap.parse_args()

    diff_path = args.diff_report if args.diff_report.is_absolute() else ROOT / args.diff_report
    ssot_path = args.ssot if args.ssot.is_absolute() else ROOT / args.ssot
    out_path = args.out if args.out.is_absolute() else ROOT / args.out

    if not diff_path.is_file() or not ssot_path.is_file():
        print(json.dumps({"ok": False, "error": "missing_input"}), file=sys.stderr)
        return 1

    ssot = _read_json(ssot_path)
    gate_cfg = dict(ssot.get("overlap_gate_v1") or {})
    if not gate_cfg:
        print(json.dumps({"ok": False, "error": "overlap_gate_v1_missing"}), file=sys.stderr)
        return 1

    report = eval_tier_a_overlap_gate(
        _read_json(diff_path),
        gate_cfg,
        ssot_path=_rel(ssot_path),
    )
    write_overlap_report(report, out_path, diff_report_rel=_rel(diff_path))

    payload = {
        "ok": report["tier_a_pass"],
        "report": _rel(out_path),
        "tier_a_pass": report["tier_a_pass"],
        "checks": report["checks"],
    }
    print(json.dumps(payload, ensure_ascii=False))
    if args.strict and not report["tier_a_pass"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
