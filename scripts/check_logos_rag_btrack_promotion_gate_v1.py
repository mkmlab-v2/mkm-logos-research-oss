#!/usr/bin/env python3
"""B-track Logos RAG promotion gate (L1 lab / L2 shadow ingest / L3 prod index blocked)."""
from __future__ import annotations

import argparse
import json
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "reports" / "constitution" / "btrack_pilot"
ART = ROOT / "docs/final/artifacts"
DEFAULT_OUT = ART / "logos_rag_btrack_promotion_gate_v1_latest.json"
ST_SQLITE = PILOT / "logos_vector_index_ann_lite_st_u_v1.sqlite"
BRIDGE = ART / "semantic_rag_bridge_insight_bundle_v1_latest.json"
FULL_AUTO = PILOT / "comp_logos_rag_full_auto_v1_latest.json"
EVAL_R3 = PILOT / "comp_logos_rag_retrieval_eval_r3_latest.json"
EVAL_R4 = PILOT / "comp_logos_rag_retrieval_eval_r4_latest.json"
DUAL_EVAL = PILOT / "comp_logos_rag_dual_gold_eval_v1_latest.json"
GOLD = ART / "logos_semantic_query_gold_human_v1.json"
MERGED_R6 = PILOT / "philosophy_lane_rag_pilot_r6_merged_q01_q12_ko_only_latest.json"
MERGED_R4 = PILOT / "philosophy_lane_rag_pilot_r4_merged_q01_q12_ko_latest.json"

# L1: B-track lab bundle freeze (infrastructure; not retrieval quality proof)
L1_MIN_BRIDGE = 12
L1_MIN_KO_MEAN = 0.33
L1_MIN_INDEX_ROWS = 30_000

# L2: Track C / premium bridge ingest (semantic quality bar)
L2_MIN_BRIDGE = 20
L2_MIN_WEAK_HIT3 = 0.20
L2_MIN_HUMAN_SIGNED = 8


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _index_rows(path: Path, eval_r3: dict[str, Any]) -> int:
    if isinstance(eval_r3.get("index_rows"), int) and eval_r3["index_rows"] > 0:
        return int(eval_r3["index_rows"])
    if not path.is_file():
        return 0
    con = sqlite3.connect(str(path))
    try:
        row = con.execute("SELECT COUNT(*) FROM logos_vec_stub").fetchone()
        return int(row[0]) if row else 0
    except sqlite3.Error:
        return 0
    finally:
        con.close()


def _profile_metric(eval_doc: dict[str, Any], mode: str, key: str) -> float | None:
    for p in eval_doc.get("profiles") or []:
        if isinstance(p, dict) and p.get("mode") == mode:
            v = p.get(key)
            return float(v) if isinstance(v, (int, float)) else None
    return None


def _dual_thematic_metric(dual_doc: dict[str, Any], key: str) -> float | None:
    return _profile_metric(dual_doc, "ko_improved_vs_thematic_gold", key)


def _gold_stats(gold: dict[str, Any]) -> dict[str, Any]:
    items = gold.get("items") or []
    filled = 0
    auto_top1 = 0
    human_signed = 0
    harness_filled = 0
    for it in items:
        if not isinstance(it, dict):
            continue
        g = it.get("gold_verse_ids_human") or []
        if g:
            filled += 1
        if it.get("gold_verse_ids_harness_top1"):
            harness_filled += 1
        st = str(it.get("adjudication_status") or "")
        if st == "auto_top1_from_pack_v1":
            auto_top1 += 1
        elif st in (
            "human_signed_v1",
            "commander_signed_v1",
            "commander_auto_thematic_v4_weak_v1",
            "commander_thematic_precision_v1",
            "commander_blend_v4_weak_pack_top5_v1",
            "commander_theology_primary_v1",
            "commander_harness_align_v1",
            "commander_retrieval_union_top1_v1",
        ):
            human_signed += 1
    status = str(gold.get("status") or "")
    signoff = str(gold.get("signoff") or "")
    dual_track = (
        status
        in (
            "commander_signed_dual_track_v1",
            "commander_thematic_precision_v1",
            "commander_direct_signoff_v1",
        )
        or signoff in ("commander_approved", "commander_direct_v1")
    )
    auto_gold = (
        not dual_track
        and (status == "auto_top1_from_pack_v1" or (auto_top1 >= filled and filled > 0))
    )
    return {
        "filled_n": filled,
        "auto_top1_n": auto_top1,
        "human_signed_n": human_signed,
        "harness_track_filled_n": harness_filled,
        "dual_track_signed": dual_track,
        "auto_gold_tainted": auto_gold,
    }


def _run_pytest() -> bool:
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_logos_rag_query_route_v1.py",
            "tests/test_semantic_rag_bridge_insight_bundle_schema_v1.py",
            "-q",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    return proc.returncode == 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--run-pytest", action="store_true")
    args = ap.parse_args()

    full = _load(FULL_AUTO)
    r3 = _load(EVAL_R3)
    r4 = _load(EVAL_R4)
    dual = _load(DUAL_EVAL)
    gold = _load(GOLD)
    bridge_doc = _load(BRIDGE)
    gstats = _gold_stats(gold)

    bridge_n = len(bridge_doc.get("rag_evidence") or [])
    ko_mean = _profile_metric(r3, "ko_baseline_top3", "mean_top1_cosine")
    if ko_mean is None:
        ko_mean = (r4.get("summary") or {}).get("mean_top1_ko_user_sim")
        if isinstance(ko_mean, (int, float)):
            ko_mean = float(ko_mean)
        else:
            ko_mean = None
    weak_hit3_source = "r3.ko_baseline_top3.gold_verse_ids_weak"
    weak_hit3 = _profile_metric(r3, "ko_baseline_top3", "weak_gold_hit_at_3_rate")
    weak_hit1 = _profile_metric(r3, "ko_baseline_top3", "weak_gold_hit_at_1_rate")
    if gstats.get("dual_track_signed") and dual:
        thematic_hit3 = _dual_thematic_metric(dual, "weak_gold_hit_at_3_rate")
        thematic_hit1 = _dual_thematic_metric(dual, "weak_gold_hit_at_1_rate")
        if thematic_hit3 is not None:
            weak_hit3 = thematic_hit3
            weak_hit3_source = "dual_gold_eval.ko_improved_vs_thematic_gold"
        if thematic_hit1 is not None:
            weak_hit1 = thematic_hit1
    index_rows = _index_rows(ST_SQLITE, r3)
    pytest_ok = _run_pytest() if args.run_pytest else None
    full_ok = bool(full.get("ok"))

    checks_l1 = {
        "full_auto_ok": full_ok,
        "st_index_rows_ge_min": index_rows >= L1_MIN_INDEX_ROWS,
        "bridge_evidence_ge_min": bridge_n >= L1_MIN_BRIDGE,
        "ko_mean_ge_min": ko_mean is not None and ko_mean >= L1_MIN_KO_MEAN,
        "merged_pilot_exists": MERGED_R6.is_file() or MERGED_R4.is_file(),
        "pytest_smoke": pytest_ok is not False if pytest_ok is not None else True,
    }
    l1_pass = all(checks_l1.values())

    checks_l2 = {
        "l1_passed": l1_pass,
        "bridge_evidence_ge_l2": bridge_n >= L2_MIN_BRIDGE,
        "weak_gold_hit_at_3_ge_min": weak_hit3 is not None and weak_hit3 >= L2_MIN_WEAK_HIT3,
        "human_signed_gold_ge_min": gstats["human_signed_n"] >= L2_MIN_HUMAN_SIGNED
        or (gstats["dual_track_signed"] and gstats["filled_n"] >= L2_MIN_HUMAN_SIGNED),
        "gold_not_auto_tainted": not gstats["auto_gold_tainted"],
    }
    l2_pass = all(checks_l2.values())

    doc: dict[str, Any] = {
        "schema": "logos_rag_btrack_promotion_gate_v1",
        "ts_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "metrics": {
            "bridge_rag_evidence_n": bridge_n,
            "ko_mean_top1": ko_mean,
            "weak_gold_hit_at_1": weak_hit1,
            "weak_gold_hit_at_3": weak_hit3,
            "weak_gold_hit_at_3_source": weak_hit3_source,
            "dual_eval_summary": dual.get("summary") if dual else None,
            "st_index_rows": index_rows,
            "gold_stats": gstats,
            "r4_human_hit_at_1": (r4.get("summary") or {}).get("human_hit_at_1"),
        },
        "tiers": {
            "L1_btrack_lab_bundle": {
                "label": "B-track lab bundle freeze (infrastructure)",
                "passed": l1_pass,
                "checks": checks_l1,
                "approval_ready": l1_pass,
                "note": "KO cosine + bridge count only; not thematic retrieval proof.",
            },
            "L2_track_c_shadow_ingest": {
                "label": "Track C / premium bridge ingest (semantic bar)",
                "passed": l2_pass,
                "checks": checks_l2,
                "approval_ready": l2_pass,
                "note": "Requires commander dual-track gold and thematic hit@3 (ko_improved vs gold_verse_ids_human).",
            },
            "L3_production_st_index": {
                "label": "Replace hash_stub ANN with ST U corpus on A-contract",
                "passed": False,
                "approval_ready": False,
                "checks": {"explicit_commander_only": True},
                "note": "Always blocked here; use record script with --tier L3 after explicit order.",
            },
        },
        "recommended_commander_action": (
            "ACK_L1_BTRACK_LAB_BUNDLE"
            if l1_pass and not l2_pass
            else ("ACK_L2_SHADOW_INGEST" if l2_pass else "HOLD_FIX_GATES")
        ),
        "track_wall": {
            "prophecy_promotion_gates_touch": False,
            "track_a_compression_touch": False,
            "use_gematria_4d_bridge": False,
            "a_track_auto_promotion": False,
        },
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "L1": l1_pass,
                "L2": l2_pass,
                "action": doc["recommended_commander_action"],
                "out": str(args.output_json),
            },
            ensure_ascii=False,
        )
    )
    return 0 if l1_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
