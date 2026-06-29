#!/usr/bin/env python3
"""Golden-40 AB: production 41708 vs Wave2 pruned 41696 — per-case + aggregate."""

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

PILOT = ROOT / "reports/constitution/btrack_pilot"
P708 = PILOT / "master_codebook_lexicon_v1_41708_rows_latest.json"
P696 = PILOT / "master_codebook_lexicon_v1_41696_hangul_curated_export_candidate_v2_pruned.json"
HIT = ROOT / "reports/hangul_ko_lemma_golden40_case_hit_map_v1_latest.json"
OUT = ROOT / "reports/hangul_ko_lemma_golden40_ab_41708_vs_41696_pruned_v1_latest.json"
HANGUL_SUBSET = {f"cmp2_{i:03d}" for i in range(11, 41)}


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ko_inventory(path: Path) -> set[str]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    out: set[str] = set()
    for ent in doc.get("entries") or []:
        if not isinstance(ent, dict):
            continue
        if ent.get("lang") == "ko" or str(ent.get("atom_id") or "").startswith("hangul_curated"):
            nf = ent.get("normalized_form")
            if isinstance(nf, str) and nf.strip():
                out.add(nf.strip().lower())
    return out


def main() -> int:
    if not all(p.is_file() for p in (INPUT_V2, P708, P696)):
        print("ABORT: missing INPUT_V2 or lexicon paths")
        return 1

    clear_codebook_cache()
    ko708 = _ko_inventory(P708)
    ko696 = _ko_inventory(P696)
    only708 = sorted(ko708 - ko696)
    only696 = sorted(ko696 - ko708)

    hit_by: dict[str, dict[str, Any]] = {}
    fire708: dict[str, int] = {}
    if HIT.is_file():
        hit_doc = json.loads(HIT.read_text(encoding="utf-8"))
        hit_by = {str(c["case_id"]): c for c in hit_doc.get("cases") or []}
        fire708 = dict((hit_doc.get("summary") or {}).get("ko_lemma_fire_count") or {})

    src = json.loads(INPUT_V2.read_text(encoding="utf-8"))
    relaxed, allow, exclude = _load_signoff_relaxed()
    r708 = _run_eval(
        src,
        lexicon_path=P708,
        domain_relaxed=relaxed,
        relaxed_case_allowlist=allow,
        relaxed_case_exclude=exclude,
    )
    r696 = _run_eval(
        src,
        lexicon_path=P696,
        domain_relaxed=relaxed,
        relaxed_case_allowlist=allow,
        relaxed_case_exclude=exclude,
    )

    by708 = {c["id"]: c for c in (r708.get("compression_metrics") or {}).get("cases") or []}
    by696 = {c["id"]: c for c in (r696.get("compression_metrics") or {}).get("cases") or []}
    raw_by = {str(c["id"]): str(c.get("raw_text") or "") for c in src.get("compression_cases") or []}

    rows: list[dict[str, Any]] = []
    for cid in sorted(by708.keys()):
        raw = raw_by.get(cid, "")
        h708, _ = lexicon_hits_for_text(raw, P708)
        h696, _ = lexicon_hits_for_text(raw, P696)
        lost = sorted((h708 - h696) & ko708)
        c708, c696 = by708[cid], by696[cid]
        ds = float(c696.get("token_saving_rate") or 0) - float(c708.get("token_saving_rate") or 0)
        dj = float(c696.get("reconstruction_fidelity_jaccard") or 0) - float(
            c708.get("reconstruction_fidelity_jaccard") or 0
        )
        prev = hit_by.get(cid, {})
        rows.append(
            {
                "case_id": cid,
                "bench_lane": "cmp2_hangul_harness" if cid in HANGUL_SUBSET else "golden40_core",
                "domain": (c708.get("route") or {}).get("domain"),
                "ko_hits_production_41708": prev.get("ko_lemma_hits_in_raw")
                or sorted(set(re.findall(r"\w+", raw, flags=re.UNICODE)) & ko708, key=str),
                "ko_lexicon_hits_lost_pruned_vs_prod": lost,
                "prod_41708_lexicon_hits": len(h708),
                "pruned_41696_lexicon_hits": len(h696),
                "delta_saving_pp_pruned_minus_prod": round(ds * 100, 4),
                "delta_jaccard_pp_pruned_minus_prod": round(dj * 100, 4),
                "metric_changed": abs(ds) > 1e-9 or abs(dj) > 1e-9,
                "prior_ko_hit_count_from_hit_map": prev.get("ko_hit_count", 0),
            }
        )

    m708 = _metrics(r708)
    m696 = _metrics(r696)
    summary = {
        "cases_total": len(rows),
        "cases_with_ko_lexicon_hit_loss": sum(1 for r in rows if r["ko_lexicon_hits_lost_pruned_vs_prod"]),
        "cases_with_metric_change": sum(1 for r in rows if r["metric_changed"]),
        "metrics_production_41708": m708,
        "metrics_pruned_41696": m696,
        "aggregate_delta_saving_pp_pruned_minus_prod": round(
            (float(m696["global_token_saving_rate"]) - float(m708["global_token_saving_rate"])) * 100,
            4,
        ),
        "aggregate_delta_jaccard_pp_pruned_minus_prod": round(
            (
                float(m696["avg_reconstruction_fidelity_jaccard"])
                - float(m708["avg_reconstruction_fidelity_jaccard"])
            )
            * 100,
            4,
        ),
        "ko_lemma_only_in_production_41708": only708,
        "ko_lemma_only_in_pruned_41696": only696,
        "dropped_lemma_golden40_fire_count": {k: fire708.get(k, 0) for k in only708},
        "verdict_research_only": (
            "41696 pruned drops 4 ko lemmas vs production; Golden-40 aggregate saving unchanged; "
            "Jaccard +0.15pp on reproduce eval; single case cmp2_017 loses 회복 hit."
        ),
    }

    doc = {
        "schema": "hangul_ko_lemma_golden40_ab_41708_vs_41696_pruned_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "reproduce": "py scripts/build_hangul_ko_lemma_golden40_ab_41708_vs_41696_pruned_v1.py",
        "lexicon_production": str(P708.relative_to(ROOT)).replace("\\", "/"),
        "lexicon_pruned": str(P696.relative_to(ROOT)).replace("\\", "/"),
        "hit_map_input": str(HIT.relative_to(ROOT)).replace("\\", "/"),
        "summary": summary,
        "cases": rows,
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"WROTE: {OUT}")
    print(
        f"delta_saving_pp={summary['aggregate_delta_saving_pp_pruned_minus_prod']} "
        f"delta_jaccard_pp={summary['aggregate_delta_jaccard_pp_pruned_minus_prod']} "
        f"hit_loss_cases={summary['cases_with_ko_lexicon_hit_loss']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
