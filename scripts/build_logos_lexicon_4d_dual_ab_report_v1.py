#!/usr/bin/env python3
"""Dual A/B report: baseline min2 vs experimental min1 lexicon 4D coverage [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "reports/logos_41k_4d_reclassification_audit_v1_latest.json"
MIN1 = ROOT / "reports/logos_41k_4d_reclassification_audit_v1_min1_latest.json"
OUT_DEFAULT = ROOT / "reports/logos_lexicon_4d_dual_ab_report_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return {}


def _coverage(doc: dict[str, Any]) -> float | None:
    pb = doc.get("phase_pb_lexicon_coverage") or {}
    cov = pb.get("lexicon_4d_coverage_rate")
    if cov is None:
        cov = pb.get("lexicon_4d_coverage")
    if cov is None:
        cov = (doc.get("summary") or {}).get("lexicon_4d_coverage")
    try:
        return float(cov) if cov is not None else None
    except (TypeError, ValueError):
        return None


def build(*, baseline_path: Path, min1_path: Path) -> dict[str, Any]:
    baseline = _load(baseline_path)
    min1 = _load(min1_path)
    b_cov = _coverage(baseline)
    m_cov = _coverage(min1)
    delta = round(m_cov - b_cov, 6) if b_cov is not None and m_cov is not None else None

    shadow_recommendation = "hold_baseline"
    if delta is not None and delta >= 0.15 and m_cov is not None and m_cov >= 0.65:
        shadow_recommendation = "min1_shadow_candidate"
    elif delta is not None and delta >= 0.05:
        shadow_recommendation = "min1_ab_watch"

    return {
        "schema": "logos_lexicon_4d_dual_ab_report_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "track_wall": {"track_a_bridge": False, "track_a_promotion_from_repair_only": False},
        "raw": {"lexicon_4d_coverage": b_cov, "artifact": str(baseline_path.relative_to(ROOT)).replace("\\", "/")},
        "min1_experiment": {
            "lexicon_4d_coverage": m_cov,
            "artifact": str(min1_path.relative_to(ROOT)).replace("\\", "/"),
        },
        "delta": {"lexicon_4d_coverage_min1_minus_baseline": delta},
        "shadow_recommendation": shadow_recommendation,
        "note": "min1 is shadow experiment only; Track A promotion requires separate gate",
        "reproduce": "py scripts/build_logos_lexicon_4d_dual_ab_report_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--baseline", type=Path, default=BASELINE)
    ap.add_argument("--min1", type=Path, default=MIN1)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    doc = build(baseline_path=args.baseline, min1_path=args.min1)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ok = doc["raw"]["lexicon_4d_coverage"] is not None
    print(json.dumps({"ok": ok, "shadow_recommendation": doc["shadow_recommendation"], "delta": doc["delta"]}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
