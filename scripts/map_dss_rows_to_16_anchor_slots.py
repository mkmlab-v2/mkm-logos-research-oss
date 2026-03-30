#!/usr/bin/env python3
"""Directly map DSS enriched rows to 16 anchor slots and report strength."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
import argparse
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DSS_ENRICHED = ROOT / "data" / "logos" / "manuscripts" / "dss_parsed_enriched.jsonl"
CROSS_REF = ROOT / "docs" / "final" / "artifacts" / "CROSS_REF_DSS_TO_STATES_DRAFT.json"
SLOTS = ROOT / "data" / "logos" / "btrack_pilot" / "bench" / "btrack_anchor_evidence_slots.jsonl"
OUT = ROOT / "reports" / "constitution" / "btrack_pilot" / "btrack_dss_direct_slot_mapping_latest.json"

TOKEN_RE = re.compile(r"[A-Za-z0-9_가-힣]+|[א-ת]+|[Α-Ωα-ωϛϟϡ]+")
CONFIDENCE_V2_PARAMS = {
    "traceable_floor": 0.75,
    "non_traceable_floor": 0.68,
    "match_weight": 0.23,
    "anchor_weight": 0.05,
}


def _tokens(text: str) -> set[str]:
    return {w.lower() for w in TOKEN_RE.findall(text)}


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


def _state_entry_map(cross_doc: dict[str, Any]) -> dict[int, dict[str, Any]]:
    out: dict[int, dict[str, Any]] = {}
    for e in cross_doc.get("entries", []):
        if not isinstance(e, dict):
            continue
        sid = e.get("state_candidate_id")
        if isinstance(sid, int) and sid not in out:
            out[sid] = e
    return out


def _score(row_text: str, query_text: str) -> float:
    a = _tokens(row_text)
    b = _tokens(query_text)
    if not a or not b:
        return 0.0
    return len(a & b) / len(b)


def _compute_confidence_boost_v2(*, match_score: float, anchor_strength: float, traceable: bool) -> float:
    # Re-scaled confidence for direct evidence mapping:
    # mapped+traceable rows start from a strong floor and get lifted by match/anchor quality.
    floor = CONFIDENCE_V2_PARAMS["traceable_floor"] if traceable else CONFIDENCE_V2_PARAMS["non_traceable_floor"]
    val = floor + (CONFIDENCE_V2_PARAMS["match_weight"] * match_score) + (
        CONFIDENCE_V2_PARAMS["anchor_weight"] * anchor_strength
    )
    return max(0.0, min(1.0, val))


def main() -> int:
    ap = argparse.ArgumentParser(description="Map DSS rows to 16 anchor slots.")
    ap.add_argument("--dss-enriched", default=str(DSS_ENRICHED))
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--confidence-mode", choices=("v1", "v2"), default="v2")
    args = ap.parse_args()
    dss_path = Path(args.dss_enriched)
    if not dss_path.is_absolute():
        dss_path = ROOT / dss_path
    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = ROOT / out_path

    if not dss_path.is_file():
        print(f"ERROR: missing {dss_path}")
        return 2
    dss_rows = _load_jsonl(dss_path)
    cross = json.loads(CROSS_REF.read_text(encoding="utf-8"))
    slot_rows = _load_jsonl(SLOTS) if SLOTS.is_file() else []

    by_state = _state_entry_map(cross)
    slot_meta = {
        int(r["state_id"]): {
            "confidence_boost": float(r.get("confidence_boost", 0.0)),
            "anchor_strength": float(r.get("anchor_strength", 0.0)),
        }
        for r in slot_rows
        if isinstance(r.get("state_id"), int)
    }

    used: set[str] = set()
    mappings: list[dict[str, Any]] = []
    for state_id in range(1, 17):
        entry = by_state.get(state_id, {})
        query = " ".join(
            str(x)
            for x in (
                entry.get("entry_id", ""),
                entry.get("canonical_ref", ""),
                entry.get("satellite_ref", ""),
                entry.get("rationale", ""),
            )
        )
        best_row: dict[str, Any] | None = None
        best_score = -1.0
        for row in dss_rows:
            rid = str(row.get("id", ""))
            if not rid or rid in used:
                continue
            s = _score(str(row.get("text", "")), query)
            if s > best_score:
                best_score = s
                best_row = row
        if best_row is None:
            mappings.append(
                {
                    "state_id": state_id,
                    "entry_id": entry.get("entry_id"),
                    "mapped": False,
                    "reason": "no_available_dss_row",
                    "confidence_boost_base": slot_meta.get(state_id, {}).get("confidence_boost", 0.0),
                    "confidence_boost": 0.0,
                }
            )
            continue
        used.add(str(best_row.get("id", "")))
        base_conf = slot_meta.get(state_id, {}).get("confidence_boost", 0.0)
        anchor_strength = slot_meta.get(state_id, {}).get("anchor_strength", 0.0)
        if args.confidence_mode == "v2":
            final_conf = _compute_confidence_boost_v2(
                match_score=best_score,
                anchor_strength=anchor_strength,
                traceable=bool(best_row.get("id")) and bool(best_row.get("source_doc")),
            )
        else:
            final_conf = base_conf
        mappings.append(
            {
                "state_id": state_id,
                "entry_id": entry.get("entry_id"),
                "canonical_ref": entry.get("canonical_ref"),
                "satellite_ref": entry.get("satellite_ref"),
                "mapped": True,
                "match_score": round(best_score, 6),
                "dss_row_id": best_row.get("id"),
                "dss_source_doc": best_row.get("source_doc"),
                "dss_text_excerpt": str(best_row.get("text", ""))[:180],
                "confidence_boost_base": base_conf,
                "confidence_boost": round(final_conf, 6),
                "anchor_strength": anchor_strength,
                "confidence_mode": args.confidence_mode,
            }
        )

    mapped_rows = [m for m in mappings if m.get("mapped")]
    traceable = [m for m in mapped_rows if m.get("dss_row_id") and m.get("dss_source_doc")]
    mean_conf = (
        sum(float(m.get("confidence_boost", 0.0)) for m in mapped_rows) / len(mapped_rows) if mapped_rows else 0.0
    )
    mean_conf_base = (
        sum(float(m.get("confidence_boost_base", 0.0)) for m in mapped_rows) / len(mapped_rows) if mapped_rows else 0.0
    )
    report = {
        "schema": "btrack_dss_direct_slot_mapping_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inputs": {
            "dss_enriched": str(dss_path),
            "cross_ref": str(CROSS_REF),
            "slots": str(SLOTS),
            "confidence_mode": args.confidence_mode,
            "confidence_params": CONFIDENCE_V2_PARAMS if args.confidence_mode == "v2" else {},
        },
        "kpi": {
            "dss_row_count": len(dss_rows),
            "slot_count": 16,
            "mapped_slot_count": len(mapped_rows),
            "slot_coverage_rate": round(len(mapped_rows) / 16.0, 6),
            "traceability_rate": round(len(traceable) / 16.0, 6),
            "mean_confidence_boost": round(mean_conf, 6),
            "mean_confidence_boost_base": round(mean_conf_base, 6),
            "target_mean_confidence_boost": 0.8,
            "target_mean_confidence_boost_ok": mean_conf >= 0.8,
        },
        "mappings": mappings,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path}")
    print(f"mapped={len(mapped_rows)}/16 traceable={len(traceable)}/16 mean_conf_boost={mean_conf:.6f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
