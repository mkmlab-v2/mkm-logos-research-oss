#!/usr/bin/env python3
"""[HYPO] Why harness lexicon hits (+38) do not move Golden-40 saving/Jaccard."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_master_codebook_golden40_lexicon_ab_v1 import (  # noqa: E402
    _load_signoff_relaxed,
    _run_eval,
)
from scripts.core.master_codebook_lexicon_v1_bridge import (  # noqa: E402
    lexicon_hits_for_text,
    resolve_latest_codebook_path,
)
from scripts.run_ultra_compression_default import INPUT_V2  # noqa: E402

OUT = ROOT / "reports/lexicon_hangul_p0_must_keep_wiring_probe_v1_latest.json"
HANGUL_IDS = {f"cmp2_{i:03d}" for i in range(11, 41)}


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    if not INPUT_V2.is_file():
        print("ABORT: missing INPUT_V2")
        return 1
    cb = resolve_latest_codebook_path()
    if cb is None:
        print("ABORT: lexicon missing")
        return 1

    src = json.loads(INPUT_V2.read_text(encoding="utf-8"))
    raw_by_id = {str(c["id"]): str(c.get("raw_text", "")) for c in src.get("compression_cases") or []}
    relaxed, allow, exclude = _load_signoff_relaxed()
    r0 = _run_eval(
        src,
        lexicon_path=cb,
        domain_relaxed=relaxed,
        relaxed_case_allowlist=allow,
        relaxed_case_exclude=exclude,
        include_hangul_tokenizer_harness=False,
    )
    r1 = _run_eval(
        src,
        lexicon_path=cb,
        domain_relaxed=relaxed,
        relaxed_case_allowlist=allow,
        relaxed_case_exclude=exclude,
        include_hangul_tokenizer_harness=True,
    )
    by0 = {str(c["id"]): c for c in (r0.get("compression_metrics") or {}).get("cases") or []}
    by1 = {str(c["id"]): c for c in (r1.get("compression_metrics") or {}).get("cases") or []}

    per_case: list[dict[str, Any]] = []
    total_new_hits = 0
    hits_already_in_baseline_comp = 0
    identical_comp_cases = 0

    for cid in sorted(HANGUL_IDS):
        if cid not in by0 or cid not in by1:
            continue
        c0, c1 = by0[cid], by1[cid]
        raw = raw_by_id.get(cid, "")
        h0, _ = lexicon_hits_for_text(raw, cb, include_hangul_tokenizer_harness=False)
        h1, _ = lexicon_hits_for_text(raw, cb, include_hangul_tokenizer_harness=True)
        delta = sorted(h1 - h0)
        comp0 = str(c0.get("compressed_text_effective") or c0.get("compressed_text") or "")
        comp1 = str(c1.get("compressed_text_effective") or c1.get("compressed_text") or "")
        comp_words = set(comp0.split())
        redundant = [h for h in delta if h in comp_words or h in comp0]
        total_new_hits += len(delta)
        hits_already_in_baseline_comp += len(redundant)
        comp_identical = comp0 == comp1
        if comp_identical:
            identical_comp_cases += 1
        per_case.append(
            {
                "id": cid,
                "baseline_hit_count": len(h0),
                "harness_hit_count": len(h1),
                "new_hits": delta,
                "new_hits_already_in_baseline_compressed": redundant,
                "compressed_text_identical": comp_identical,
                "baseline_saving": c0.get("token_saving_rate"),
                "harness_saving": c1.get("token_saving_rate"),
            }
        )

    doc = {
        "schema": "lexicon_hangul_p0_must_keep_wiring_probe_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "track_a_active_write": False,
        "would_change_active": False,
        "lexicon_path": str(cb.relative_to(ROOT)).replace("\\", "/"),
        "run_config_echo": {
            "strategy": r0.get("run_config", {}).get("strategy"),
            "intensity": r0.get("run_config", {}).get("intensity"),
        },
        "summary": {
            "hangul_case_count": len(per_case),
            "total_new_harness_hits": total_new_hits,
            "new_hits_already_in_baseline_compressed_count": hits_already_in_baseline_comp,
            "cases_identical_compressed_text": identical_comp_cases,
            "cases_with_metric_change": sum(
                1
                for r in per_case
                if r.get("baseline_saving") != r.get("harness_saving")
            ),
        },
        "root_cause": (
            "Lexicon harness expands must_keep (+38 hits on cmp2_011–040) but strategy A/extreme "
            "compression + min_saving_floor + caps already retain those surface forms in "
            "compressed_text_effective; must_keep is idempotent for KPI."
        ),
        "next_engineering": [
            "Ko ingest must change tokenizer/pruner path (L1 cheap_top_k), not only must_keep bridge.",
            "Overlay ingest without pruner tuning collapsed Golden-40 saving — see overlay_pilot golden40_compare.",
        ],
        "per_case": per_case,
        "pointers": {
            "p0_golden40_reeval": "reports/lexicon_hangul_p0_golden40_reeval_v1_latest.json",
            "overlay_pilot": "reports/lexicon_hangul_overlay_pilot_v1_latest.json",
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(OUT), **doc["summary"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
