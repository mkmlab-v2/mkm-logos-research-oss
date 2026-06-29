#!/usr/bin/env python3
"""[HYPO] Gematria + 4D-bridge era blind eval on historical gold (NON_GATING).

Maps macro history headlines -> inferred tags -> Hebrew anchor pool -> gematria 4D vector,
then ranks Logos chronology eras by L2 distance to era verse-ref centroids.

Does NOT use KOSPI, price direction, or Track A gates. Korean-only headlines score 0 gematria
without tag anchors — documented in output.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from logos_chronology_map_core_v1 import (  # noqa: E402
    POLICY,
    infer_tags_from_text_v2,
    load_json,
)
from scripts.core.gematria_engine import build_gematria_metadata  # noqa: E402
from scripts.core.gematria_to_4d_bridge import build_gematria_4d_bridge  # noqa: E402
from tools.core.logos_corpus_loader import default_hebrew_greek_jsonl, verse_logos_text  # noqa: E402

DEFAULT_GOLD = ROOT / "docs/final/artifacts/fixtures/logos_chronology_historical_era_gold_v1.json"
DEFAULT_CHRONOLOGY = ROOT / "docs/final/artifacts/logos_chronology_v1_latest.json"
DEFAULT_CORPUS = default_hebrew_greek_jsonl(ROOT)
DEFAULT_OUT_ART = ROOT / "docs/final/artifacts/logos_chronology_era_gematria_blind_eval_v1_latest.json"
DEFAULT_OUT_INSIGHTS = ROOT / "reports/logos_chronology_era_gematria_insights_v1_latest.json"
SYNTHETIC_SOURCES = frozenset({"label_guided_seed", "manual_seed"})


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path.resolve())


def _load_verse_index(corpus: Path) -> dict[str, dict[str, str]]:
    index: dict[str, dict[str, str]] = {}
    if not corpus.is_file():
        return index
    for line in corpus.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(rec, dict):
            continue
        vid = str(rec.get("verse_id") or "").strip()
        if not vid:
            continue
        he = str(rec.get("text_hebrew") or "").strip()
        gr = str(rec.get("text_greek") or "").strip()
        logos = " ".join(x for x in (he, gr) if x).strip()
        if not logos:
            logos = verse_logos_text(rec)
        payload = {"logos_text": logos, "text_hebrew": he, "text_greek": gr}
        index[vid] = payload
        if vid.startswith("aramaic::"):
            index[vid.split("::", 1)[1]] = payload
    return index


def _resolve_ref(ref: str, verse_index: dict[str, dict[str, str]]) -> str:
    ref = str(ref or "").strip()
    if not ref:
        return ""
    entry = verse_index.get(ref)
    if entry is None and "::" in ref:
        entry = verse_index.get(ref.split("::", 1)[1])
    if not entry:
        return ""
    return str(entry.get("logos_text") or "")


def _vec4(meta: dict[str, int]) -> dict[str, float]:
    bridge = build_gematria_4d_bridge(gematria_metadata=meta)
    vec = bridge.get("vector_4d") or {}
    return {
        "S": float(vec.get("S", 0.25)),
        "L": float(vec.get("L", 0.25)),
        "K": float(vec.get("K", 0.25)),
        "M": float(vec.get("M", 0.25)),
    }


def _l2(a: dict[str, float], b: dict[str, float]) -> float:
    return math.sqrt(sum((float(a[k]) - float(b[k])) ** 2 for k in ("S", "L", "K", "M")))


def _mean_vec(vectors: list[dict[str, float]]) -> dict[str, float]:
    if not vectors:
        return {"S": 0.25, "L": 0.25, "K": 0.25, "M": 0.25}
    out = {"S": 0.0, "L": 0.0, "K": 0.0, "M": 0.0}
    for v in vectors:
        for k in out:
            out[k] += float(v[k])
    n = float(len(vectors))
    return {k: round(out[k] / n, 6) for k in out}


def _gematria_bundle(text: str) -> dict[str, Any]:
    meta = build_gematria_metadata(
        raw_text=text,
        compressed_text=text,
        reconstructed_text=text,
    )
    bridge = build_gematria_4d_bridge(gematria_metadata=meta)
    return {
        "text_preview": text[:120],
        "gematria": meta,
        "vector_4d": _vec4(meta),
        "state16": bridge.get("state16"),
        "hebrew_chars": int(meta.get("raw_hebrew_chars") or 0),
        "greek_chars": int(meta.get("raw_greek_chars") or 0),
        "combined_sum": int(meta.get("raw_combined_sum") or 0),
    }


def _build_era_profiles(chrono: dict[str, Any], verse_index: dict[str, dict[str, str]]) -> list[dict[str, Any]]:
    profiles: list[dict[str, Any]] = []
    for era in chrono.get("eras") or []:
        if not isinstance(era, dict):
            continue
        eid = str(era.get("era_id") or "")
        verse_texts: list[str] = []
        for ref in era.get("verse_refs") or []:
            t = _resolve_ref(str(ref), verse_index)
            if t:
                verse_texts.append(t)
        verse_vecs = [_gematria_bundle(t)["vector_4d"] for t in verse_texts]
        concat = " ".join(verse_texts)
        bundle = _gematria_bundle(concat) if concat else _gematria_bundle(str(era.get("label_ko") or eid))
        profiles.append(
            {
                "era_id": eid,
                "label_ko": str(era.get("label_ko") or eid),
                "n_verse_refs": len(era.get("verse_refs") or []),
                "n_verse_texts_resolved": len(verse_texts),
                "obs_tags": [str(t) for t in (era.get("regime_tags_observational") or [])],
                "centroid_4d": _mean_vec(verse_vecs) if verse_vecs else bundle["vector_4d"],
                "era_gematria": bundle,
            }
        )
    return profiles


def _build_tag_hebrew_anchors(chrono: dict[str, Any], verse_index: dict[str, dict[str, str]]) -> dict[str, str]:
    anchors: dict[str, str] = {}
    for era in chrono.get("eras") or []:
        if not isinstance(era, dict):
            continue
        obs = [str(t) for t in (era.get("regime_tags_observational") or [])]
        if not obs:
            continue
        snippets: list[str] = []
        for ref in era.get("verse_refs") or []:
            t = _resolve_ref(str(ref), verse_index)
            if t:
                snippets.append(t)
                break
        if not snippets:
            continue
        for tag in obs:
            anchors.setdefault(tag, snippets[0])
    return anchors


def _rank_eras_by_gematria_distance(
    event_vec: dict[str, float],
    profiles: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    ranked: list[dict[str, Any]] = []
    for p in profiles:
        dist = round(_l2(event_vec, p["centroid_4d"]), 6)
        ranked.append(
            {
                "era_id": p["era_id"],
                "label_ko": p["label_ko"],
                "distance_l2": dist,
                "score": round(max(0.0, 1.0 - dist * 4.0), 6),
                "interpretation_class": "[HYPO]",
            }
        )
    ranked.sort(key=lambda r: (float(r["distance_l2"]), str(r["era_id"])))
    return ranked


def _event_text_for_mode(
    ev: dict[str, Any],
    *,
    tag_mode: str,
    anchors: dict[str, str],
) -> tuple[str, list[str], str]:
    headline = str(ev.get("headline_ko") or ev.get("canonical_text") or "")
    tier = str(ev.get("tier") or "")
    if tag_mode == "gold_tags":
        tags = [str(t) for t in (ev.get("inferred_regime_tags") or []) if str(t).strip()]
        source = "gold_inferred_regime_tags"
    else:
        tags = infer_tags_from_text_v2(headline, event_tier=tier or None)
        source = "text_blind_v2_inferred_tags"
    hebrew_parts = [anchors[t] for t in tags if t in anchors]
    if hebrew_parts:
        text = " ".join(hebrew_parts)
        return text, tags, source
    return headline, tags, "headline_ko_only_no_hebrew"


def _evaluate(
    *,
    gold: dict[str, Any],
    profiles: list[dict[str, Any]],
    anchors: dict[str, str],
    tag_mode: str,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    n = hit1 = hit1_relaxed = hit3 = locked_n = locked_hit = 0
    for ev in gold.get("events") or []:
        if not isinstance(ev, dict):
            continue
        src = str(ev.get("source_id") or "")
        if src in SYNTHETIC_SOURCES:
            continue
        text, tags, text_source = _event_text_for_mode(ev, tag_mode=tag_mode, anchors=anchors)
        bundle = _gematria_bundle(text)
        ranking = _rank_eras_by_gematria_distance(bundle["vector_4d"], profiles)
        pred_ids = [str(r["era_id"]) for r in ranking]
        gold_id = str(ev.get("gold_era_id") or "")
        acceptable = [str(x) for x in (ev.get("acceptable_era_ids") or [])]
        pool = {gold_id, *acceptable}
        row_hit1 = bool(pred_ids) and pred_ids[0] == gold_id
        row_hit1_relaxed = bool(pred_ids) and pred_ids[0] in pool
        row_hit3 = any(pid in pool for pid in pred_ids[:3])
        n += 1
        hit1 += int(row_hit1)
        hit1_relaxed += int(row_hit1_relaxed)
        hit3 += int(row_hit3)
        partition = str(ev.get("partition") or "")
        if partition == "locked_eval":
            locked_n += 1
            locked_hit += int(row_hit1)
        top = ranking[0] if ranking else {}
        insight_ko = (
            f"[HYPO] 게마트리아 4D 거리 {top.get('distance_l2')} → "
            f"{top.get('label_ko')} ({top.get('era_id')}). "
            f"NON_GATING · 예언·실매매 단정 없음."
        )
        rows.append(
            {
                "event_id": ev.get("event_id"),
                "tier": ev.get("tier"),
                "partition": ev.get("partition"),
                "tag_mode": tag_mode,
                "text_source": text_source,
                "inferred_tags": tags,
                "event_gematria": bundle,
                "gold_era_id": gold_id,
                "acceptable_era_ids": acceptable,
                "predicted_top1_era_id": pred_ids[0] if pred_ids else None,
                "predicted_top3_era_ids": pred_ids[:3],
                "distance_top1": top.get("distance_l2"),
                "hit_at_1_strict": row_hit1,
                "hit_at_1_relaxed": row_hit1_relaxed,
                "hit_at_3": row_hit3,
                "insight_ko": insight_ko,
            }
        )
    summary = {
        "n_events": n,
        "hit_at_1_strict": round(hit1 / n, 6) if n else None,
        "hit_at_1_relaxed": round(hit1_relaxed / n, 6) if n else None,
        "hit_at_3": round(hit3 / n, 6) if n else None,
        "locked_eval_hit_at_1_strict": round(locked_hit / locked_n, 6) if locked_n else None,
        "tag_mode": tag_mode,
    }
    return {"summary": summary, "rows": rows}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gold-json", type=Path, default=DEFAULT_GOLD)
    ap.add_argument("--chronology-json", type=Path, default=DEFAULT_CHRONOLOGY)
    ap.add_argument("--corpus-jsonl", type=Path, default=DEFAULT_CORPUS)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT_ART)
    ap.add_argument("--insights-json", type=Path, default=DEFAULT_OUT_INSIGHTS)
    args = ap.parse_args()

    gold_path = args.gold_json if args.gold_json.is_absolute() else ROOT / args.gold_json
    chrono_path = args.chronology_json if args.chronology_json.is_absolute() else ROOT / args.chronology_json
    corpus = args.corpus_jsonl if args.corpus_jsonl.is_absolute() else ROOT / args.corpus_jsonl
    out = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    insights_out = args.insights_json if args.insights_json.is_absolute() else ROOT / args.insights_json

    for p in (gold_path, chrono_path):
        if not p.is_file():
            print(f"MISSING: {p}", file=sys.stderr)
            return 2

    gold = load_json(gold_path)
    chrono = load_json(chrono_path)
    verse_index = _load_verse_index(corpus)
    profiles = _build_era_profiles(chrono, verse_index)
    anchors = _build_tag_hebrew_anchors(chrono, verse_index)

    text_blind = _evaluate(gold=gold, profiles=profiles, anchors=anchors, tag_mode="text_blind")
    gold_tags = _evaluate(gold=gold, profiles=profiles, anchors=anchors, tag_mode="gold_tags")

    payload: dict[str, Any] = {
        "schema": "logos_chronology_era_gematria_blind_eval_v1",
        "generated_at_utc": _now(),
        "hypothesis_tier": "[HYPO]",
        "research_only": True,
        "policy": POLICY,
        "method_ko": (
            "역사 headline → (태그 추론 또는 gold tags) → Hebrew anchor pool → "
            "gematria_engine + gematria_to_4d_bridge → era verse-ref centroid L2 rank"
        ),
        "inputs": {
            "gold_json": _rel(gold_path),
            "chronology_json": _rel(chrono_path),
            "corpus_jsonl": _rel(corpus),
            "n_verse_index": len(verse_index),
            "n_tag_hebrew_anchors": len(anchors),
        },
        "era_profiles": profiles,
        "tag_hebrew_anchors_preview": {k: v[:80] for k, v in list(anchors.items())[:8]},
        "evaluations": {
            "text_blind_gematria": text_blind,
            "gold_tags_gematria": gold_tags,
        },
        "known_limitations": [
            "Korean headlines alone yield combined_sum=0; anchors required for non-flat 4D.",
            "gematria_engine counts Hebrew/Greek letters only (additive, not full gematria tradition).",
            "4D bridge uses deterministic mod-101 spread + state16 probe — research PoC only.",
            "Does not replace logos_chronology_era_blind keyword eval or imply Track A promotion.",
        ],
        "compare_to_keyword_blind_ms_public": {
            "keyword_text_blind_locked_eval_hit_at_1_strict": 0.090909,
            "note": "From rq032 / logos_chronology_era_blind_eval_text_blind_tier_v2 — different axis.",
        },
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    insight_doc = {
        "schema": "logos_chronology_era_gematria_insights_v1",
        "generated_at_utc": payload["generated_at_utc"],
        "hypothesis_tier": "[HYPO]",
        "source_eval": _rel(out),
        "text_blind_summary": text_blind["summary"],
        "gold_tags_summary": gold_tags["summary"],
        "sample_insights": [r for r in text_blind["rows"][:5]],
    }
    insights_out.parent.mkdir(parents=True, exist_ok=True)
    insights_out.write_text(json.dumps(insight_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    tb = text_blind["summary"]
    gt = gold_tags["summary"]
    print(
        json.dumps(
            {
                "ok": True,
                "output": _rel(out),
                "insights": _rel(insights_out),
                "text_blind_hit_at_1_strict": tb.get("hit_at_1_strict"),
                "text_blind_locked_eval_hit_at_1_strict": tb.get("locked_eval_hit_at_1_strict"),
                "gold_tags_hit_at_1_strict": gt.get("hit_at_1_strict"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
