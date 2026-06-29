"""Shared gematria + chronology era ranking helpers ([HYPO], NON_GATING)."""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from logos_chronology_map_core_v1 import infer_tags_from_text_v2, load_json
from scripts.core.gematria_engine import build_gematria_metadata
from scripts.core.gematria_to_4d_bridge import build_gematria_4d_bridge
from tools.core.logos_corpus_loader import verse_logos_text

SYNTHETIC_SOURCES = frozenset({"label_guided_seed", "manual_seed"})


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def rel_repo(root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve())).replace("\\", "/")
    except ValueError:
        return str(path.resolve())


def load_verse_index(corpus: Path) -> dict[str, dict[str, str]]:
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
        encode_text = verse_logos_text(rec) or logos
        payload = {
            "logos_text": logos,
            "encode_text": encode_text,
            "text_hebrew": he,
            "text_greek": gr,
        }
        index[vid] = payload
        if vid.startswith("aramaic::"):
            index[vid.split("::", 1)[1]] = payload
    return index


def resolve_ref(ref: str, verse_index: dict[str, dict[str, str]]) -> str:
    ref = str(ref or "").strip()
    if not ref:
        return ""
    entry = verse_index.get(ref)
    if entry is None and "::" in ref:
        entry = verse_index.get(ref.split("::", 1)[1])
    if not entry:
        return ""
    return str(entry.get("logos_text") or "")


def vec4_from_text(text: str) -> dict[str, float]:
    meta = build_gematria_metadata(raw_text=text, compressed_text=text, reconstructed_text=text)
    bridge = build_gematria_4d_bridge(gematria_metadata=meta)
    vec = bridge.get("vector_4d") or {}
    return {
        "S": float(vec.get("S", 0.25)),
        "L": float(vec.get("L", 0.25)),
        "K": float(vec.get("K", 0.25)),
        "M": float(vec.get("M", 0.25)),
    }


def l2_distance(a: dict[str, float], b: dict[str, float]) -> float:
    return math.sqrt(sum((float(a[k]) - float(b[k])) ** 2 for k in ("S", "L", "K", "M")))


def mean_vec(vectors: list[dict[str, float]]) -> dict[str, float]:
    if not vectors:
        return {"S": 0.25, "L": 0.25, "K": 0.25, "M": 0.25}
    out = {"S": 0.0, "L": 0.0, "K": 0.0, "M": 0.0}
    for v in vectors:
        for k in out:
            out[k] += float(v[k])
    n = float(len(vectors))
    return {k: round(out[k] / n, 6) for k in out}


def gematria_bundle(text: str) -> dict[str, Any]:
    meta = build_gematria_metadata(
        raw_text=text,
        compressed_text=text,
        reconstructed_text=text,
    )
    bridge = build_gematria_4d_bridge(gematria_metadata=meta)
    return {
        "text_preview": text[:120],
        "gematria": meta,
        "vector_4d": vec4_from_text(text),
        "state16": bridge.get("state16"),
        "hebrew_chars": int(meta.get("raw_hebrew_chars") or 0),
        "greek_chars": int(meta.get("raw_greek_chars") or 0),
        "combined_sum": int(meta.get("raw_combined_sum") or 0),
    }


def build_era_profiles(chrono: dict[str, Any], verse_index: dict[str, dict[str, str]]) -> list[dict[str, Any]]:
    profiles: list[dict[str, Any]] = []
    for era in chrono.get("eras") or []:
        if not isinstance(era, dict):
            continue
        eid = str(era.get("era_id") or "")
        verse_texts: list[str] = []
        for ref in era.get("verse_refs") or []:
            t = resolve_ref(str(ref), verse_index)
            if t:
                verse_texts.append(t)
        verse_vecs = [gematria_bundle(t)["vector_4d"] for t in verse_texts]
        concat = " ".join(verse_texts)
        bundle = gematria_bundle(concat) if concat else gematria_bundle(str(era.get("label_ko") or eid))
        profiles.append(
            {
                "era_id": eid,
                "label_ko": str(era.get("label_ko") or eid),
                "n_verse_refs": len(era.get("verse_refs") or []),
                "n_verse_texts_resolved": len(verse_texts),
                "obs_tags": [str(t) for t in (era.get("regime_tags_observational") or [])],
                "centroid_4d": mean_vec(verse_vecs) if verse_vecs else bundle["vector_4d"],
                "era_gematria": bundle,
            }
        )
    return profiles


def build_verse_to_eras(chrono: dict[str, Any]) -> dict[str, list[str]]:
    mapping: dict[str, list[str]] = {}
    for era in chrono.get("eras") or []:
        if not isinstance(era, dict):
            continue
        eid = str(era.get("era_id") or "")
        for ref in era.get("verse_refs") or []:
            key = str(ref).strip()
            if not key:
                continue
            mapping.setdefault(key, [])
            if eid not in mapping[key]:
                mapping[key].append(eid)
            if "::" in key:
                short = key.split("::", 1)[1]
                mapping.setdefault(short, [])
                if eid not in mapping[short]:
                    mapping[short].append(eid)
    return mapping


def build_tag_hebrew_anchors(chrono: dict[str, Any], verse_index: dict[str, dict[str, str]]) -> dict[str, str]:
    anchors: dict[str, str] = {}
    for era in chrono.get("eras") or []:
        if not isinstance(era, dict):
            continue
        obs = [str(t) for t in (era.get("regime_tags_observational") or [])]
        if not obs:
            continue
        snippet = ""
        for ref in era.get("verse_refs") or []:
            t = resolve_ref(str(ref), verse_index)
            if t:
                snippet = t
                break
        if not snippet:
            continue
        for tag in obs:
            anchors.setdefault(tag, snippet)
    return anchors


def rank_eras_by_gematria_distance(
    event_vec: dict[str, float],
    profiles: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    ranked: list[dict[str, Any]] = []
    for p in profiles:
        dist = round(l2_distance(event_vec, p["centroid_4d"]), 6)
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


def event_text_for_mode(
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
        return " ".join(hebrew_parts), tags, source
    return headline, tags, "headline_ko_only_no_hebrew"


def summarize_hits(rows: list[dict[str, Any]]) -> dict[str, Any]:
    n = hit1 = hit1_relaxed = hit3 = locked_n = locked_hit = 0
    for row in rows:
        n += 1
        hit1 += int(bool(row.get("hit_at_1_strict")))
        hit1_relaxed += int(bool(row.get("hit_at_1_relaxed")))
        hit3 += int(bool(row.get("hit_at_3")))
        if str(row.get("partition") or "") == "locked_eval":
            locked_n += 1
            locked_hit += int(bool(row.get("hit_at_1_strict")))
    return {
        "n_events": n,
        "hit_at_1_strict": round(hit1 / n, 6) if n else None,
        "hit_at_1_relaxed": round(hit1_relaxed / n, 6) if n else None,
        "hit_at_3": round(hit3 / n, 6) if n else None,
        "locked_eval_hit_at_1_strict": round(locked_hit / locked_n, 6) if locked_n else None,
    }


def filter_gold_events(gold: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for ev in gold.get("events") or []:
        if not isinstance(ev, dict):
            continue
        if str(ev.get("source_id") or "") in SYNTHETIC_SOURCES:
            continue
        out.append(ev)
    return out


def build_tag_to_eras(chrono: dict[str, Any]) -> dict[str, list[str]]:
    mapping: dict[str, list[str]] = {}
    for era in chrono.get("eras") or []:
        if not isinstance(era, dict):
            continue
        eid = str(era.get("era_id") or "")
        for tag in era.get("regime_tags_observational") or []:
            key = str(tag).strip()
            if not key:
                continue
            mapping.setdefault(key, [])
            if eid not in mapping[key]:
                mapping[key].append(eid)
    return mapping


def sim_weighted_era_scores(
    hits: list[dict[str, Any]],
    verse_to_eras: dict[str, list[str]],
) -> dict[str, float]:
    scores: dict[str, float] = {}
    for h in hits:
        sim = float(h.get("cosine_sim") or 0.0)
        if sim <= 0.0:
            continue
        for eid in verse_to_eras.get(str(h.get("verse_id") or ""), []):
            scores[eid] = scores.get(eid, 0.0) + sim
    return scores


def scores_from_gematria_ranking(ranking: list[dict[str, Any]]) -> dict[str, float]:
    return {str(r["era_id"]): float(r.get("score") or 0.0) for r in ranking}


def scores_from_keyword_ranking(ranking: list[dict[str, Any]]) -> dict[str, float]:
    return {str(r["era_id"]): float(r.get("score") or 0.0) for r in ranking}


def normalize_score_map(scores: dict[str, float]) -> dict[str, float]:
    if not scores:
        return {}
    vals = list(scores.values())
    lo = min(vals)
    hi = max(vals)
    if hi - lo < 1e-9:
        return {k: 1.0 if v > 0 else 0.0 for k, v in scores.items()}
    return {k: round((v - lo) / (hi - lo), 6) for k, v in scores.items()}


def fuse_weighted_score_maps(
    profiles: list[dict[str, Any]],
    *weighted_maps: tuple[dict[str, float], float],
) -> dict[str, float]:
    era_ids = [str(p["era_id"]) for p in profiles]
    fused: dict[str, float] = {eid: 0.0 for eid in era_ids}
    for raw, weight in weighted_maps:
        if weight <= 0.0 or not raw:
            continue
        norm = normalize_score_map({eid: raw.get(eid, 0.0) for eid in era_ids})
        for eid in era_ids:
            fused[eid] += weight * norm.get(eid, 0.0)
    return fused


def rank_eras_by_score_map(
    scores: dict[str, float],
    profiles: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    label_by_id = {str(p["era_id"]): str(p.get("label_ko") or p["era_id"]) for p in profiles}
    ranked = [
        {
            "era_id": eid,
            "label_ko": label_by_id.get(eid, eid),
            "score": round(float(scores.get(eid, 0.0)), 6),
            "interpretation_class": "[HYPO]",
        }
        for eid in scores
    ]
    ranked.sort(key=lambda r: (-float(r["score"]), str(r["era_id"])))
    return ranked


def reciprocal_rank_fusion(
    ranked_era_ids: list[list[str]],
    *,
    k: float = 60.0,
) -> list[str]:
    scores: dict[str, float] = {}
    for ranking in ranked_era_ids:
        for rank, eid in enumerate(ranking, start=1):
            scores[eid] = scores.get(eid, 0.0) + 1.0 / (k + float(rank))
    return [eid for eid, _ in sorted(scores.items(), key=lambda x: (-x[1], x[0]))]


def row_hit_fields(
    pred_ids: list[str],
    gold_id: str,
    acceptable: list[str],
) -> dict[str, bool]:
    pool = {gold_id, *acceptable}
    return {
        "predicted_top1_era_id": pred_ids[0] if pred_ids else None,
        "predicted_top3_era_ids": pred_ids[:3],
        "hit_at_1_strict": bool(pred_ids) and pred_ids[0] == gold_id,
        "hit_at_1_relaxed": bool(pred_ids) and pred_ids[0] in pool,
        "hit_at_3": any(pid in pool for pid in pred_ids[:3]),
    }
