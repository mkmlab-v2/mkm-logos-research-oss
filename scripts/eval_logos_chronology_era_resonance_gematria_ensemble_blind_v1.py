#!/usr/bin/env python3
"""[HYPO] Resonance vote + gematria + keyword ensemble era blind eval (NON_GATING).

Fuses three B-track signals on the same 47-event historical gold:
  1) LogosEncoder cosine top-k -> sim-weighted era votes (verse_ref map)
  2) Resonance Hebrew pool -> gematria 4D centroid L2 score
  3) text_blind_v2 keyword tags -> rank_eras score (RQ-032 axis)

Reports weight presets + RRF; does not promote Track A or MS headline metrics.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eval_logos_chronology_era_logos_resonance_gematria_blind_v1 import (  # noqa: E402
    _build_corpus_embeddings,
    _era_votes_from_hits,
    _top_k_resonance,
)
from logos_chronology_gematria_core_v1 import (  # noqa: E402
    build_era_profiles,
    build_verse_to_eras,
    filter_gold_events,
    fuse_weighted_score_maps,
    gematria_bundle,
    load_json,
    load_verse_index,
    rank_eras_by_gematria_distance,
    rank_eras_by_score_map,
    reciprocal_rank_fusion,
    rel_repo,
    row_hit_fields,
    scores_from_gematria_ranking,
    scores_from_keyword_ranking,
    sim_weighted_era_scores,
    summarize_hits,
    utc_now,
)
from logos_chronology_map_core_v1 import POLICY, infer_tags_from_text, infer_tags_from_text_v2, rank_eras  # noqa: E402
from tools.core.logos_corpus_loader import default_hebrew_greek_jsonl  # noqa: E402
from tools.core.logos_encoder_gpu import LogosEncoder  # noqa: E402

DEFAULT_GOLD = ROOT / "docs/final/artifacts/fixtures/logos_chronology_historical_era_gold_v1.json"
DEFAULT_CHRONOLOGY = ROOT / "docs/final/artifacts/logos_chronology_v1_latest.json"
DEFAULT_CORPUS = default_hebrew_greek_jsonl(ROOT)
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_chronology_era_resonance_gematria_ensemble_blind_eval_v1_latest.json"
DEFAULT_INSIGHTS = ROOT / "reports/logos_chronology_era_resonance_gematria_ensemble_insights_v1_latest.json"
DEFAULT_MODERN_BOOST = 0.08

ENSEMBLE_PRESETS: list[dict[str, Any]] = [
    {"mode": "vote_sim_only", "vote_w": 1.0, "gematria_w": 0.0, "keyword_w": 0.0},
    {"mode": "gematria_only", "vote_w": 0.0, "gematria_w": 1.0, "keyword_w": 0.0},
    {"mode": "keyword_only", "vote_w": 0.0, "gematria_w": 0.0, "keyword_w": 1.0, "keyword_v2": False},
    {"mode": "keyword_v2_only", "vote_w": 0.0, "gematria_w": 0.0, "keyword_w": 1.0, "keyword_v2": True},
    {"mode": "ensemble_vote_gem_50_50", "vote_w": 0.5, "gematria_w": 0.5, "keyword_w": 0.0},
    {"mode": "ensemble_three_25_25_50", "vote_w": 0.25, "gematria_w": 0.25, "keyword_w": 0.5},
    {"mode": "ensemble_three_20_20_60", "vote_w": 0.2, "gematria_w": 0.2, "keyword_w": 0.6},
    {"mode": "ensemble_three_33_33_34", "vote_w": 0.33, "gematria_w": 0.33, "keyword_w": 0.34},
]


def _event_query_text(ev: dict[str, Any]) -> str:
    """Match eval_logos_chronology_era_blind_v1 text_source=headline_ko resolution."""
    return str(ev.get("canonical_text") or ev.get("headline_ko") or "")


def _evaluate_mode(
    *,
    mode: str,
    events: list[dict[str, Any]],
    profiles: list[dict[str, Any]],
    chrono: dict[str, Any],
    verse_index: dict[str, dict[str, str]],
    verse_to_eras: dict[str, list[str]],
    encoder: LogosEncoder,
    verse_ids: list[str],
    embeddings: np.ndarray,
    device: str,
    top_k: int,
    vote_w: float,
    gematria_w: float,
    keyword_w: float,
    modern_boost: float,
    keyword_v2: bool,
    use_rrf: bool,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for ev in events:
        headline = _event_query_text(ev)
        tier = str(ev.get("tier") or "")
        partition = str(ev.get("partition") or "")
        hits = _top_k_resonance(
            encoder,
            headline,
            verse_ids,
            embeddings,
            device=device,
            top_k=top_k,
        )
        hebrew_parts = []
        for h in hits:
            entry = verse_index.get(str(h["verse_id"]) or "")
            if entry and entry.get("logos_text"):
                hebrew_parts.append(str(entry["logos_text"]))
        pool = " ".join(hebrew_parts).strip()
        bundle = gematria_bundle(pool) if pool else gematria_bundle(headline)
        gem_rank = rank_eras_by_gematria_distance(bundle["vector_4d"], profiles)
        vote_scores = sim_weighted_era_scores(hits, verse_to_eras)
        gem_scores = scores_from_gematria_ranking(gem_rank)
        if keyword_v2:
            tags = infer_tags_from_text_v2(headline, event_tier=tier or None)
            kw_rank = rank_eras(
                chrono,
                tags,
                modern_boost=modern_boost,
                event_tier=tier or None,
                event_partition=partition or None,
                boost_policy="tier_v2_locked_eval",
                source_text=headline,
                text_blind_v2=True,
            )
        else:
            tags = infer_tags_from_text(headline)
            kw_rank = rank_eras(
                chrono,
                tags,
                modern_boost=modern_boost,
                event_tier=tier or None,
                event_partition=partition or None,
                boost_policy="tier_v2_locked_eval",
            )
        kw_scores = scores_from_keyword_ranking(kw_rank)
        if use_rrf:
            pred_ids = reciprocal_rank_fusion(
                [
                    [str(r["era_id"]) for r in rank_eras_by_score_map(vote_scores, profiles)],
                    [str(r["era_id"]) for r in gem_rank],
                    [str(r["era_id"]) for r in kw_rank],
                ]
            )
        else:
            fused = fuse_weighted_score_maps(
                profiles,
                (vote_scores, vote_w),
                (gem_scores, gematria_w),
                (kw_scores, keyword_w),
            )
            pred_ids = [str(r["era_id"]) for r in rank_eras_by_score_map(fused, profiles)]
        gold_id = str(ev.get("gold_era_id") or "")
        acceptable = [str(x) for x in (ev.get("acceptable_era_ids") or [])]
        hits_out = dict(row_hit_fields(pred_ids, gold_id, acceptable))
        vote_top = sorted(_era_votes_from_hits(hits, verse_to_eras).items(), key=lambda x: (-x[1], x[0]))[:3]
        top_label = next((p["label_ko"] for p in profiles if p["era_id"] == pred_ids[0]), pred_ids[0] if pred_ids else "")
        insight_ko = (
            f"[HYPO] {mode} → {top_label} ({pred_ids[0] if pred_ids else 'none'}). "
            f"tags={tags[:4]}. NON_GATING."
        )
        rows.append(
            {
                "event_id": ev.get("event_id"),
                "tier": tier,
                "partition": partition,
                "mode": mode,
                "query_headline_ko": headline[:160],
                "inferred_tags": tags,
                "resonance_top1_verse": hits[0]["verse_id"] if hits else None,
                "era_vote_top3": [{"era_id": e, "votes": v} for e, v in vote_top],
                "gematria_top1_era_id": gem_rank[0]["era_id"] if gem_rank else None,
                "keyword_top1_era_id": kw_rank[0]["era_id"] if kw_rank else None,
                "gold_era_id": gold_id,
                "acceptable_era_ids": acceptable,
                **hits_out,
                "insight_ko": insight_ko,
            }
        )
    summary = summarize_hits(rows)
    summary["mode"] = mode
    summary["vote_w"] = vote_w
    summary["gematria_w"] = gematria_w
    summary["keyword_w"] = keyword_w
    summary["keyword_v2"] = keyword_v2
    summary["use_rrf"] = use_rrf
    return {"summary": summary, "rows": rows}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gold-json", type=Path, default=DEFAULT_GOLD)
    ap.add_argument("--chronology-json", type=Path, default=DEFAULT_CHRONOLOGY)
    ap.add_argument("--corpus-jsonl", type=Path, default=DEFAULT_CORPUS)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--insights-json", type=Path, default=DEFAULT_INSIGHTS)
    ap.add_argument("--top-k", type=int, default=8)
    ap.add_argument("--chunk-size", type=int, default=512)
    ap.add_argument("--corpus-limit", type=int, default=None)
    args = ap.parse_args()

    gold_path = args.gold_json if args.gold_json.is_absolute() else ROOT / args.gold_json
    chrono_path = args.chronology_json if args.chronology_json.is_absolute() else ROOT / args.chronology_json
    corpus = args.corpus_jsonl if args.corpus_jsonl.is_absolute() else ROOT / args.corpus_jsonl
    out = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    insights_out = args.insights_json if args.insights_json.is_absolute() else ROOT / args.insights_json

    for p in (gold_path, chrono_path, corpus):
        if not p.is_file():
            print(f"MISSING: {p}", file=sys.stderr)
            return 2

    try:
        import torch
    except ImportError:
        print("PyTorch required for LogosEncoder", file=sys.stderr)
        return 1

    device = "cuda" if torch.cuda.is_available() else "cpu"
    encoder = LogosEncoder().eval()
    gold = load_json(gold_path)
    chrono = load_json(chrono_path)
    verse_index = load_verse_index(corpus)
    profiles = build_era_profiles(chrono, verse_index)
    verse_to_eras = build_verse_to_eras(chrono)
    verse_ids, embeddings = _build_corpus_embeddings(
        encoder,
        corpus,
        verse_index,
        device=device,
        chunk_size=max(32, int(args.chunk_size)),
        limit=args.corpus_limit,
    )
    if embeddings.shape[0] == 0:
        print("Empty corpus embeddings", file=sys.stderr)
        return 2

    events = filter_gold_events(gold)
    top_k = max(1, int(args.top_k))
    modern_boost = float(DEFAULT_MODERN_BOOST)
    mode_results: dict[str, Any] = {}
    for preset in ENSEMBLE_PRESETS:
        mode_results[preset["mode"]] = _evaluate_mode(
            mode=str(preset["mode"]),
            events=events,
            profiles=profiles,
            chrono=chrono,
            verse_index=verse_index,
            verse_to_eras=verse_to_eras,
            encoder=encoder,
            verse_ids=verse_ids,
            embeddings=embeddings,
            device=device,
            top_k=top_k,
            vote_w=float(preset["vote_w"]),
            gematria_w=float(preset["gematria_w"]),
            keyword_w=float(preset["keyword_w"]),
            modern_boost=modern_boost,
            keyword_v2=bool(preset.get("keyword_v2", False)),
            use_rrf=False,
        )
    mode_results["rrf_vote_gem_keyword"] = _evaluate_mode(
        mode="rrf_vote_gem_keyword",
        events=events,
        profiles=profiles,
        chrono=chrono,
        verse_index=verse_index,
        verse_to_eras=verse_to_eras,
        encoder=encoder,
        verse_ids=verse_ids,
        embeddings=embeddings,
        device=device,
        top_k=top_k,
        vote_w=0.0,
        gematria_w=0.0,
        keyword_w=0.0,
        modern_boost=modern_boost,
        keyword_v2=False,
        use_rrf=True,
    )

    leaderboard = sorted(
        [
            {
                "mode": name,
                **res["summary"],
            }
            for name, res in mode_results.items()
        ],
        key=lambda x: (
            -(float(x.get("locked_eval_hit_at_1_strict") or 0.0)),
            -(float(x.get("hit_at_1_strict") or 0.0)),
            str(x.get("mode") or ""),
        ),
    )

    payload: dict[str, Any] = {
        "schema": "logos_chronology_era_resonance_gematria_ensemble_blind_eval_v1",
        "generated_at_utc": utc_now(),
        "hypothesis_tier": "[HYPO]",
        "research_only": True,
        "policy": POLICY,
        "method_ko": (
            "Logos공명 sim-weight vote + resonance-pool gematria 4D + text_blind keyword rank_eras "
            "(keyword_only=text_blind v1 + tier_v2_locked_eval, MS 9.1% 축) 가중합 또는 RRF"
        ),
        "inputs": {
            "gold_json": rel_repo(ROOT, gold_path),
            "chronology_json": rel_repo(ROOT, chrono_path),
            "corpus_jsonl": rel_repo(ROOT, corpus),
            "n_corpus_verses_encoded": int(embeddings.shape[0]),
            "top_k": top_k,
            "device": device,
        },
        "ensemble_presets": ENSEMBLE_PRESETS + [{"mode": "rrf_vote_gem_keyword", "use_rrf": True}],
        "leaderboard": leaderboard,
        "mode_evaluations": mode_results,
        "compare_axes": {
            "keyword_text_blind_ms_public_locked_eval_hit_at_1_strict": 0.090909,
            "logos_resonance_gematria_hit_at_1_strict": 0.021277,
            "tag_anchor_gematria_hit_at_1_strict": 0.021277,
        },
        "known_limitations": [
            "Ensemble tuning on same 47-event gold — no fresh holdout; locked_eval is report-only.",
            "keyword_w>0 reuses tier_v2 rank_eras — not independent of RQ-032 MS baseline path.",
            "Does not change SEND_GATE, Track A, or live trading.",
        ],
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    best = leaderboard[0] if leaderboard else {}
    insight_doc = {
        "schema": "logos_chronology_era_resonance_gematria_ensemble_insights_v1",
        "generated_at_utc": payload["generated_at_utc"],
        "hypothesis_tier": "[HYPO]",
        "source_eval": rel_repo(ROOT, out),
        "leaderboard_top5": leaderboard[:5],
        "best_mode": best.get("mode"),
        "sample_rows": mode_results.get(str(best.get("mode") or ""), {}).get("rows", [])[:6],
    }
    insights_out.parent.mkdir(parents=True, exist_ok=True)
    insights_out.write_text(json.dumps(insight_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "output": rel_repo(ROOT, out),
                "insights": rel_repo(ROOT, insights_out),
                "best_mode": best.get("mode"),
                "best_locked_eval_hit_at_1_strict": best.get("locked_eval_hit_at_1_strict"),
                "best_hit_at_1_strict": best.get("hit_at_1_strict"),
                "keyword_only_locked": next(
                    (
                        m.get("locked_eval_hit_at_1_strict")
                        for m in leaderboard
                        if m.get("mode") == "keyword_only"
                    ),
                    None,
                ),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
