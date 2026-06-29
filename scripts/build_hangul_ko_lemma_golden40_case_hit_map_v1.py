#!/usr/bin/env python3
"""Golden-40 × 42 ko lemma case hit map — 41658 baseline vs 41708 production lexicon."""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_master_codebook_golden40_lexicon_ab_v1 import (  # noqa: E402
    _load_signoff_relaxed,
    _metrics,
    _run_eval,
)
from scripts.core.master_codebook_lexicon_v1_bridge import (  # noqa: E402
    clear_codebook_cache,
    lexicon_hits_for_text,
)
from scripts.run_ultra_compression_default import INPUT_V2  # noqa: E402

PILOT = ROOT / "reports" / "constitution" / "btrack_pilot"
P658 = PILOT / "master_codebook_lexicon_v1_41658_rows_latest.json"
P708 = PILOT / "master_codebook_lexicon_v1_41708_rows_latest.json"
OUT = ROOT / "reports" / "hangul_ko_lemma_golden40_case_hit_map_v1_latest.json"
HANGUL_SUBSET = {f"cmp2_{i:03d}" for i in range(11, 41)}


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ko_inventory(path: Path) -> list[str]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    out: list[str] = []
    for ent in doc.get("entries") or []:
        if not isinstance(ent, dict):
            continue
        if ent.get("lang") == "ko" or str(ent.get("atom_id") or "").startswith("hangul_curated"):
            nf = ent.get("normalized_form")
            if isinstance(nf, str) and nf.strip():
                out.append(nf.strip())
    return sorted(set(out))


def main() -> int:
    if not INPUT_V2.is_file() or not P658.is_file() or not P708.is_file():
        print("ABORT: missing INPUT_V2 or lexicon paths")
        return 1

    clear_codebook_cache()
    src = json.loads(INPUT_V2.read_text(encoding="utf-8"))
    relaxed, allow, exclude = _load_signoff_relaxed()
    ko_lemmas = _ko_inventory(P708)
    ko_set = {k.lower() for k in ko_lemmas}

    r658 = _run_eval(
        src,
        lexicon_path=P658,
        domain_relaxed=relaxed,
        relaxed_case_allowlist=allow,
        relaxed_case_exclude=exclude,
    )
    r708 = _run_eval(
        src,
        lexicon_path=P708,
        domain_relaxed=relaxed,
        relaxed_case_allowlist=allow,
        relaxed_case_exclude=exclude,
    )

    by658 = {c["id"]: c for c in (r658.get("compression_metrics") or {}).get("cases") or []}
    by708 = {c["id"]: c for c in (r708.get("compression_metrics") or {}).get("cases") or []}
    raw_by = {str(c["id"]): str(c.get("raw_text") or "") for c in src.get("compression_cases") or []}

    rows: list[dict[str, Any]] = []
    lemma_fire: dict[str, int] = {}

    for cid in sorted(by658.keys()):
        raw = raw_by.get(cid, "")
        h658, _ = lexicon_hits_for_text(raw, P658)
        h708, _ = lexicon_hits_for_text(raw, P708)
        raw_tokens = {t.lower() for t in re.findall(r"\w+", raw, flags=re.UNICODE)}
        ko_hits = sorted(k for k in ko_set if k in raw_tokens)
        for k in ko_hits:
            lemma_fire[k] = lemma_fire.get(k, 0) + 1
        new_hits = sorted(h708 - h658)
        ko_new = sorted(set(new_hits) & ko_set)
        c658, c708 = by658[cid], by708[cid]
        ds = float(c708.get("token_saving_rate") or 0) - float(c658.get("token_saving_rate") or 0)
        dj = float(c708.get("reconstruction_fidelity_jaccard") or 0) - float(
            c658.get("reconstruction_fidelity_jaccard") or 0
        )
        route658 = (c658.get("route") or {}).get("master_codebook_lexicon_v1") or {}
        route708 = (c708.get("route") or {}).get("master_codebook_lexicon_v1") or {}
        rows.append(
            {
                "case_id": cid,
                "bench_lane": "cmp2_hangul_harness" if cid in HANGUL_SUBSET else "golden40_core",
                "domain": (c658.get("route") or {}).get("domain"),
                "ko_lemma_hits_in_raw": ko_hits,
                "ko_hit_count": len(ko_hits),
                "lexicon_hit_delta_708_minus_658": new_hits,
                "ko_only_lexicon_delta": ko_new,
                "baseline_41658_lexicon_hits": len(h658),
                "prod_41708_lexicon_hits": len(h708),
                "must_keep_meta_658": route658.get("hit_count"),
                "must_keep_meta_708": route708.get("hit_count"),
                "delta_saving_pp": round(ds * 100, 4),
                "delta_jaccard_pp": round(dj * 100, 4),
                "metric_changed": abs(ds) > 1e-9 or abs(dj) > 1e-9,
            }
        )

    m658 = _metrics(r658)
    m708 = _metrics(r708)
    summary = {
        "cases_total": len(rows),
        "cases_with_ko_hits": sum(1 for r in rows if r["ko_hit_count"] > 0),
        "cases_with_ko_lexicon_delta": sum(1 for r in rows if r["ko_only_lexicon_delta"]),
        "cases_with_metric_change": sum(1 for r in rows if r["metric_changed"]),
        "cmp2_subset_with_ko_hits": sum(
            1 for r in rows if r["bench_lane"] == "cmp2_hangul_harness" and r["ko_hit_count"] > 0
        ),
        "cmp2_subset_total": sum(1 for r in rows if r["bench_lane"] == "cmp2_hangul_harness"),
        "golden40_core_with_ko_hits": sum(
            1 for r in rows if r["bench_lane"] == "golden40_core" and r["ko_hit_count"] > 0
        ),
        "ko_lemma_fired_count": len(lemma_fire),
        "ko_lemma_never_fired_count": len(ko_set - set(lemma_fire)),
        "ko_lemma_fire_count": dict(sorted(lemma_fire.items(), key=lambda x: (-x[1], x[0]))),
        "metrics_41658": m658,
        "metrics_41708": m708,
        "aggregate_delta_saving_pp": round(
            (float(m708["global_token_saving_rate"]) - float(m658["global_token_saving_rate"])) * 100,
            4,
        ),
        "aggregate_delta_jaccard_pp": round(
            (
                float(m708["avg_reconstruction_fidelity_jaccard"])
                - float(m658["avg_reconstruction_fidelity_jaccard"])
            )
            * 100,
            4,
        ),
    }

    doc = {
        "schema": "hangul_ko_lemma_golden40_case_hit_map_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "reproduce": "py scripts/build_hangul_ko_lemma_golden40_case_hit_map_v1.py",
        "lexicon_baseline": str(P658.relative_to(ROOT)).replace("\\", "/"),
        "lexicon_production": str(P708.relative_to(ROOT)).replace("\\", "/"),
        "ko_lemma_inventory_count": len(ko_lemmas),
        "ko_lemma_inventory": ko_lemmas,
        "summary": summary,
        "cases": rows,
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"WROTE: {OUT}")
    print(
        f"ko_hits={summary['cases_with_ko_hits']}/40 "
        f"metric_changed={summary['cases_with_metric_change']} "
        f"delta_saving_pp={summary['aggregate_delta_saving_pp']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
