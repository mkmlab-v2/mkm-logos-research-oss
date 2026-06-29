#!/usr/bin/env python3
"""Cap profile × gold RAG regression — minimal cap promotion candidate ([HYPO]).

Rebuilds insight payloads per gold fixture item under each cap profile and checks
whether RAG gold hits are preserved vs baseline_production. Router gates unchanged.

  py scripts/build_mkm_ltm_insight_cap_gold_regression_v1.py
  py scripts/build_mkm_ltm_insight_cap_gold_regression_v1.py --strict
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_ROOT / "scripts"))

from build_mkm_ltm_insight_cap_ablation_bench_v1 import CAP_PROFILES  # noqa: E402
from build_logos_gold_query_eval_report_v1 import (  # noqa: E402
    DEFAULT_GOLD,
    _collect_rag_verses,
    _match_gold,
    normalize_verse_ref,
)
from mkm_ops_memory_index_lib_v1 import utc_now_iso  # noqa: E402

DEFAULT_OUT = SCRIPT_ROOT / "reports" / "mkm_ltm_insight_cap_gold_regression_v1_latest.json"
DEFAULT_BUNDLE = SCRIPT_ROOT / "docs/final/artifacts/semantic_rag_bridge_insight_bundle_v1_latest.json"
REPORT_DIR = SCRIPT_ROOT / "reports/magic_orb_insight_by_query"
PROFILE_ORDER = ("baseline_production", "tight", "minimal", "ultra_min")


def _profile_rank(profile_id: str) -> int:
    try:
        return PROFILE_ORDER.index(profile_id)
    except ValueError:
        return 99


def _count_tokens(text: str) -> int:
    try:
        import tiktoken

        return len(tiktoken.get_encoding("cl100k_base").encode(text))
    except Exception:  # noqa: BLE001
        return max(1, len(text) // 4)


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _load_module(name: str, rel: str) -> Any:
    path = SCRIPT_ROOT / rel
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _build_insight_for_caps(
    *,
    query: str,
    query_id: str,
    caps: dict[str, int],
    bundle: dict[str, Any],
    router: dict[str, Any] | None,
) -> dict[str, Any]:
    insight_mod = _load_module(
        "build_magic_orb_question_insight_payload_v1",
        "scripts/build_magic_orb_question_insight_payload_v1.py",
    )
    bloom_mod = _load_module(
        "build_magic_orb_graph_bloom_v1",
        "scripts/build_magic_orb_graph_bloom_v1.py",
    )
    ann_top = insight_mod._ann_top_verse_ids(list(bundle.get("rag_evidence") or []))
    bloom = bloom_mod.build_bloom(
        query=query,
        router=router,
        ann_top_verse_ids=ann_top,
        expand_graph=False,
        lod_node_cap=int(caps.get("lod_node_cap") or 48),
        lod_edge_cap=int(caps.get("lod_edge_cap") or 56),
    )
    return insight_mod.build_payload(
        query=query,
        query_id=query_id,
        bundle=bundle,
        chain=None,
        router=router,
        graph_bloom=bloom,
        caps=caps,
        shadow=None,
        digest=None,
        enrich_four_slot=False,
    )


def _rag_gold_row(insight: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]:
    gold_ids = [normalize_verse_ref(str(x)) for x in (item.get("gold_verse_ids") or [])]
    prefixes = [str(x) for x in (item.get("gold_verse_prefixes") or [])]
    rag_verses = _collect_rag_verses(insight)
    hits = _match_gold(rag_verses, gold_ids, prefixes)
    return {
        "rag_count": len(insight.get("rag_evidence") or []),
        "gold_hits": hits,
        "gold_hit_count": len(hits),
        "rag_has_gold": len(hits) > 0,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gold-json", type=Path, default=DEFAULT_GOLD)
    ap.add_argument("--bundle-json", type=Path, default=DEFAULT_BUNDLE)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--strict", action="store_true", help="Exit 1 if minimal regresses any gold RAG hit")
    args = ap.parse_args()

    gold_doc = _load_json(args.gold_json.resolve())
    if not gold_doc or gold_doc.get("schema") != "logos_gold_query_eval_v1":
        print("FAIL: invalid gold fixture", file=sys.stderr)
        return 1

    bundle = _load_json(args.bundle_json.resolve())
    if not bundle:
        print(f"FAIL: missing bundle: {args.bundle_json}", file=sys.stderr)
        return 1

    items = [x for x in (gold_doc.get("items") or []) if isinstance(x, dict)]
    required = [x for x in items if x.get("eval_tier") == "gold_required"]

    per_item: list[dict[str, Any]] = []
    regressions: list[str] = []
    skipped: list[str] = []
    profile_pass_counts: dict[str, int] = {pid: 0 for pid in CAP_PROFILES}
    profile_tokens: dict[str, list[int]] = {pid: [] for pid in CAP_PROFILES}

    for item in required:
        qid = str(item.get("id") or "")
        router_path = REPORT_DIR / f"router_{qid}_latest.json"
        router = _load_json(router_path)
        if not router:
            skipped.append(qid)
            continue

        query = str(item.get("query_ko") or "")
        profiles: dict[str, Any] = {}
        baseline_hits = 0
        for profile_id in PROFILE_ORDER:
            if profile_id not in CAP_PROFILES:
                continue
            caps = CAP_PROFILES[profile_id]
            insight = _build_insight_for_caps(
                query=query,
                query_id=qid,
                caps=caps,
                bundle=bundle,
                router=router,
            )
            row = _rag_gold_row(insight, item)
            serialized = json.dumps(insight, ensure_ascii=False, separators=(",", ":"))
            row["payload_tokens"] = _count_tokens(serialized)
            profiles[profile_id] = row
            profile_tokens[profile_id].append(int(row["payload_tokens"]))
            if profile_id == "baseline_production":
                baseline_hits = int(row["gold_hit_count"])

        preserved_by_profile: dict[str, bool] = {}
        for profile_id, row in profiles.items():
            hits = int(row["gold_hit_count"])
            ok_row = hits >= baseline_hits
            preserved_by_profile[profile_id] = ok_row
            if ok_row:
                profile_pass_counts[profile_id] += 1
            elif profile_id != "baseline_production" and baseline_hits > 0 and hits < baseline_hits:
                regressions.append(f"{qid}/{profile_id}: gold hits {hits} < baseline {baseline_hits}")

        per_item.append(
            {
                "id": qid,
                "query_ko": query,
                "router_present": True,
                "profiles": profiles,
                "baseline_gold_hit_count": baseline_hits,
                "preserved_vs_baseline": preserved_by_profile,
            }
        )

    evaluated = len(per_item)
    best_profile: str | None = None
    best_mean_tokens: int | None = None
    for profile_id in reversed(PROFILE_ORDER):
        if profile_id not in CAP_PROFILES:
            continue
        if profile_pass_counts.get(profile_id, 0) != evaluated or evaluated == 0:
            continue
        tokens = profile_tokens.get(profile_id) or []
        mean_tokens = int(sum(tokens) / max(1, len(tokens)))
        if best_profile is None or mean_tokens < int(best_mean_tokens or 10**9):
            best_profile = profile_id
            best_mean_tokens = mean_tokens

    minimal_preserved = profile_pass_counts.get("minimal", 0)
    promotion_candidate = evaluated > 0 and minimal_preserved == evaluated

    doc: dict[str, Any] = {
        "schema": "mkm_ltm_insight_cap_gold_regression_v1",
        "track": "B",
        "research_only": True,
        "hypothesis_tier": "B",
        "boundary_ack": "[HYPO] cap×gold RAG regression — not Track A promotion; router gates unchanged",
        "generated_at_utc": utc_now_iso(),
        "compare_profiles": list(PROFILE_ORDER),
        "gold_required_count": len(required),
        "evaluated_count": evaluated,
        "skipped_missing_router": skipped,
        "items": per_item,
        "aggregate": {
            "profile_pass_counts": profile_pass_counts,
            "minimal_cap_promotion_candidate": promotion_candidate,
            "best_cap_profile_under_gold_guard": best_profile,
            "best_cap_profile_mean_payload_tokens": best_mean_tokens,
            "rag_gold_regression_count": len(regressions),
            "note": "best_cap_profile = strictest caps with 12/12 RAG gold preserved; B-track ops only.",
        },
        "regressions": regressions,
        "policy": {
            "gating": "NON_GATING",
            "send_gate": "HOLD",
            "must_not_merge_with": ["track_a_compression", "live_trading_trigger"],
        },
        "reproduce": "py scripts/build_mkm_ltm_insight_cap_gold_regression_v1.py",
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"WROTE: {args.out}")
    print(
        f"evaluated={evaluated} best_profile={best_profile} "
        f"minimal_promotion={promotion_candidate} regressions={len(regressions)}"
    )
    if regressions:
        for err in regressions:
            print(f"  REGRESSION: {err}", file=sys.stderr)

    if args.strict and (regressions or not promotion_candidate):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
