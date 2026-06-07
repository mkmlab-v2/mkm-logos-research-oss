#!/usr/bin/env python3
"""Blind era prediction eval on non-synthetic historical gold ([HYPO], NON_GATING).

Uses the same ranking core as build_logos_chronology_dynamic_map_v1.py.
Excludes label_guided_seed; does not assert prophecy or trading signals.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from logos_chronology_eval_governance_v1 import assess_eval_governance
from logos_chronology_map_core_v1 import (
    POLICY,
    confidence_band,
    infer_tags_from_text,
    infer_tags_from_text_v2,
    load_json,
    rank_eras,
)
from logos_chronology_rag_tag_bridge_v1 import infer_tags_rag_assisted

ROOT = Path(__file__).resolve().parents[1]


def _rel_repo(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path.resolve()).replace("\\", "/")
DEFAULT_GOLD = ROOT / "docs/final/artifacts/fixtures/logos_chronology_historical_era_gold_v1.json"
DEFAULT_CHRONOLOGY = ROOT / "docs/final/artifacts/logos_chronology_v1_latest.json"
DEFAULT_OUT_ART = ROOT / "docs/final/artifacts/logos_chronology_era_blind_eval_v1_latest.json"
DEFAULT_OUT_REP = ROOT / "reports/logos_chronology_era_blind_eval_v1_latest.json"
DEFAULT_REVAL = ROOT / "docs/final/artifacts/logos_symbolic_revalidation_report_latest.json"
DEFAULT_HARDSET = ROOT / "docs/final/artifacts/news_observation_v1_blind_split_hardset_latest.jsonl"
SYNTHETIC_SOURCES = frozenset({"label_guided_seed", "manual_seed"})


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def _hit_at_k(pred_ids: list[str], gold: str, acceptable: list[str]) -> bool:
    pool = {gold, *acceptable}
    top = pred_ids[:3] if len(pred_ids) >= 3 else pred_ids
    return any(pid in pool for pid in top[:1]) if len(top) >= 1 else False


def _hit_at_3(pred_ids: list[str], gold: str, acceptable: list[str]) -> bool:
    pool = {gold, *acceptable}
    return any(pid in pool for pid in pred_ids[:3])


def _resolve_text_src(ev: dict[str, Any], text_source: str) -> str:
    if text_source == "headline_en":
        return str(ev.get("headline_en") or ev.get("canonical_text") or "")
    if text_source == "canonical_text":
        return str(ev.get("canonical_text") or "")
    return str(ev.get("canonical_text") or ev.get("headline_ko") or "")


def _merge_en_headlines(events: list[dict[str, Any]], sidecar_path: Path | None) -> int:
    if not sidecar_path or not sidecar_path.is_file():
        return 0
    sidecar = load_json(sidecar_path)
    by_id = {
        str(row.get("event_id") or ""): str(row.get("headline_en") or "")
        for row in (sidecar.get("headlines") or [])
        if row.get("event_id")
    }
    merged = 0
    for ev in events:
        eid = str(ev.get("event_id") or "")
        if eid in by_id and by_id[eid]:
            ev["headline_en"] = by_id[eid]
            merged += 1
    return merged


def _evaluate_event(
    chrono: dict[str, Any],
    ev: dict[str, Any],
    *,
    tag_mode: str,
    modern_boost: float,
    boost_policy: str = "global",
    graphrag_topics_json: Path | None = None,
    text_source: str = "headline_ko",
) -> dict[str, Any]:
    tags = list(ev.get("inferred_regime_tags") or [])
    rag_trace: dict[str, Any] | None = None
    text_src = _resolve_text_src(ev, text_source)
    tier = str(ev.get("tier") or "")
    if tag_mode == "text_blind" and text_src:
        tags = infer_tags_from_text(text_src)
    elif tag_mode in ("text_blind_v2", "text_blind_v2_no_hints") and text_src:
        tags = infer_tags_from_text_v2(text_src, event_tier=tier or None)
    elif tag_mode == "rag_assisted" and text_src:
        tags, rag_trace = infer_tags_rag_assisted(text_src, graphrag_topics_json=graphrag_topics_json)

    partition = str(ev.get("partition") or "") or None
    v2_modes = frozenset({"text_blind_v2", "text_blind_v2_no_hints"})
    ranking = rank_eras(
        chrono,
        tags,
        modern_boost=modern_boost,
        event_tier=tier,
        event_partition=partition,
        boost_policy=boost_policy,
        source_text=text_src if tag_mode in v2_modes else None,
        text_blind_v2=(tag_mode in v2_modes),
        text_blind_v2_era_hints=(tag_mode == "text_blind_v2"),
    )
    pred_ids = [str(r["era_id"]) for r in ranking]
    gold = str(ev.get("gold_era_id") or "")
    acceptable = [str(x) for x in (ev.get("acceptable_era_ids") or [])]
    top = ranking[0] if ranking else {}
    hit1_strict = bool(pred_ids) and pred_ids[0] == gold
    hit1_relaxed = _hit_at_k(pred_ids, gold, acceptable)
    hit3 = _hit_at_3(pred_ids, gold, acceptable)

    return {
        "event_id": ev.get("event_id"),
        "tier": ev.get("tier"),
        "as_of_date": ev.get("as_of_date"),
        "partition": ev.get("partition"),
        "tag_mode": tag_mode,
        "text_source": text_source,
        "text_preview": text_src[:120] if text_src else None,
        "inferred_regime_tags": tags,
        "gold_era_id": gold,
        "acceptable_era_ids": acceptable,
        "predicted_top1_era_id": pred_ids[0] if pred_ids else None,
        "predicted_top3_era_ids": pred_ids[:3],
        "top1_score": top.get("score"),
        "confidence_band": confidence_band(float(top.get("score") or 0)),
        "hit_at_1_strict": hit1_strict,
        "hit_at_1_relaxed": hit1_relaxed,
        "hit_at_3": hit3,
        "is_synthetic_source": bool(ev.get("is_synthetic_source")),
        "observation_id": ev.get("observation_id"),
        "source_id": ev.get("source_id"),
        "rag_trace": rag_trace,
    }


def _rate(rows: list[dict[str, Any]], key: str) -> float | None:
    vals = [r for r in rows if r.get(key) is not None]
    if not vals:
        return None
    hits = sum(1 for r in vals if r.get(key))
    return round(hits / len(vals), 6)


def _append_revalidation(reval_path: Path, block: dict[str, Any], key: str) -> None:
    if not reval_path.is_file():
        return
    doc = load_json(reval_path)
    doc[key] = block
    doc["non_synthetic_era_blind_appended_at_utc"] = _now()
    reval_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gold-json", type=Path, default=DEFAULT_GOLD)
    ap.add_argument("--chronology-json", type=Path, default=DEFAULT_CHRONOLOGY)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT_ART)
    ap.add_argument("--report-json", type=Path, default=DEFAULT_OUT_REP)
    ap.add_argument("--append-revalidation", type=Path, default=None, help="Patch logos_symbolic_revalidation_report")
    ap.add_argument(
        "--revalidation-key",
        type=str,
        default="non_synthetic_era_blind_eval_v1",
        help="JSON key under revalidation report for this eval summary",
    )
    ap.add_argument("--include-hardset-news", action="store_true", help="Add hardset news rows (non-synthetic only)")
    ap.add_argument("--hardset-jsonl", type=Path, default=DEFAULT_HARDSET)
    ap.add_argument(
        "--tag-mode",
        choices=["gold_tags", "text_blind", "text_blind_v2", "text_blind_v2_no_hints", "rag_assisted"],
        default="gold_tags",
        help="gold_tags=fixture tags; text_blind=keyword v1; text_blind_v2=KO+narrative hints; "
        "text_blind_v2_no_hints=KO keywords only (era hint ablation); rag_assisted=text_blind+GraphRAG",
    )
    ap.add_argument(
        "--graphrag-topics-json",
        type=Path,
        default=ROOT / "reports/logos_topic_graphrag_seed_retrieval_v1_latest.json",
        help="GraphRAG topic catalog for rag_assisted mode",
    )
    ap.add_argument(
        "--modern-boost",
        type=float,
        default=0.0,
        help="Score boost for modern_observational_field when tags present (default 0.0 per AB v1)",
    )
    ap.add_argument(
        "--boost-policy",
        choices=["global", "tier_v1", "tier_v2_locked_eval"],
        default="global",
        help="tier_v1: narrative boost off; tier_v2_locked_eval: +locked_eval judges/modern dampen",
    )
    ap.add_argument(
        "--min-human-override-ratio",
        type=float,
        default=0.10,
        help="text_blind: warn if human_override ratio below this when heuristic gold present",
    )
    ap.add_argument(
        "--text-source",
        choices=["headline_ko", "headline_en", "canonical_text"],
        default="headline_ko",
        help="Which event text field to feed tag inference (headline_en for EN-only OOV probe).",
    )
    ap.add_argument(
        "--en-headlines-json",
        type=Path,
        default=None,
        help="Sidecar mapping event_id -> headline_en merged into gold events before eval.",
    )
    ap.add_argument("--skip-governance", action="store_true", help="Disable self-match governance gate")
    args = ap.parse_args()

    gold_path = args.gold_json if args.gold_json.is_absolute() else ROOT / args.gold_json
    chrono_path = args.chronology_json if args.chronology_json.is_absolute() else ROOT / args.chronology_json
    out_art = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    out_rep = args.report_json if args.report_json.is_absolute() else ROOT / args.report_json

    if not gold_path.is_file():
        print(f"MISSING: {gold_path}", file=sys.stderr)
        return 2
    if not chrono_path.is_file():
        print(f"MISSING: {chrono_path}", file=sys.stderr)
        return 2

    gold_doc = load_json(gold_path)
    chrono = load_json(chrono_path)
    excluded = set(gold_doc.get("excluded_source_ids") or list(SYNTHETIC_SOURCES))

    events: list[dict[str, Any]] = list(gold_doc.get("events") or [])
    en_sidecar = args.en_headlines_json
    if en_sidecar is not None and not en_sidecar.is_absolute():
        en_sidecar = ROOT / en_sidecar
    n_en_merged = _merge_en_headlines(events, en_sidecar)
    if args.include_hardset_news and gold_doc.get("schema") != "logos_chronology_hardset_news_era_gold_v1":
        hardset = args.hardset_jsonl if args.hardset_jsonl.is_absolute() else ROOT / args.hardset_jsonl
        for row in _load_jsonl(hardset):
            sid = str(row.get("source_id") or "")
            if sid in excluded:
                continue
            text = str(row.get("canonical_text") or "")
            ev = {
                "event_id": f"news-{row.get('observation_id', 'x')}",
                "tier": "news_hardset",
                "as_of_date": str(row.get("as_of_utc") or "")[:10],
                "partition": row.get("dataset_partition") or "train_holdout",
                "canonical_text": text,
                "headline_ko": text[:120],
                "inferred_regime_tags": infer_tags_from_text(text),
                "gold_era_id": "modern_observational_field",
                "acceptable_era_ids": ["modern_observational_field", "judges_risk_cycle"],
                "observation_id": row.get("observation_id"),
                "source_id": sid,
                "is_synthetic_source": False,
                "gold_provisional": True,
            }
            events.append(ev)

    boost = float(args.modern_boost)
    policy = str(args.boost_policy)
    graphrag_path = (
        args.graphrag_topics_json
        if args.graphrag_topics_json.is_absolute()
        else ROOT / args.graphrag_topics_json
    )
    results = [
        _evaluate_event(
            chrono,
            ev,
            tag_mode=args.tag_mode,
            modern_boost=boost,
            boost_policy=policy,
            graphrag_topics_json=graphrag_path if args.tag_mode == "rag_assisted" else None,
            text_source=str(args.text_source),
        )
        for ev in events
    ]
    non_syn = [r for r in results if not r.get("is_synthetic_source")]
    locked = [r for r in non_syn if r.get("partition") == "locked_eval"]
    macro = [r for r in non_syn if r.get("tier") == "macro_landmark"]
    narrative = [r for r in non_syn if r.get("tier") == "biblical_narrative"]

    summary = {
        "n_events": len(results),
        "n_non_synthetic": len(non_syn),
        "n_synthetic_excluded_by_fixture": len(excluded),
        "hit_at_1_strict": _rate(non_syn, "hit_at_1_strict"),
        "hit_at_1_relaxed": _rate(non_syn, "hit_at_1_relaxed"),
        "hit_at_3": _rate(non_syn, "hit_at_3"),
        "locked_eval_hit_at_1_strict": _rate(locked, "hit_at_1_strict"),
        "macro_landmark_hit_at_1_strict": _rate(macro, "hit_at_1_strict"),
        "narrative_hit_at_1_strict": _rate(narrative, "hit_at_1_strict"),
        "tag_mode": args.tag_mode,
        "text_source": args.text_source,
    }

    status = "ok"
    min_hit = 0.35
    if summary["hit_at_1_strict"] is not None and summary["hit_at_1_strict"] < min_hit:
        status = "warning"
    if summary["n_non_synthetic"] == 0:
        status = "fail"

    governance: dict[str, Any] = {}
    if not args.skip_governance:
        governance = assess_eval_governance(
            gold_doc,
            args.tag_mode,
            summary,
            min_human_override_ratio=float(args.min_human_override_ratio),
        )
        if governance.get("status") == "warning" and status == "ok":
            status = "warning"

    known = [
        f"modern_observational_field boost policy={policy} base={boost} "
        f"(tier_v1/v2 block narrative boost; tier_v2 dampens modern on locked_eval risk cluster).",
        "gold_tags mode uses operator-supplied tags (upper bound on tag extraction quality).",
        "text_blind mode uses keyword heuristics only; no RAG retrieval in this eval."
        if args.tag_mode != "rag_assisted"
        else "rag_assisted merges text_blind tags with offline GraphRAG topic-router enrichment (PoC; not live LLM).",
        "Does not measure price-direction prophecy; era alignment only.",
    ]
    known.extend(governance.get("limitation_lines") or [])

    doc: dict[str, Any] = {
        "schema": "logos_chronology_era_blind_eval_v1",
        "generated_at_utc": _now(),
        "policy": POLICY,
        "hypothesis_tier": "[HYPO]",
        "status": status,
        "inputs": {
            "gold_json": _rel_repo(gold_path),
            "chronology_json": _rel_repo(chrono_path),
            "tag_mode": args.tag_mode,
            "text_source": args.text_source,
            "en_headlines_json": _rel_repo(en_sidecar) if en_sidecar else None,
            "n_en_headlines_merged": n_en_merged,
            "modern_boost": boost,
            "boost_policy": policy,
            "include_hardset_news": args.include_hardset_news,
            "excluded_source_ids": sorted(excluded),
            "graphrag_topics_json": _rel_repo(graphrag_path) if args.tag_mode == "rag_assisted" else None,
        },
        "summary": summary,
        "governance": governance or None,
        "known_limitations": known,
        "rows": results,
    }

    out_art.parent.mkdir(parents=True, exist_ok=True)
    out_rep.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    out_art.write_text(payload, encoding="utf-8")
    out_rep.write_text(payload, encoding="utf-8")

    if args.append_revalidation:
        rev = args.append_revalidation if args.append_revalidation.is_absolute() else ROOT / args.append_revalidation
        _append_revalidation(
            rev,
            {
                k: doc[k]
                for k in ("schema", "generated_at_utc", "status", "summary", "governance", "known_limitations")
            },
            args.revalidation_key,
        )

    print(f"WROTE: {out_art}")
    print(
        f"status={status} n={summary['n_non_synthetic']} hit@1={summary['hit_at_1_strict']} "
        f"hit@1_relaxed={summary['hit_at_1_relaxed']} hit@3={summary['hit_at_3']}"
    )
    return 0 if status != "fail" else 2


if __name__ == "__main__":
    import sys

    raise SystemExit(main())
