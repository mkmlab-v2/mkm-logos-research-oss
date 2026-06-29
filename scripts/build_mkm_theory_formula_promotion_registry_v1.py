#!/usr/bin/env python3
"""Build theory formula promotion registry — P5 B-track gate pointers ([HYPO] only)."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORMULAS = ROOT / "docs/final/artifacts/mkm12_75_formulas_ssot_v1_latest.json"
OUT = ROOT / "docs/final/artifacts/mkm_theory_formula_promotion_registry_v1_latest.json"

FORBIDDEN_PATTERNS = (
    r"dt\s*/\s*dx",
    r"역시간",
    r"통일장\s*완성",
)
SASANG_LANE = (
    "사상",
    "동역학",
    "마르코프",
    "켈리",
    "oracle",
    "오라클",
    "병증",
    "주역",
)
COMPRESSION_LANE = (
    "압축",
    "엔트로피",
    "패킹",
    "토큰",
    "무결성",
    "니트로",
    "해밀턴",
    "fft",
    "사원수",
    "한글",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _lane_for_entry(entry: dict, fact_ids: set[str]) -> dict[str, object]:
    slot_id = str(entry.get("id", ""))
    name = str(entry.get("name", ""))
    formula = str(entry.get("formula", ""))
    blob = f"{name} {formula}".lower()

    if any(re.search(p, blob, re.I) for p in FORBIDDEN_PATTERNS):
        return {
            "promotion_lane": "forbidden",
            "gate_script": None,
            "gate_artifact": None,
            "promotion_to_a_track_allowed": False,
            "note": "FORBIDDEN — no promotion path",
        }

    if slot_id in fact_ids or any(
        x in blob for x in ("gematria", "myeongni_d_out", "geumhwa_index")
    ):
        return {
            "promotion_lane": "repo_fact",
            "gate_script": "docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md",
            "gate_artifact": "repo_implemented_facts",
            "promotion_to_a_track_allowed": False,
            "note": "FACT path only; domain-scoped citation",
        }

    if any(k in name for k in SASANG_LANE):
        return {
            "promotion_lane": "sasang12_judge_btrack",
            "gate_script": "scripts/run_sasang12_promotion_candidate_chain_v1.py",
            "gate_artifact": "docs/final/artifacts/sasang12_promotion_candidate_gate_latest.json",
            "promotion_to_a_track_allowed": False,
            "note": "B-track sasang gate; human GO required",
        }

    if any(k in name for k in COMPRESSION_LANE):
        return {
            "promotion_lane": "compression_operational",
            "gate_script": "scripts/check_compression_narrative_fact_lock_v1.py",
            "gate_artifact": "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json",
            "promotion_to_a_track_allowed": False,
            "note": "Compression FACT lane separate from 75식 HYPO index",
        }

    return {
        "promotion_lane": "research_only",
        "gate_script": None,
        "gate_artifact": None,
        "promotion_to_a_track_allowed": False,
        "note": "HYPO index — no auto gate",
    }


def main() -> int:
    if not FORMULAS.is_file():
        raise SystemExit(f"missing {FORMULAS}")
    doc = json.loads(FORMULAS.read_text(encoding="utf-8"))
    fact_ids = {str(x.get("id", "")) for x in doc.get("repo_implemented_facts", [])}

    rows: list[dict[str, object]] = []
    lane_counts: dict[str, int] = {}
    for entry in doc.get("formulas", []):
        lane = _lane_for_entry(entry, fact_ids)
        lane_name = str(lane["promotion_lane"])
        lane_counts[lane_name] = lane_counts.get(lane_name, 0) + 1
        rows.append(
            {
                "slot": entry.get("slot"),
                "id": entry.get("id"),
                "name": entry.get("name"),
                "grade": entry.get("grade", "HYPO"),
                "has_formula_expr": bool(entry.get("formula")),
                **lane,
            }
        )

    payload = {
        "schema": "mkm_theory_formula_promotion_registry_v1",
        "generated_at_utc": utc_now(),
        "research_only": True,
        "promotion_to_a_track_allowed": False,
        "source_formulas": str(FORMULAS.relative_to(ROOT)).replace("\\", "/"),
        "unrecovered_slots": int(doc.get("unrecovered_slots", 0)),
        "documented_with_expr": int(doc.get("documented_with_expr", 0)),
        "lane_counts": lane_counts,
        "entries": rows,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "out": str(OUT),
                "entries": len(rows),
                "lane_counts": lane_counts,
                "documented_with_expr": payload["documented_with_expr"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
