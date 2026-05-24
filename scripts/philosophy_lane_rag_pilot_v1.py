#!/usr/bin/env python3
"""Philosophy / counsel lane RAG pilot (Track B only, Fact-Lock).

- Forbidden-domain gate (no network, no orders).
- Optional ANN-lite Top-K via query_logos_vector_index_ann_lite_v1.py (local sqlite).
- Optional cross_lens_rag_fusion refresh (subprocess; may no-op if inputs missing).
- Writes disk SSOT JSON for mkmlife-style \"one question\" pipelines; does NOT promote to A-track.

Exit codes:
  0 wrote pilot JSON (including fallback_rejection)
  1 unexpected failure
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.logos_rag_hybrid_query_v1 import (  # noqa: E402
    HybridStyle,
    build_hybrid_text_query,
    encode_hybrid_query,
)
from scripts.logos_rag_bilingual_query_v1 import (  # noqa: E402
    DEFAULT_V3_BILINGUAL,
    effective_retrieval_query_ko_only,
    en_to_ko_map,
    load_bilingual_items,
)
from scripts.logos_rag_query_route_v1 import (  # noqa: E402
    build_retrieval_query,
    detect_query_route,
    hangul_ratio,
)
from scripts.run_logos_rag_retrieval_round_v1 import (  # noqa: E402
    _encode_query,
    _load_index,
    _load_medoid_weights,
    _retrieve_improved,
    _score_all,
    preprocess_query,
)
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "philosophy_lane_rag_pilot_v1_latest.json"
DEFAULT_SQLITE = ROOT / "docs" / "final" / "artifacts" / "logos_vector_index_ann_lite_v1.sqlite"
DEFAULT_SQLITE_BTRACK_ST = (
    ROOT / "reports" / "constitution" / "btrack_pilot" / "logos_vector_index_ann_lite_st_u_v1.sqlite"
)
DEFAULT_ST_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
QUERY_SCRIPT = ROOT / "scripts" / "query_logos_vector_index_ann_lite_v1.py"
FUSION_SCRIPT = ROOT / "scripts" / "build_cross_lens_rag_fusion_v1.py"
DEFAULT_FORBIDDEN_CONFIG = (
    ROOT / "docs" / "final" / "artifacts" / "schemas" / "philosophy_lane_rag_pilot_forbidden_substrings_v1.json"
)

SCHEMA = "philosophy_lane_rag_pilot_v1"
VERSION = "1.2.0"

# Fallback if JSON missing or invalid (keep in sync with default JSON when possible).
_FORBIDDEN_SUBSTRINGS_FALLBACK = (
    "btcusdt",
    "binance",
    "주식",
    "투자",
    "매매",
    "비트코인",
    "선물",
    "옵션",
    "날씨",
    "기상",
    "진단",
    "처방",
    "약물",
    "암 ",
    "암이",
    "수술",
    "정치",
    "선거",
    "투표",
    "stock",
    "invest",
    "etf",
    "forex",
    "weather forecast",
    "diagnos",
    "prescription",
    "election",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_forbidden_substrings(config_path: Path) -> tuple[tuple[str, ...], str | None]:
    """Return (substrings, config_error_or_none)."""
    if not config_path.is_file():
        return _FORBIDDEN_SUBSTRINGS_FALLBACK, f"missing_forbidden_config:{config_path}"
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        return _FORBIDDEN_SUBSTRINGS_FALLBACK, f"forbidden_config_read_error:{e}"
    subs = raw.get("substrings") if isinstance(raw, dict) else None
    if not isinstance(subs, list):
        return _FORBIDDEN_SUBSTRINGS_FALLBACK, "forbidden_config_invalid_substrings"
    out: list[str] = []
    for x in subs:
        if isinstance(x, str) and (s := x.strip()):
            out.append(s)
    if not out:
        return _FORBIDDEN_SUBSTRINGS_FALLBACK, "forbidden_config_empty_substrings"
    return tuple(out), None


def _forbidden_hit(text: str, substrings: tuple[str, ...]) -> str | None:
    hay = text.lower()
    for s in substrings:
        if s.lower() in hay:
            return s
    return None


def _sqlite_embedding_mode(sqlite: Path) -> str | None:
    import sqlite3

    con = sqlite3.connect(str(sqlite))
    try:
        row = con.execute("SELECT embedding_mode FROM logos_vec_stub LIMIT 1").fetchone()
        return str(row[0]) if row and row[0] else None
    finally:
        con.close()


def _run_ann_lite_structured_hybrid(
    query_en: str,
    query_ko: str,
    top_k: int,
    sqlite: Path,
    *,
    hybrid_style: HybridStyle,
    sentence_transformer_model: str,
) -> tuple[dict[str, Any] | None, str | None]:
    """In-process Top-K for bilingual EN+KO (dual_embed_mean or concat styles)."""
    from scripts.logos_ann_lite_embedding_v1 import load_sentence_transformer
    from scripts.run_logos_rag_retrieval_round_v1 import _encode_query, _load_index, _score_all

    if not sqlite.is_file():
        return None, f"missing_sqlite:{sqlite}"
    mode = _sqlite_embedding_mode(sqlite)
    if mode != "sentence_transformers_v1":
        return None, f"structured_hybrid_requires_st_index got={mode}"
    try:
        model = load_sentence_transformer(sentence_transformer_model)
        index_rows, dim, mode = _load_index(sqlite)
        if hybrid_style == "dual_embed_mean":
            qvec = encode_hybrid_query(model, query_en, query_ko, style=hybrid_style)
            seed = f"hybrid_dual:{query_ko[:48]}|{query_en[:48]}"
        else:
            text, applied = build_hybrid_text_query(query_en, query_ko, style=hybrid_style)
            qvec = _encode_query(model, text)
            seed = f"{applied}:{text[:96]}"
        scored = _score_all(qvec, index_rows, dim)
        top = scored[:top_k]
        ts = _utc_now()
        doc: dict[str, Any] = {
            "schema": "logos_vector_ann_lite_query_result_v1",
            "version": "1.1.0",
            "ts_utc": ts,
            "hypothesis_tier": "B",
            "non_gating_ack": True,
            "embedding_mode": mode,
            "sqlite_path": str(sqlite.resolve()),
            "query_seed": seed,
            "dim": dim,
            "top_k": [
                {"verse_id": vid, "score": round(sc, 9), "rank": i + 1}
                for i, (vid, sc) in enumerate(top)
            ],
            "notes": f"structured bilingual via logos_rag_hybrid_query_v1 ({hybrid_style}).",
        }
        return doc, None
    except Exception as e:
        return None, str(e)[:400]


def _run_ann_lite_structured_ko_only(
    query_ko: str,
    top_k: int,
    sqlite: Path,
    *,
    sentence_transformer_model: str,
    medoids_json: Path | None = None,
) -> tuple[dict[str, Any] | None, str | None]:
    """P15 R6: KO-only lane — preprocess_query + improved retrieval (no EN/hybrid blend)."""
    from scripts.logos_ann_lite_embedding_v1 import load_sentence_transformer

    if not sqlite.is_file():
        return None, f"missing_sqlite:{sqlite}"
    mode = _sqlite_embedding_mode(sqlite)
    if mode != "sentence_transformers_v1":
        return None, f"ko_only_requires_st_index got={mode}"
    medoid_path = medoids_json or (ROOT / "docs/final/artifacts/logos_verse_4d_medoids_v1_latest.json")
    try:
        model = load_sentence_transformer(sentence_transformer_model)
        index_rows, dim, mode = _load_index(sqlite)
        medoid_weights = _load_medoid_weights(medoid_path) if medoid_path.is_file() else {}
        q_eff = preprocess_query(query_ko.strip())
        qvec = _encode_query(model, q_eff)
        scored = _score_all(qvec, index_rows, dim)
        hits, _meta = _retrieve_improved(
            scored,
            max_k=max(top_k, 24),
            floor_abs=0.12,
            floor_ratio=0.5,
            medoid_weights=medoid_weights,
            medoid_boost_cap=0.0,
        )
        top = hits[:top_k]
        doc: dict[str, Any] = {
            "schema": "logos_vector_ann_lite_query_result_v1",
            "version": "1.2.0",
            "ts_utc": _utc_now(),
            "hypothesis_tier": "B",
            "non_gating_ack": True,
            "embedding_mode": mode,
            "sqlite_path": str(sqlite.resolve()),
            "query_seed": f"ko_only_improved:{q_eff[:96]}",
            "dim": dim,
            "top_k": [
                {"verse_id": vid, "score": round(sc, 9), "rank": i + 1}
                for i, row in enumerate(top)
                if isinstance(row, dict)
                for vid, sc in [(row.get("verse_id"), row.get("score"))]
                if isinstance(vid, str) and isinstance(sc, (int, float))
            ],
            "notes": "P15 R6 ko_only lane: query_ko + improved retrieval (sweep-aligned).",
        }
        return doc, None
    except Exception as e:
        return None, str(e)[:400]


def _run_ann_lite_query(
    query: str,
    top_k: int,
    sqlite: Path,
    *,
    sentence_transformer_model: str | None = None,
) -> tuple[dict[str, Any] | None, str | None]:
    """Return (query_result_doc, error_message)."""
    if not sqlite.is_file():
        return None, f"missing_sqlite:{sqlite}"
    if not QUERY_SCRIPT.is_file():
        return None, "missing_query_script"
    mode = _sqlite_embedding_mode(sqlite)
    st_model = sentence_transformer_model
    if mode == "sentence_transformers_v1" and not (st_model and st_model.strip()):
        st_model = DEFAULT_ST_MODEL
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as tmp:
        tmp_path = Path(tmp.name)
    try:
        cmd = [
            sys.executable,
            str(QUERY_SCRIPT),
            "--sqlite",
            str(sqlite),
            "--query",
            query,
            "--top-k",
            str(top_k),
            "--output-json",
            str(tmp_path),
        ]
        if st_model and mode == "sentence_transformers_v1":
            cmd.extend(["--sentence-transformer-model", st_model.strip()])
        proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=120)
        if proc.returncode != 0:
            err = (proc.stderr or proc.stdout or "").strip() or f"exit_{proc.returncode}"
            return None, err
        if not tmp_path.is_file():
            return None, "query_output_missing"
        doc = json.loads(tmp_path.read_text(encoding="utf-8"))
        return doc if isinstance(doc, dict) else None, None
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError) as e:
        return None, str(e)
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass


def _run_cross_lens_fusion() -> tuple[bool, str | None]:
    if not FUSION_SCRIPT.is_file():
        return False, "missing_fusion_script"
    proc = subprocess.run(
        [sys.executable, str(FUSION_SCRIPT), "--skip-history-append", "--skip-alert-emit"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=180,
    )
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "")[-800:]
        return False, tail.strip() or f"exit_{proc.returncode}"
    return True, None


def _blocks_from_ann(ann: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not ann:
        return []
    top = ann.get("top_k")
    if not isinstance(top, list):
        return []
    out: list[dict[str, Any]] = []
    for row in top[:10]:
        if not isinstance(row, dict):
            continue
        vid = row.get("verse_id")
        score = row.get("score")
        out.append(
            {
                "source_rail": "logos_ann_lite",
                "hypothesis_tag": "[HYPO]",
                "summary": f"logos_ann_lite hit verse_id={vid!r} score={score}",
                "detail": "Track B ANN-lite hit; see ann_lite_query notes for embedding_mode.",
                "evidence_path": None,
            }
        )
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--user-query", default="", help="User question text (pilot channel).")
    ap.add_argument("--query-en", default="", help="Structured EN leg (optional; use with --query-ko).")
    ap.add_argument("--query-ko", default="", help="Structured KO leg (optional; use with --query-en).")
    ap.add_argument(
        "--hybrid-style",
        choices=("dual_embed_mean", "en_ko_concat", "ko_en_concat", "ko_primary"),
        default="dual_embed_mean",
        help="When --query-en and --query-ko are set (P15 hybrid default).",
    )
    ap.add_argument(
        "--rag-lane",
        choices=("auto", "hybrid_dual", "ko_only"),
        default="ko_only",
        help="P15 R6 default: ko_only uses query_ko + improved ST retrieval (bilingual structured).",
    )
    ap.add_argument("--menu-id", default="mkm_philosophy_chat_v1")
    ap.add_argument("--top-k", type=int, default=3)
    ap.add_argument("--sqlite", type=Path, default=DEFAULT_SQLITE)
    ap.add_argument(
        "--use-btrack-st-index",
        action="store_true",
        help="Force btrack_pilot ST U index (semantic).",
    )
    ap.add_argument(
        "--no-prefer-btrack-st",
        action="store_true",
        help="Do not auto-select btrack ST sqlite when present (default: prefer ST).",
    )
    ap.add_argument(
        "--query-route",
        choices=("auto", "en", "ko", "hybrid", "mixed_raw", "ko_only"),
        default="ko_only",
        help="R6 default: ko_only uses v3 bilingual KO gloss for EN probes (P15).",
    )
    ap.add_argument(
        "--bilingual-map-json",
        type=Path,
        default=DEFAULT_V3_BILINGUAL,
        help="EN→KO gloss map for --query-route ko_only (v3_bilingual_v1).",
    )
    ap.add_argument(
        "--sentence-transformer-model",
        type=str,
        default=None,
        help="Required for ST index; default all-MiniLM-L6-v2 when --use-btrack-st-index.",
    )
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--forbidden-config",
        type=Path,
        default=DEFAULT_FORBIDDEN_CONFIG,
        help="JSON with schema philosophy_lane_rag_pilot_forbidden_substrings_v1 and substrings[].",
    )
    ap.add_argument(
        "--invoke-cross-lens-fusion",
        action="store_true",
        help="Run build_cross_lens_rag_fusion_v1.py after ANN step (Track B artifact refresh).",
    )
    ap.add_argument(
        "--redact-query",
        action="store_true",
        help="Do not embed raw user_query in output (store sha256 prefix only).",
    )
    args = ap.parse_args()

    sqlite_path = Path(args.sqlite)
    use_st = bool(args.use_btrack_st_index) or (
        not args.no_prefer_btrack_st and DEFAULT_SQLITE_BTRACK_ST.is_file()
    )
    if use_st:
        sqlite_path = DEFAULT_SQLITE_BTRACK_ST
    st_model = args.sentence_transformer_model
    if use_st and not (st_model and str(st_model).strip()):
        st_model = DEFAULT_ST_MODEL

    q_en = str(args.query_en or "").strip()
    q_ko = str(args.query_ko or "").strip()
    structured_bilingual = bool(q_en and q_ko)
    raw_q = str(args.user_query or "").strip()
    if not raw_q and structured_bilingual:
        raw_q = f"{q_en}. {q_ko}"
    if not raw_q:
        print("Provide --user-query or both --query-en and --query-ko.", file=sys.stderr)
        return 1

    hybrid_style: HybridStyle = args.hybrid_style  # type: ignore[assignment]
    rag_lane = str(args.rag_lane or "ko_only").strip().lower()
    route_policy = str(args.query_route).strip().lower()
    en_ko: dict[str, str] = {}
    if args.bilingual_map_json.is_file():
        try:
            en_ko = en_to_ko_map(load_bilingual_items(args.bilingual_map_json))
        except (ValueError, OSError, json.JSONDecodeError):
            en_ko = {}

    use_ko_lane = (structured_bilingual and rag_lane == "ko_only") or route_policy == "ko_only"
    if use_ko_lane:
        route = "ko_only"
        retrieval_q, route_applied = effective_retrieval_query_ko_only(
            raw_q=raw_q,
            query_en=q_en,
            query_ko=q_ko,
            en_ko=en_ko or None,
        )
    elif structured_bilingual and rag_lane == "hybrid_dual":
        route = "hybrid"
        retrieval_q, route_applied = build_hybrid_text_query(q_en, q_ko, style=hybrid_style)
        route_applied = f"structured_{route_applied}"
    else:
        route = detect_query_route(raw_q, policy=route_policy)
        retrieval_q, route_applied = build_retrieval_query(raw_q, route)

    forbidden_path = Path(args.forbidden_config)
    forbidden_subs, forbidden_cfg_err = _load_forbidden_substrings(forbidden_path)
    hit = _forbidden_hit(raw_q, forbidden_subs)
    ann_doc: dict[str, Any] | None = None
    ann_err: str | None = None
    fusion_ok = False
    fusion_err: str | None = None

    status = "ok"
    reasons: list[str] = []
    if forbidden_cfg_err:
        reasons.append(forbidden_cfg_err)

    if hit:
        status = "fallback_rejection"
        reasons.append(f"forbidden_domain_keyword:{hit}")
    else:
        if use_ko_lane and use_st and st_model:
            ko_for_ann = q_ko or retrieval_q
            ann_doc, ann_err = _run_ann_lite_structured_ko_only(
                ko_for_ann,
                max(1, int(args.top_k)),
                sqlite_path,
                sentence_transformer_model=str(st_model),
            )
        elif structured_bilingual and use_st and st_model:
            ann_doc, ann_err = _run_ann_lite_structured_hybrid(
                q_en,
                q_ko,
                max(1, int(args.top_k)),
                sqlite_path,
                hybrid_style=hybrid_style,
                sentence_transformer_model=str(st_model),
            )
        else:
            ann_doc, ann_err = _run_ann_lite_query(
                retrieval_q,
                max(1, int(args.top_k)),
                sqlite_path,
                sentence_transformer_model=st_model,
            )
        if ann_err:
            status = "ann_lite_skipped"
            reasons.append(ann_err)
        if args.invoke_cross_lens_fusion:
            fusion_ok, fusion_err = _run_cross_lens_fusion()
            if not fusion_ok and fusion_err:
                reasons.append(f"cross_lens_fusion:{fusion_err[:400]}")

    q_out: str | dict[str, Any]
    if args.redact_query:
        import hashlib

        h = hashlib.sha256(raw_q.encode("utf-8")).hexdigest()
        q_out = {"redacted": True, "sha256": h}
    else:
        q_out = raw_q

    out_doc: dict[str, Any] = {
        "schema": SCHEMA,
        "version": VERSION,
        "generated_at_utc": _utc_now(),
        "menu_id": str(args.menu_id),
        "track": "B",
        "research_only": True,
        "non_gating_ack": True,
        "promotion_status": "local_only_human_signoff_required",
        "status": status,
        "reasons": reasons,
        "user_query": q_out,
        "disclaimer_pack": {
            "hypothesis": "Outputs are [HYPO] / Track B; not medical, investment, or trading advice.",
            "medical": "Not a diagnosis; seek licensed professionals for symptoms.",
            "investment": "No buy/sell recommendations; finance domain is blocked in this pilot.",
            "logos": "Logos lens is advisory / [NON_GATING] per workspace lens contract.",
        },
        "forbidden_config_path": str(forbidden_path.resolve()),
        "forbidden_config_fallback": forbidden_cfg_err is not None,
        "rails_used": ["forbidden_substrings_v1", "logos_rag_query_route_v1", "logos_ann_lite_query_v1"]
        + (
            ["logos_rag_hybrid_query_v1"]
            if structured_bilingual and rag_lane != "ko_only"
            else []
        )
        + (["logos_rag_ko_only_lane_v1"] if structured_bilingual and rag_lane == "ko_only" else [])
        + (["cross_lens_rag_fusion_v1"] if args.invoke_cross_lens_fusion else []),
        "rag_query_route": {
            "policy": args.query_route,
            "detected": route,
            "applied": route_applied,
            "hangul_ratio": round(hangul_ratio(raw_q), 4),
            "retrieval_query": retrieval_q if not args.redact_query else {"redacted": True},
            "structured_bilingual": structured_bilingual,
            "rag_lane": rag_lane if structured_bilingual else None,
            "hybrid_style": hybrid_style if structured_bilingual and rag_lane != "ko_only" else None,
            "query_en": q_en if structured_bilingual and not args.redact_query else None,
            "query_ko": q_ko if structured_bilingual and not args.redact_query else None,
        },
        "ann_lite_sqlite": str(sqlite_path.resolve()),
        "ann_lite_use_st_index": use_st,
        "ann_lite_embedding_mode": _sqlite_embedding_mode(sqlite_path) if sqlite_path.is_file() else None,
        "sentence_transformer_model": st_model,
        "ann_lite_query": ann_doc,
        "cross_lens_fusion_invoked": bool(args.invoke_cross_lens_fusion),
        "cross_lens_fusion_ok": fusion_ok if args.invoke_cross_lens_fusion else None,
        "fusion_artifact_hint": "docs/final/artifacts/cross_lens_rag_fusion_latest.json",
        "m31_hormone_gate": {"status": "skipped_v1", "note": "Pilot v1 does not wire lens_music M31; add in v2 if needed."},
        "blocks": [] if status == "fallback_rejection" else _blocks_from_ann(ann_doc),
    }

    if status == "fallback_rejection":
        out_doc["blocks"] = [
            {
                "source_rail": "pilot_gate",
                "hypothesis_tag": "[HYPO]",
                "summary": "Question routed to safe fallback (forbidden domain).",
                "detail": "Retry with a philosophy / counsel / general life question outside blocked domains.",
                "evidence_path": None,
            }
        ]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(args.out.resolve()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
