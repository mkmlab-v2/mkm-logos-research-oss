#!/usr/bin/env python3
"""B-track trial: Dan.2 hub seeds for empire_transition GraphRAG [HYPO][research_only]."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DEFAULT_CANDIDATES = ROOT / "docs/final/artifacts/bible_meaning_insight_candidates_latest.json"
DEFAULT_OUT = ROOT / "reports/logos_graphrag_2026_empire_transition_dan2_trial_v1_latest.json"
DEFAULT_FIXTURE = ROOT / "tests/fixtures/logos_topic_empire_transition_dan2_trial_v1.json"
DEFAULT_AUDIT = ROOT / "reports/logos_empire_transition_dan2_trial_audit_v1_latest.json"

TRIAL_SEEDS = ["Dan.2.10", "Dan.2.31"]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _candidate_meta(candidates_doc: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in candidates_doc.get("candidates") or []:
        if not isinstance(row, dict):
            continue
        nid = str(row.get("source_node_id") or "")
        if nid.startswith("aramaic::Dan.2."):
            vid = nid.replace("aramaic::", "")
            out[vid] = row
    return out


def build_router(*, candidates_doc: dict[str, Any]) -> dict[str, Any]:
    meta = _candidate_meta(candidates_doc)
    paths: list[dict[str, Any]] = []
    for vid in TRIAL_SEEDS:
        row = meta.get(vid) or {}
        paths.append(
            {
                "bridge_artifact": "docs/final/artifacts/bible_meaning_insight_candidates_latest.json",
                "path_id": f"path_dan2_{vid.replace('.', '_')}",
                "steps": [
                    "concept:empire_transition",
                    "function:wise_men_crisis",
                    "lemma:aramaic:chokmah_proxy",
                    f"verse:{vid}",
                ],
                "note_ko": (
                    f"제국 전환기 지혜자·궁정 위기 — {vid} "
                    f"[HYPO] hub_score={row.get('hub_score')} cluster={row.get('cluster_size')}"
                ),
                "match_score": int(float(row.get("hub_score") or 0.5) * 5),
            }
        )
    verse_ids = [f"aramaic::{v}" for v in TRIAL_SEEDS] + TRIAL_SEEDS
    return {
        "schema": "logos_subgraph_graphrag_router_v1",
        "version": "1.3.1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "query": "제국·체제 전환기 지혜자·상징 궁정 위기",
        "query_tokens": ["제국", "체제", "전환", "지혜자", "궁정", "위기"],
        "theme_lanes_active": ["empire_transition_trial"],
        "bridges_matched": 1,
        "paths": paths,
        "verse_ids": verse_ids,
        "trial_meta": {
            "schema": "logos_empire_transition_dan2_trial_v1",
            "promotion_status": "trial_only_not_in_6topic_fixture",
            "seed_verse_ids": TRIAL_SEEDS,
            "source_candidates": str(DEFAULT_CANDIDATES.relative_to(ROOT)).replace("\\", "/"),
        },
    }


def build_fixture() -> dict[str, Any]:
    return {
        "schema": "logos_topic_4d_resonance_topics_v1",
        "hypothesis_tier": "B",
        "research_only": True,
        "note": "Dan.2 trial — not merged into 18-seed SSOT fixture",
        "topics": [
            {
                "topic_id": "empire_transition_dan2_trial",
                "seed_verse_ids": TRIAL_SEEDS,
                "graphrag_ref": "reports/logos_graphrag_2026_empire_transition_dan2_trial_v1_latest.json",
            }
        ],
    }


def audit_router(*, router: dict[str, Any], fixture: dict[str, Any]) -> dict[str, Any]:
    from scripts.audit_logos_topic_graphrag_seed_retrieval_v1 import collect_router_verses, normalize_topic_verse_ref

    topic = (fixture.get("topics") or [{}])[0]
    seeds = [normalize_topic_verse_ref(v) for v in (topic.get("seed_verse_ids") or [])]
    router_verses = collect_router_verses(router)
    overlap = [s for s in seeds if s in router_verses]
    return {
        "schema": "logos_empire_transition_dan2_trial_audit_v1",
        "generated_at_utc": _utc_now(),
        "topic_id": topic.get("topic_id"),
        "seed_verse_ids": seeds,
        "seed_hit_count": len(overlap),
        "seed_router_overlap": overlap,
        "topic_pass": len(overlap) == len(seeds) and len(seeds) > 0,
        "router_verse_count": len(router_verses),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--candidates-json", type=Path, default=DEFAULT_CANDIDATES)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--fixture-json", type=Path, default=DEFAULT_FIXTURE)
    ap.add_argument("--audit-json", type=Path, default=DEFAULT_AUDIT)
    args = ap.parse_args()

    candidates = _read(args.candidates_json)
    router = build_router(candidates_doc=candidates)
    fixture = build_fixture()
    audit = audit_router(router=router, fixture=fixture)

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(router, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.fixture_json.write_text(json.dumps(fixture, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.audit_json.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": audit.get("topic_pass"),
                "seed_hits": f"{audit.get('seed_hit_count')}/{len(TRIAL_SEEDS)}",
                "out": str(args.out_json),
                "audit": str(args.audit_json),
            }
        )
    )
    return 0 if audit.get("topic_pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
