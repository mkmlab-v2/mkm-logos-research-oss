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


def _build_conflict_summary(
    lens_rows: list[dict[str, Any]],
    cs: dict[str, Any],
    logos_doc: dict[str, Any] | None,
) -> dict[str, Any]:
    """Deterministic narrative only: signs/scores + optional Logos batch fields; no LLM."""
    active = [x for x in lens_rows if x.get("available")]
    maj = str(cs.get("consensus_sign") or "neutral")
    minority_ids: list[str] = []
    for r in active:
        if r.get("direction_sign") != maj:
            minority_ids.append(str(r.get("lens_id", "?")))

    parts: list[str] = []
    parts.append(
        f"Lens direction alignment: majority_sign={maj}, agreement_rate={cs.get('agreement_rate')}, "
        f"conflict_count={cs.get('conflict_count')}."
    )
    if minority_ids:
        parts.append(
            "Minority vs majority: "
            + ", ".join(minority_ids)
            + f" differ from majority_sign={maj}."
        )
    else:
        parts.append("No direction_sign conflict among active lenses.")

    breakdown: list[str] = []
    for r in active:
        breakdown.append(
            f"{r['lens_id']}: sign={r['direction_sign']}, "
            f"score={float(r['direction_score']):.6f}, conf={float(r['confidence']):.6f}"
        )
    parts.append("Breakdown: " + "; ".join(breakdown) + ".")

    verse_ids: list[str] = []
    if logos_doc and isinstance(logos_doc.get("evidence_refs"), list):
        for er in logos_doc["evidence_refs"]:
            if isinstance(er, dict):
                vid = er.get("verse_id")
                if vid:
                    verse_ids.append(str(vid))
    if verse_ids:
        parts.append(
            "Logos evidence verse_id anchors (batch-bound): " + ", ".join(verse_ids) + "."
        )
    ns = logos_doc.get("narrative_snippet_guarded") if logos_doc else None
    if isinstance(ns, str) and ns.strip():
        clip = ns.strip()
        if len(clip) > 320:
            clip = clip[:319] + "…"
        parts.append("Logos hash-tagged snippet (clipped): " + clip)

    return {
        "conflict_narrative_guarded": " ".join(parts),
        "minority_lens_ids": minority_ids,
        "majority_sign": maj,
        "logos_evidence_verse_ids": verse_ids,
        "narrative_policy": (
            "Deterministic template from lens signs/scores and optional Logos "
            "evidence_refs/narrative_snippet_guarded only; no LLM paraphrase; "
            "observation_only; not an A-track action."
        ),
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
    logos_doc = _read_json(args.logos)
    conflict_summary = _build_conflict_summary(lens_rows, cs, logos_doc)
    out = {
        "schema": "independent_lens_fusion_stub_v0",
        "version": "0.2.0",
        "ts_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "mode": "observation_only",
        "inputs": lens_rows,
        "consensus": cs,
        "conflict_summary": conflict_summary,
        "note": (
            "Read-only comparison of independent lens outputs; not A-track auto-fusion or live sizing trigger. "
            "No consistency_rate here — use consensus.agreement_rate for lens-direction alignment; "
            "optional consistency_rate is defined for myeongni 16-state experiment JSON (separate schema). "
            "conflict_summary.* is template-bound narrative + optional Logos batch anchors only. "
            "Vector gematria+myeongri geometric spike: scripts/spike_gematria_myeongri_blend_v0.py."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
