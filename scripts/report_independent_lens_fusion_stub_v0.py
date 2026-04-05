#!/usr/bin/env python3
"""Read three independent lens artifacts and emit consensus/conflict summary (fusion stub v0)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "independent_lens_fusion_stub_latest.json"

DEFAULT_MYEONGNI = ROOT / "docs" / "final" / "artifacts" / "myeongni_independent_lens_latest.json"
DEFAULT_SASANG = ROOT / "docs" / "final" / "artifacts" / "sasang_independent_lens_latest.json"
DEFAULT_LOGOS = ROOT / "docs" / "final" / "artifacts" / "logos_independent_lens_latest.json"


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def _pick_sign(v: float) -> str:
    if v > 0:
        return "bull"
    if v < 0:
        return "bear"
    return "neutral"


def _load_lens(path: Path, lens_name: str) -> dict[str, Any]:
    doc = _read_json(path)
    if not doc:
        return {
            "lens_id": lens_name,
            "available": False,
            "direction_score": 0.0,
            "confidence": 0.0,
            "direction_sign": "neutral",
        }
    scores = doc.get("scores") if isinstance(doc.get("scores"), dict) else {}
    ds = float(scores.get("direction_score", 0.0))
    cf = float(scores.get("confidence", 0.0))
    return {
        "lens_id": str(doc.get("lens_id") or lens_name),
        "available": True,
        "direction_score": ds,
        "confidence": max(0.0, min(1.0, cf)),
        "direction_sign": _pick_sign(ds),
        "artifact_path": str(path.resolve()),
        "artifact_ts_utc": doc.get("ts_utc"),
        "schema": doc.get("schema"),
    }


def _consensus(summary: list[dict[str, Any]]) -> dict[str, Any]:
    active = [x for x in summary if x["available"]]
    if not active:
        return {
            "available_count": 0,
            "agreement_rate": 0.0,
            "conflict_count": 0,
            "consensus_sign": "neutral",
            "consensus_score": 0.0,
            "consensus_confidence": 0.0,
        }
    sign_counts = {"bull": 0, "bear": 0, "neutral": 0}
    for row in active:
        sign_counts[row["direction_sign"]] += 1
    majority_sign = max(sign_counts, key=sign_counts.get)
    agreement_rate = sign_counts[majority_sign] / len(active)
    conflict_count = len(active) - sign_counts[majority_sign]

    weighted_num = sum(r["direction_score"] * r["confidence"] for r in active)
    weighted_den = sum(r["confidence"] for r in active)
    consensus_score = weighted_num / weighted_den if weighted_den > 0 else 0.0
    mean_conf = sum(r["confidence"] for r in active) / len(active)

    return {
        "available_count": len(active),
        "agreement_rate": round(agreement_rate, 6),
        "conflict_count": conflict_count,
        "consensus_sign": majority_sign,
        "consensus_score": round(consensus_score, 6),
        "consensus_confidence": round(mean_conf, 6),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Fusion stub v0 for independent lens outputs.")
    ap.add_argument("--myeongni", type=Path, default=DEFAULT_MYEONGNI)
    ap.add_argument("--sasang", type=Path, default=DEFAULT_SASANG)
    ap.add_argument("--logos", type=Path, default=DEFAULT_LOGOS)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    lens_rows = [
        _load_lens(args.myeongni, "myeongni"),
        _load_lens(args.sasang, "sasang"),
        _load_lens(args.logos, "logos"),
    ]
    cs = _consensus(lens_rows)
    out = {
        "schema": "independent_lens_fusion_stub_v0",
        "version": "0.1.0",
        "ts_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "mode": "observation_only",
        "inputs": lens_rows,
        "consensus": cs,
        "note": (
            "Read-only comparison of independent lens outputs; not A-track auto-fusion or live sizing trigger. "
            "No consistency_rate here — use consensus.agreement_rate for lens-direction alignment; "
            "optional consistency_rate is defined for myeongni 16-state experiment JSON (separate schema). "
            "Vector gematria+myeongri geometric spike: scripts/spike_gematria_myeongri_blend_v0.py."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
