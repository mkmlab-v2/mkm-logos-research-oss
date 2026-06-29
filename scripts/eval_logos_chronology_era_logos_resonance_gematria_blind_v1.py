#!/usr/bin/env python3
"""[HYPO] LogosEncoder resonance -> Hebrew gematria 4D -> era blind eval (NON_GATING).

Pipeline: history headline -> LogosEncoder cosine over canon corpus -> top-k verses ->
concat Hebrew/Greek -> gematria_engine + 4D bridge -> rank vs era verse-ref centroids.

LogosEncoder here is deterministic sha256->4D (tools/core/logos_encoder_gpu.py), same as
logos_vector_resonance_probe — research PoC, not neural embedding.
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

from logos_chronology_gematria_core_v1 import (  # noqa: E402
    build_era_profiles,
    build_verse_to_eras,
    filter_gold_events,
    gematria_bundle,
    load_json,
    load_verse_index,
    rank_eras_by_gematria_distance,
    rel_repo,
    summarize_hits,
    utc_now,
)
from logos_chronology_map_core_v1 import POLICY  # noqa: E402
from tools.core.logos_corpus_loader import default_hebrew_greek_jsonl, iter_hebrew_greek_jsonl  # noqa: E402
from tools.core.logos_encoder_gpu import LogosEncoder  # noqa: E402

DEFAULT_GOLD = ROOT / "docs/final/artifacts/fixtures/logos_chronology_historical_era_gold_v1.json"
DEFAULT_CHRONOLOGY = ROOT / "docs/final/artifacts/logos_chronology_v1_latest.json"
DEFAULT_CORPUS = default_hebrew_greek_jsonl(ROOT)
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_chronology_era_logos_resonance_gematria_blind_eval_v1_latest.json"
DEFAULT_INSIGHTS = ROOT / "reports/logos_chronology_era_logos_resonance_gematria_insights_v1_latest.json"


def _l2n(x: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(x, axis=-1, keepdims=True)
    return x / (n + 1e-8)


def _build_corpus_embeddings(
    encoder: LogosEncoder,
    corpus: Path,
    verse_index: dict[str, dict[str, str]],
    *,
    device: str,
    chunk_size: int,
    limit: int | None,
) -> tuple[list[str], np.ndarray]:
    ids: list[str] = []
    texts: list[str] = []
    for rec in iter_hebrew_greek_jsonl(corpus, limit=limit):
        vid = str(rec.get("verse_id") or "").strip()
        if not vid or vid not in verse_index:
            continue
        txt = str(verse_index[vid].get("encode_text") or "").strip()
        if not txt:
            continue
        ids.append(vid)
        texts.append(txt)
    if not texts:
        return [], np.zeros((0, 4), dtype=np.float32)
    rows: list[np.ndarray] = []
    for i in range(0, len(texts), chunk_size):
        batch = texts[i : i + chunk_size]
        emb = encoder.encode_texts_batch_to_logos_embeddings(batch, device=device)
        rows.append(_l2n(emb.detach().float().cpu().numpy()))
    mat = np.vstack(rows) if rows else np.zeros((0, 4), dtype=np.float32)
    return ids, mat


def _top_k_resonance(
    encoder: LogosEncoder,
    query: str,
    verse_ids: list[str],
    embeddings: np.ndarray,
    *,
    device: str,
    top_k: int,
) -> list[dict[str, Any]]:
    if not query.strip() or embeddings.shape[0] == 0:
        return []
    q = encoder.encode_texts_batch_to_logos_embeddings([query], device=device)
    qv = _l2n(q.detach().float().cpu().numpy())[0]
    sims = embeddings @ qv
    kk = min(max(1, top_k), sims.shape[0])
    idx = np.argpartition(-sims, kk - 1)[:kk]
    idx = idx[np.argsort(-sims[idx])]
    hits: list[dict[str, Any]] = []
    for i in idx:
        hits.append({"verse_id": verse_ids[int(i)], "cosine_sim": round(float(sims[int(i)]), 6)})
    return hits


def _era_votes_from_hits(hits: list[dict[str, Any]], verse_to_eras: dict[str, list[str]]) -> dict[str, int]:
    votes: dict[str, int] = {}
    for h in hits:
        for eid in verse_to_eras.get(str(h.get("verse_id") or ""), []):
            votes[eid] = votes.get(eid, 0) + 1
    return votes


def _evaluate_resonance_gematria(
    *,
    events: list[dict[str, Any]],
    profiles: list[dict[str, Any]],
    verse_index: dict[str, dict[str, str]],
    verse_to_eras: dict[str, list[str]],
    encoder: LogosEncoder,
    verse_ids: list[str],
    embeddings: np.ndarray,
    device: str,
    top_k: int,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for ev in events:
        headline = str(ev.get("headline_ko") or ev.get("canonical_text") or "")
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
        ranking = rank_eras_by_gematria_distance(bundle["vector_4d"], profiles)
        era_votes = _era_votes_from_hits(hits, verse_to_eras)
        for h in hits:
            h["era_ids_from_chronology_refs"] = verse_to_eras.get(str(h.get("verse_id") or ""), [])
        pred_ids = [str(r["era_id"]) for r in ranking]
        gold_id = str(ev.get("gold_era_id") or "")
        acceptable = [str(x) for x in (ev.get("acceptable_era_ids") or [])]
        pool_ids = {gold_id, *acceptable}
        top = ranking[0] if ranking else {}
        vote_top = sorted(era_votes.items(), key=lambda x: (-x[1], x[0]))[:3]
        insight_ko = (
            f"[HYPO] Logos공명 top-{len(hits)} 구절 → 게마트리아 4D → "
            f"{top.get('label_ko')} ({top.get('era_id')}). "
            f"공명 1위={hits[0]['verse_id'] if hits else 'none'}. "
            f"NON_GATING · 통찰·예언 단정 없음."
        )
        rows.append(
            {
                "event_id": ev.get("event_id"),
                "tier": ev.get("tier"),
                "partition": ev.get("partition"),
                "query_headline_ko": headline[:160],
                "resonance_hits": hits,
                "era_vote_top3": [{"era_id": e, "votes": v} for e, v in vote_top],
                "event_gematria": bundle,
                "gold_era_id": gold_id,
                "acceptable_era_ids": acceptable,
                "predicted_top1_era_id": pred_ids[0] if pred_ids else None,
                "predicted_top3_era_ids": pred_ids[:3],
                "distance_top1": top.get("distance_l2"),
                "hit_at_1_strict": bool(pred_ids) and pred_ids[0] == gold_id,
                "hit_at_1_relaxed": bool(pred_ids) and pred_ids[0] in pool_ids,
                "hit_at_3": any(pid in pool_ids for pid in pred_ids[:3]),
                "insight_ko": insight_ko,
            }
        )
    summary = summarize_hits(rows)
    summary["mode"] = "logos_resonance_gematria"
    summary["top_k"] = top_k
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
    ap.add_argument("--corpus-limit", type=int, default=None, help="Dev-only verse cap")
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
    evaluation = _evaluate_resonance_gematria(
        events=events,
        profiles=profiles,
        verse_index=verse_index,
        verse_to_eras=verse_to_eras,
        encoder=encoder,
        verse_ids=verse_ids,
        embeddings=embeddings,
        device=device,
        top_k=max(1, int(args.top_k)),
    )

    payload: dict[str, Any] = {
        "schema": "logos_chronology_era_logos_resonance_gematria_blind_eval_v1",
        "generated_at_utc": utc_now(),
        "hypothesis_tier": "[HYPO]",
        "research_only": True,
        "policy": POLICY,
        "method_ko": (
            "역사 headline → LogosEncoder(sha256 4D) 코퍼스 cosine top-k → "
            "히브리/그리스 pool → gematria 4D bridge → era centroid L2 rank + era vote from verse_refs"
        ),
        "inputs": {
            "gold_json": rel_repo(ROOT, gold_path),
            "chronology_json": rel_repo(ROOT, chrono_path),
            "corpus_jsonl": rel_repo(ROOT, corpus),
            "n_corpus_verses_encoded": int(embeddings.shape[0]),
            "top_k": int(args.top_k),
            "device": device,
            "logos_encoder_note": "sha256 deterministic projection — not neural GPU model",
        },
        "era_profiles": profiles,
        "evaluation": evaluation,
        "known_limitations": [
            "LogosEncoder is hash projection; KO->scripture resonance is lexical/hash, not semantic LLM.",
            "Gematria 4D bridge is mod-101 PoC; not traditional gematria exegesis.",
            "Does not mutate Track A, ops score, or live trading.",
        ],
        "compare_axes": {
            "keyword_text_blind_locked_eval_hit_at_1_strict": 0.090909,
            "tag_anchor_gematria_hit_at_1_strict": 0.021277,
            "note": "Prior runs on same 47-event gold fixture.",
        },
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    insight_doc = {
        "schema": "logos_chronology_era_logos_resonance_gematria_insights_v1",
        "generated_at_utc": payload["generated_at_utc"],
        "hypothesis_tier": "[HYPO]",
        "source_eval": rel_repo(ROOT, out),
        "summary": evaluation["summary"],
        "sample_insights": evaluation["rows"][:8],
    }
    insights_out.parent.mkdir(parents=True, exist_ok=True)
    insights_out.write_text(json.dumps(insight_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    sm = evaluation["summary"]
    print(
        json.dumps(
            {
                "ok": True,
                "output": rel_repo(ROOT, out),
                "insights": rel_repo(ROOT, insights_out),
                "n_corpus_verses": int(embeddings.shape[0]),
                "hit_at_1_strict": sm.get("hit_at_1_strict"),
                "locked_eval_hit_at_1_strict": sm.get("locked_eval_hit_at_1_strict"),
                "hit_at_3": sm.get("hit_at_3"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
