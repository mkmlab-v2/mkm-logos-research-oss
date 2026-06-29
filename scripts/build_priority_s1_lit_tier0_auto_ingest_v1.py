#!/usr/bin/env python3
"""[HYPO] Auto Tier0 ingest for priority S1 LIT (prophecy·lexicon·fact-lock·logos)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "docs/research/raw"
DIGEST = ROOT / "scripts/run_mkm_digestion_engine_chain_v1.py"
OUT = ROOT / "reports/priority_s1_lit_tier0_auto_ingest_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _fact(
    fact_id: str,
    metric_name: str,
    value: float,
    unit: str,
    arm: str,
    artifact_path: str,
    artifact_field: str,
    *,
    plane: str = "research_benchmarks",
    assertion: str = "eq",
) -> str:
    return f"""### fact_id: {fact_id}
- metric_name: {metric_name}
- value: {value}
- unit: {unit}
- comparison_arm: {arm}
- verification_status: Right
- verification_method: local_artifact
- baseline_plane: {plane}
- artifact_path: {artifact_path}
- artifact_field: {artifact_field}
- assertion: {assertion}
"""


def _build_prophecy() -> str:
    hit = _load(ROOT / "reports/prophecy_hit_rate_eval_recommended_chain_run_latest.json")
    gates = _load(ROOT / "reports/prophecy_promotion_gates_recommended_chain_v1_latest.json")
    lens = _load(ROOT / "reports/prophecy_per_date_combo_walkforward_recommended_chain_v1_latest.json")
    inst = _load(ROOT / "reports/prophecy_instrument_combo_walkforward_recommended_chain_v1_latest.json")
    combined = 0.0 if not gates.get("combined_all_passed") else 1.0
    facts = [
        _fact(
            "prophecy_price_directional_hit_rate",
            "price_directional_hit_rate",
            float(hit["metrics"]["price_directional_hit_rate"]),
            "ratio",
            "recommended_chain_dual_leg",
            "reports/prophecy_hit_rate_eval_recommended_chain_run_latest.json",
            "metrics.price_directional_hit_rate",
            plane="prophecy_btrack",
        ),
        _fact(
            "prophecy_n_evaluated",
            "n_evaluated",
            float(hit["metrics"]["n_evaluated"]),
            "count",
            "recommended_chain_dual_leg",
            "reports/prophecy_hit_rate_eval_recommended_chain_run_latest.json",
            "metrics.n_evaluated",
            plane="prophecy_btrack",
        ),
        _fact(
            "prophecy_lens_wf_mean_test_accuracy",
            "mean_test_accuracy",
            float(lens["aggregate"]["mean_test_accuracy"]),
            "ratio",
            "per_date_lens_wf",
            "reports/prophecy_per_date_combo_walkforward_recommended_chain_v1_latest.json",
            "aggregate.mean_test_accuracy",
            plane="prophecy_btrack",
        ),
        _fact(
            "prophecy_instrument_wf_mean_test_accuracy",
            "mean_test_accuracy",
            float(inst["aggregate"]["mean_test_accuracy"]),
            "ratio",
            "instrument_combo_wf",
            "reports/prophecy_instrument_combo_walkforward_recommended_chain_v1_latest.json",
            "aggregate.mean_test_accuracy",
            plane="prophecy_btrack",
        ),
        _fact(
            "prophecy_combined_all_passed",
            "combined_all_passed",
            combined,
            "count",
            "promotion_gates",
            "reports/prophecy_promotion_gates_recommended_chain_v1_latest.json",
            "combined_all_passed",
            plane="prophecy_btrack",
        ),
    ]
    return _wrap(
        "prophecy_edge_neuro_symbolic_finance_tier0_2026-06-23.md",
        "PROPHECY_EDGE_NEURO_SYMBOLIC_FINANCE_LIT_REVIEW_2026-06-22.md",
        "Prophecy B-track SSOT: recommended chain + WF gates; strict combined_all_passed false.",
        facts,
    )


def _build_lexicon() -> str:
    logos = _load(ROOT / "docs/final/artifacts/logos_narrative_lemma_overlap_eval_v1_latest.json")
    active = _load(ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json")
    cm = active.get("compression_metrics") or {}
    inp = logos.get("inputs") or {}
    facts = [
        _fact(
            "lexicon_row_count_41658",
            "lexicon_row_count",
            float(inp.get("lexicon_row_count") or 0),
            "count",
            "master_codebook_export",
            "docs/final/artifacts/logos_narrative_lemma_overlap_eval_v1_latest.json",
            "inputs.lexicon_row_count",
            plane="lexicon_rail",
        ),
        _fact(
            "bidirectional_verse_count",
            "bidirectional_verse_count",
            float(inp.get("bidirectional_verse_count") or 0),
            "count",
            "logos_bidirectional_index",
            "docs/final/artifacts/logos_narrative_lemma_overlap_eval_v1_latest.json",
            "inputs.bidirectional_verse_count",
            plane="lexicon_rail",
        ),
        _fact(
            "active_lexicon_on_saving",
            "global_token_saving_rate",
            float(cm["global_token_saving_rate"]),
            "ratio",
            "frozen_active",
            "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json",
            "compression_metrics.global_token_saving_rate",
            plane="golden40_latent",
        ),
        _fact(
            "active_lexicon_on_jaccard",
            "avg_reconstruction_fidelity_jaccard",
            float(cm["avg_reconstruction_fidelity_jaccard"]),
            "ratio",
            "frozen_active",
            "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json",
            "compression_metrics.avg_reconstruction_fidelity_jaccard",
            plane="golden40_latent",
        ),
    ]
    return _wrap(
        "root_lexicon_41k_4d_evolution_tier0_2026-06-23.md",
        "ROOT_LEXICON_41K_4D_EVOLUTION_LIT_REVIEW_2026-06-21.md",
        "41k lexicon rail vs 4D bridge OFF; disk row counts from lemma overlap eval.",
        facts,
    )


def _build_fact_lock() -> str:
    dr = _load(ROOT / "reports/mkm_deep_research_bench_mini_v1_latest.json")
    inv = _load(ROOT / "reports/mkm_research_digestion_inventory_v1_latest.json")
    chain = _load(ROOT / "reports/mkm_digestion_engine_chain_v1_latest.json")
    facts = [
        _fact(
            "dr_bench_tasks_ok",
            "tasks_ok",
            float(dr["metrics"]["tasks_ok"]),
            "count",
            "dr_bench_mini_offline",
            "reports/mkm_deep_research_bench_mini_v1_latest.json",
            "metrics.tasks_ok",
        ),
        _fact(
            "dr_bench_citation_pass_rate_mean",
            "citation_pass_rate_mean",
            float(dr["metrics"]["citation_pass_rate_mean"]),
            "ratio",
            "dr_bench_mini_offline",
            "reports/mkm_deep_research_bench_mini_v1_latest.json",
            "metrics.citation_pass_rate_mean",
        ),
        _fact(
            "digestion_inventory_s3_count",
            "s3_count",
            float(inv["summary"]["s3_count"]),
            "count",
            "research_digestion_inventory",
            "reports/mkm_research_digestion_inventory_v1_latest.json",
            "summary.s3_count",
        ),
        _fact(
            "digestion_chain_ok",
            "ok",
            1.0 if chain.get("ok") else 0.0,
            "count",
            "mkm_digestion_engine_chain",
            "reports/mkm_digestion_engine_chain_v1_latest.json",
            "ok",
        ),
    ]
    return _wrap(
        "mkm_fact_lock_insight_engine_stress_test_tier0_2026-06-23.md",
        "MKM_FACT_LOCK_INSIGHT_ENGINE_STRESS_TEST_LIT_REVIEW_2026-06-23.md",
        "Stress test LIT wired to DR bench mini + digestion inventory on disk.",
        facts,
    )


def _build_logos_graphrag() -> str:
    logos = _load(ROOT / "docs/final/artifacts/logos_narrative_lemma_overlap_eval_v1_latest.json")
    gap = _load(ROOT / "reports/ollama_shallow_routing_oracle_gap_v1_latest.json")
    inp = logos.get("inputs") or {}
    raw_gap = (gap.get("raw") or {}).get("routing_oracle_gap", 0.0)
    facts = [
        _fact(
            "logos_lemma_index_verse_count",
            "lemma_index_verse_count",
            float(inp.get("lemma_index_verse_count") or 0),
            "count",
            "logos_lemma_edges",
            "docs/final/artifacts/logos_narrative_lemma_overlap_eval_v1_latest.json",
            "inputs.lemma_index_verse_count",
            plane="logos_btrack",
        ),
        _fact(
            "logos_bidirectional_verse_count",
            "bidirectional_verse_count",
            float(inp.get("bidirectional_verse_count") or 0),
            "count",
            "logos_bidirectional_index",
            "docs/final/artifacts/logos_narrative_lemma_overlap_eval_v1_latest.json",
            "inputs.bidirectional_verse_count",
            plane="logos_btrack",
        ),
        _fact(
            "ollama_shallow_routing_oracle_gap",
            "routing_oracle_gap",
            float(raw_gap),
            "ratio",
            "ollama_shallow_router_bench",
            "reports/ollama_shallow_routing_oracle_gap_v1_latest.json",
            "raw.routing_oracle_gap",
            plane="logos_btrack",
        ),
    ]
    return _wrap(
        "logos_graphrag_4d_ollama_tier0_2026-06-23.md",
        "LOGOS_GRAPHRAG_4D_OLLAMA_LIT_REVIEW_2026-06-21.md",
        "Logos GraphRAG + shallow router: lemma index counts + oracle_gap on disk.",
        facts,
    )


def _wrap(filename: str, lit: str, summary: str, facts: list[str]) -> str:
    rel = f"docs/research/raw/{filename}"
    return f"""# {lit} — Tier0 auto-ingest

**Generated:** {_utc()} · **Source LIT:** docs/research/{lit}
**Track:** B-track · research_only · send_gate HOLD

## Summary

{summary}

## Digested facts

{"".join(facts)}

## Reproduce

```powershell
py scripts/run_mkm_digestion_engine_chain_v1.py --input {rel} --offline
```
"""


TOPICS: list[tuple[str, Callable[[], str]]] = [
    ("prophecy_edge_neuro_symbolic_finance_tier0_2026-06-23.md", _build_prophecy),
    ("root_lexicon_41k_4d_evolution_tier0_2026-06-23.md", _build_lexicon),
    ("mkm_fact_lock_insight_engine_stress_test_tier0_2026-06-23.md", _build_fact_lock),
    ("logos_graphrag_4d_ollama_tier0_2026-06-23.md", _build_logos_graphrag),
]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-digest", action="store_true")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []
    rc = 0

    for filename, builder in TOPICS:
        path = RAW / filename
        rel = path.relative_to(ROOT).as_posix()
        if path.is_file() and not args.force:
            steps.append({"file": rel, "action": "skip_exists"})
        else:
            RAW.mkdir(parents=True, exist_ok=True)
            path.write_text(builder(), encoding="utf-8")
            steps.append({"file": rel, "action": "wrote"})

        if not args.skip_digest:
            cp = subprocess.run(
                [sys.executable, str(DIGEST), "--input", rel, "--offline"],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
            )
            tail = (cp.stdout or "").strip().splitlines()
            parsed = json.loads(tail[-1]) if tail else None
            steps.append({"file": rel, "digest_exit_code": int(cp.returncode), "parsed": parsed})
            if cp.returncode != 0:
                rc = cp.returncode

    manifest = {
        "schema": "priority_s1_lit_tier0_auto_ingest_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "steps": steps,
        "rc": rc,
        "reproducible_command": "py scripts/build_priority_s1_lit_tier0_auto_ingest_v1.py",
    }
    OUT.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(OUT), "rc": rc, "topics": len(TOPICS)}))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
