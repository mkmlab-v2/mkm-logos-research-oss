#!/usr/bin/env python3
"""Phase 0 real-corpus smoke — medical_ko cmp2_011–040 · 41658 archived vs 41687 ([HYPO])."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.core.hangul_curated_eval_config_v1 import (  # noqa: E402
    INPUT_V2,
    MEDICAL_KO_CASE_IDS,
    active_run_config,
    evaluate_with_active_profile,
    subset_metrics,
)
PILOT = ROOT / "reports/constitution/btrack_pilot"
P41687 = PILOT / "master_codebook_lexicon_v1_41687_rows_latest.json"
OUT = ROOT / "reports/hangul_curated_real_corpus_smoke_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    return str(p.relative_to(ROOT)).replace("\\", "/")


def _resolve_archived_41658() -> Path | None:
    candidates = sorted(
        PILOT.glob("master_codebook_lexicon_v1_41658_rows_archived_*_pre_hangul_curated.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    fallback = PILOT / "master_codebook_lexicon_v1_41658_rows_latest.json"
    if candidates:
        return candidates[0]
    return fallback if fallback.is_file() else None


def _per_case_rows(cases: list[dict[str, Any]], id_set: frozenset[str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for c in cases:
        cid = str(c.get("id", ""))
        if cid not in id_set:
            continue
        route = c.get("route") or {}
        meta = route.get("master_codebook_lexicon_v1") or {}
        out.append(
            {
                "id": cid,
                "token_saving_rate": c.get("token_saving_rate"),
                "reconstruction_fidelity_jaccard": c.get("reconstruction_fidelity_jaccard"),
                "lexicon_hit_count": meta.get("hit_count"),
                "lexicon_hits_sample": (meta.get("hits_sample") or [])[:8],
            }
        )
    return out


def main() -> int:
    p658 = _resolve_archived_41658()
    if p658 is None or not P41687.is_file() or not INPUT_V2.is_file():
        print("ABORT: missing lexicon or bench input", file=sys.stderr)
        return 1

    src = json.loads(INPUT_V2.read_text(encoding="utf-8"))
    r658 = evaluate_with_active_profile(src, lexicon_path=p658)
    r687 = evaluate_with_active_profile(src, lexicon_path=P41687)

    cases658 = (r658.get("compression_metrics") or {}).get("cases") or []
    cases687 = (r687.get("compression_metrics") or {}).get("cases") or []

    m_all_658 = {
        "global_token_saving_rate": (r658.get("compression_metrics") or {}).get("global_token_saving_rate"),
        "avg_reconstruction_fidelity_jaccard": (r658.get("compression_metrics") or {}).get(
            "avg_reconstruction_fidelity_jaccard"
        ),
    }
    m_all_687 = {
        "global_token_saving_rate": (r687.get("compression_metrics") or {}).get("global_token_saving_rate"),
        "avg_reconstruction_fidelity_jaccard": (r687.get("compression_metrics") or {}).get(
            "avg_reconstruction_fidelity_jaccard"
        ),
    }
    sub658 = subset_metrics(cases658, MEDICAL_KO_CASE_IDS)
    sub687 = subset_metrics(cases687, MEDICAL_KO_CASE_IDS)

    delta_sub = {
        "avg_token_saving_rate": (sub687.get("avg_token_saving_rate") or 0)
        - (sub658.get("avg_token_saving_rate") or 0),
        "avg_reconstruction_fidelity_jaccard": (sub687.get("avg_reconstruction_fidelity_jaccard") or 0)
        - (sub658.get("avg_reconstruction_fidelity_jaccard") or 0),
        "cases_with_lexicon_hit_gt_0_delta": (sub687.get("cases_with_lexicon_hit_gt_0") or 0)
        - (sub658.get("cases_with_lexicon_hit_gt_0") or 0),
    }

    per_case_delta: list[dict[str, Any]] = []
    by658 = {str(c["id"]): c for c in _per_case_rows(cases658, MEDICAL_KO_CASE_IDS)}
    by687 = {str(c["id"]): c for c in _per_case_rows(cases687, MEDICAL_KO_CASE_IDS)}
    for cid in sorted(MEDICAL_KO_CASE_IDS):
        a, b = by658.get(cid), by687.get(cid)
        if not a or not b:
            continue
        per_case_delta.append(
            {
                "id": cid,
                "delta_saving": (b.get("token_saving_rate") or 0) - (a.get("token_saving_rate") or 0),
                "delta_jaccard": (b.get("reconstruction_fidelity_jaccard") or 0)
                - (a.get("reconstruction_fidelity_jaccard") or 0),
                "hit_count_41658": a.get("lexicon_hit_count"),
                "hit_count_41687": b.get("lexicon_hit_count"),
            }
        )

    doc: dict[str, Any] = {
        "schema": "hangul_curated_real_corpus_smoke_v1",
        "generated_at_utc": _utc(),
        "hypo_label": "[HYPO]",
        "research_only": True,
        "ms_paste_headline": "HOLD",
        "fail_comp_004": "Not Track A promotion or MS headline update.",
        "corpus_scope": {
            "label": "medical_ko_proxy_cmp2_011_040",
            "case_ids": sorted(MEDICAL_KO_CASE_IDS),
            "note": "Golden-40 Korean medical band; full clinical JSONL eval is Phase 1.",
        },
        "run_config_source": active_run_config(),
        "lexicon_paths": {
            "archived_41658": _rel(p658),
            "production_41687": _rel(P41687),
        },
        "golden40_full": {
            "archived_41658": m_all_658,
            "production_41687": m_all_687,
        },
        "medical_ko_subset": {
            "archived_41658": sub658,
            "production_41687": sub687,
            "delta_41687_minus_41658": delta_sub,
        },
        "per_case_medical_ko": per_case_delta,
        "smoke_verdict": {
            "subset_hit_lift_ok": (delta_sub.get("cases_with_lexicon_hit_gt_0_delta") or 0) >= 0,
            "subset_jaccard_drop_pp": round(
                (delta_sub.get("avg_reconstruction_fidelity_jaccard") or 0) * 100, 4
            ),
            "subset_saving_lift_pp": round((delta_sub.get("avg_token_saving_rate") or 0) * 100, 4),
        },
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(OUT), "verdict": doc["smoke_verdict"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
