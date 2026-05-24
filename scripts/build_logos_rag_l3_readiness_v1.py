#!/usr/bin/env python3
"""L3 readiness: hash_stub production index vs B-track ST-U (no prod swap)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_logos_rag_retrieval_round_v1 import (  # noqa: E402
    DEFAULT_MODEL,
    DEFAULT_SQLITE as ST_SQLITE,
    _encode_query,
    _load_index,
    _retrieve_baseline,
    _score_all,
    preprocess_query,
)
from scripts.logos_ann_lite_embedding_v1 import load_sentence_transformer  # noqa: E402

ART = ROOT / "docs/final/artifacts"
PILOT = ROOT / "reports/constitution/btrack_pilot"
PROD_SQLITE = ART / "logos_vector_index_ann_lite_v1.sqlite"
V4 = ART / "logos_semantic_query_set_v4_ko_en_v1.json"
DEFAULT_OUT = ART / "logos_rag_l3_readiness_v1_latest.json"

L3_MIN_KO_MEAN_ST = 0.33
L3_MIN_ST_ROWS = 28_000


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _probe_index(sqlite: Path, queries: list[tuple[str, str]], model: Any) -> dict[str, Any]:
    index_rows, dim, mode = _load_index(sqlite)
    scores: list[float] = []
    for _qid, ko in queries:
        qvec = _encode_query(model, preprocess_query(ko))
        scored = _score_all(qvec, index_rows, dim)
        hits = _retrieve_baseline(scored, 1)
        sc = hits[0].get("score") if hits else None
        if isinstance(sc, (int, float)):
            scores.append(float(sc))
    mean = sum(scores) / len(scores) if scores else None
    return {"rows": len(index_rows), "embedding_mode": mode, "mean_top1_ko": mean}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    v4 = json.loads(V4.read_text(encoding="utf-8-sig"))
    queries = [
        (str(it["id"]), str(it.get("query_ko") or ""))
        for it in v4.get("items") or []
        if isinstance(it, dict) and it.get("query_ko")
    ]
    model = load_sentence_transformer(DEFAULT_MODEL)

    prod_ok = PROD_SQLITE.is_file()
    st_ok = ST_SQLITE.is_file()
    prod: dict[str, Any] = {"available": prod_ok}
    st: dict[str, Any] = {"available": st_ok, "path": str(ST_SQLITE)}

    if prod_ok:
        try:
            prod = {**prod, **_probe_index(PROD_SQLITE, queries, model)}
        except Exception as e:
            prod["error"] = str(e)
    if st_ok:
        st = {**st, **_probe_index(ST_SQLITE, queries, model)}

    st_mean = st.get("mean_top1_ko")
    checks = {
        "st_index_rows_ge_min": (st.get("rows") or 0) >= L3_MIN_ST_ROWS,
        "st_ko_mean_ge_min": st_mean is not None and st_mean >= L3_MIN_KO_MEAN_ST,
        "prod_index_readable": prod_ok and "error" not in prod,
        "l2_ingest_complete": (ART / "logos_rag_l2_post_ingest_v1_latest.json").is_file(),
        "commander_l3_approval_required": True,
    }
    approval_ready = all(
        [
            checks["st_index_rows_ge_min"],
            checks["st_ko_mean_ge_min"],
            checks["l2_ingest_complete"],
        ]
    )

    doc = {
        "schema": "logos_rag_l3_readiness_v1",
        "ts_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "production_hash_stub_index": prod,
        "btrack_st_u_index": st,
        "delta_st_minus_prod_mean": (
            None
            if st_mean is None or prod.get("mean_top1_ko") is None
            else round(st_mean - float(prod["mean_top1_ko"]), 9)
        ),
        "checks": checks,
        "approval_ready": approval_ready,
        "recommended_commander_action": "ACK_L3_PRODUCTION_ST_INDEX" if approval_ready else "HOLD_L3",
        "track_wall": {
            "prophecy_promotion_gates_touch": False,
            "track_a_compression_touch": False,
            "use_gematria_4d_bridge": False,
            "does_not_modify": str(PROD_SQLITE),
            "note": "Readiness only; run record --tier L3 after explicit chat approval.",
        },
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "approval_ready": approval_ready,
                "st_mean": st_mean,
                "prod_mean": prod.get("mean_top1_ko"),
                "out": str(args.output_json),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
