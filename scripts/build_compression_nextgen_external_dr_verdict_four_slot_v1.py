#!/usr/bin/env python3
"""[HYPO] Four-slot disk verdict for nextgen latent indexer external DR ingestion."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TIER0 = ROOT / "docs/research/raw/compression_nextgen_latent_indexer_external_dr_2026-06-23.md"
DIGESTED = (
    ROOT
    / "docs/final/artifacts/compression_nextgen_latent_indexer_external_dr_2026-06-23_digested_facts_latest.json"
)
CHAIN = ROOT / "reports/mkm_digestion_engine_chain_v1_latest.json"
OUT = ROOT / "reports/compression_nextgen_external_dr_verdict_four_slot_v1_latest.json"
MERGED = (
    ROOT
    / "docs/research/COMPRESSION_NEXTGEN_LATENT_INDEXER_EXTERNAL_DR_MERGED_LIT_REVIEW_2026-06-23.md"
)

FAKE_PATHS = [
    "ng40_eval_v2",
    "MIPIC_SIA_Alignment_Block",
    "RAGDocumentPrestageTokenizer",
    "TelegraphEnglishSymbolicCompressor",
    "EmbeddingCheckpointMapper",
    "LatentFeatureExtractor",
    "ASG_SpectralGate",
    "LatentMetricsEvaluator",
]

REAL_PATHS = [
    "scripts/run_btrack_nextgen_indexer_parallel_bench_chain_v1.py",
    "scripts/run_ng40_codec_bench_split_chain_v1.py",
    "scripts/run_compression_conditional_fusion_ablation_v2_codec_rerun_v1.py",
    "scripts/run_ng40_path_b_dual_axis_push_v1.py",
    "experiments/nextgen_clean_slate_cpu_v1/results/ng40_latent_eval_best_v1_latest.json",
    "scripts/run_ng40_mipic_mrl_cka_eval_stub_v1.py",
    "experiments/nextgen_clean_slate_cpu_v1/results/ng40_mipic_mrl_cka_eval_stub_v1_latest.json",
    "scripts/run_ng40_carvq_embedding_lut_stub_v1.py",
    "experiments/nextgen_clean_slate_cpu_v1/results/ng40_carvq_embedding_lut_stub_v1_latest.json",
]

CANDIDATES = [
    {
        "id": "mipic",
        "arxiv": "2604.24374",
        "external_tag": "Adoptable",
        "tier": "B",
        "reason": "STS/NLI only; no Golden-40 Jaccard repro; fake class paths",
        "b_arm_status": "not_wired",
        "next_script": "scripts/run_ng40_mipic_mrl_cka_eval_stub_v1.py",
    },
    {
        "id": "carvq",
        "arxiv": "2510.12721",
        "external_tag": "Needs experiment",
        "tier": "B",
        "reason": "Embedding param compression; neighbor J unverified on G40",
        "b_arm_status": "not_wired",
        "next_script": "scripts/run_ng40_carvq_embedding_lut_stub_v1.py",
    },
    {
        "id": "telegraph_english",
        "arxiv": "2605.04426",
        "external_tag": "Adoptable",
        "tier": "A",
        "reason": "run_ng40_telegraph_english_spine_arm_v1.py exit0; beat_frozen false; J 0.923 saving negative (spine overhead)",
        "b_arm_status": "wired",
        "next_script": "scripts/run_ng40_telegraph_english_spine_arm_v1.py",
    },
    {
        "id": "asgmamba",
        "arxiv": "2602.01668",
        "external_tag": "Needs experiment",
        "tier": "D",
        "reason": "Time-series domain; no text indexer path",
        "b_arm_status": "deferred",
        "next_script": None,
    },
    {
        "id": "rwc_cptc",
        "arxiv": "2602.03903",
        "external_tag": "Marketing only",
        "tier": "D",
        "reason": "Conformal VaR calibration; not codec dual-axis",
        "b_arm_status": "deferred",
        "next_script": None,
    },
    {
        "id": "dual_axis_diagnosis",
        "arxiv": None,
        "external_tag": "FACT",
        "tier": "A",
        "reason": "ng40_latent_eval_best beat_check on disk",
        "b_arm_status": "wired",
        "next_script": "experiments/.../ng40_latent_eval_best_v1_latest.json",
    },
    {
        "id": "conditional_fusion_ablation",
        "arxiv": None,
        "external_tag": "FACT",
        "tier": "A",
        "reason": "v2 codec rerun exit 0; holdout min_j signal; beat_frozen false",
        "b_arm_status": "wired",
        "next_script": "scripts/run_compression_conditional_fusion_ablation_v2_codec_rerun_v1.py",
    },
    {
        "id": "codec_bench_split",
        "arxiv": None,
        "external_tag": "FACT",
        "tier": "A",
        "reason": "3-lane manifest; hybrid spine byte_exact 1.0",
        "b_arm_status": "wired",
        "next_script": "scripts/run_ng40_codec_bench_split_chain_v1.py",
    },
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _path_exists(rel: str) -> bool:
    return (ROOT / rel.replace("/", "\\")).is_file()


def _grep_fake_in_repo(name: str) -> bool:
  for base in (ROOT / "scripts", ROOT / "experiments"):
      if not base.is_dir():
          continue
      for p in base.rglob("*.py"):
          try:
              if name in p.read_text(encoding="utf-8", errors="ignore"):
                  return True
          except OSError:
              continue
  return False


def build() -> dict[str, Any]:
    digested = _load_json(DIGESTED) or {}
    chain = _load_json(CHAIN) or {}
    facts = digested.get("facts") or []
    right = sum(1 for f in facts if (f.get("verification") or {}).get("status") == "Right")
    unknown = sum(1 for f in facts if (f.get("verification") or {}).get("status") == "Unknown")

    fake_gaps = [
        {"symbol": name, "found_in_repo": _grep_fake_in_repo(name)} for name in FAKE_PATHS
    ]
    real_ok = {rel: _path_exists(rel) for rel in REAL_PATHS}

    candidates: list[dict[str, Any]] = []
    for c in CANDIDATES:
        row = dict(c)
        if row["id"] == "mipic" and real_ok.get("scripts/run_ng40_mipic_mrl_cka_eval_stub_v1.py"):
            stub = _load_json(
                ROOT
                / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_mipic_mrl_cka_eval_stub_v1_latest.json"
            )
            row["b_arm_status"] = "stub_wired" if stub else "wired_pending_run"
            if stub:
                bc = stub.get("beat_check") or {}
                row["reason"] = (
                    "MRL+CKA hashed-trigram stub on G40; "
                    f"beat_frozen={bc.get('beat_frozen')}; not paper STS/NLI"
                )
        if row["id"] == "carvq" and real_ok.get("scripts/run_ng40_carvq_embedding_lut_stub_v1.py"):
            stub = _load_json(
                ROOT
                / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_carvq_embedding_lut_stub_v1_latest.json"
            )
            row["b_arm_status"] = "stub_wired" if stub else "wired_pending_run"
            if stub:
                bc = stub.get("beat_check") or {}
                row["reason"] = (
                    "group-RVQ LUT stub on G40; "
                    f"beat_frozen={bc.get('beat_frozen')}; not LLM embedding perplexity"
                )
        candidates.append(row)

    ng40 = _load_json(
        ROOT / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_latent_eval_best_v1_latest.json"
    ) or {}
    fusion = _load_json(
        ROOT / "reports/compression_conditional_fusion_ablation_v2_codec_rerun_v1_latest.json"
    ) or {}

    raw = ng40.get("aggregate") or {}
    repair_note = "Golden-40 ng40 lane reports saving+J only; repair_v2 delta N/A on this cohort"

    doc = {
        "schema": "compression_nextgen_external_dr_verdict_four_slot_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "send_gate": "HOLD",
        "track_a_active_write": False,
        "tier0_path": "docs/research/raw/compression_nextgen_latent_indexer_external_dr_2026-06-23.md",
        "digested_facts_path": "docs/final/artifacts/compression_nextgen_latent_indexer_external_dr_2026-06-23_digested_facts_latest.json",
        "digestion_chain_ok": chain.get("ok"),
        "fact_stats": {
            "total": len(facts),
            "verification_right": right,
            "verification_unknown": unknown,
        },
        "four_slot": {
            "disk_verdict": {
                "overall_tier": "C",
                "summary_ko": "병목 진단·기존 체인은 Tier A; MIPIC/TE/CARVQ 구현·G40 재현은 Tier B GAP; fake paths 미존재",
                "candidates": candidates,
            },
            "reproduce": {
                "digestion": "py scripts/run_mkm_digestion_engine_chain_v1.py --input docs/research/raw/compression_nextgen_latent_indexer_external_dr_2026-06-23.md",
                "verdict": "py scripts/build_compression_nextgen_external_dr_verdict_four_slot_v1.py",
                "ng40_best": "experiments/nextgen_clean_slate_cpu_v1/results/ng40_latent_eval_best_v1_latest.json",
                "fusion_v2": "reports/compression_conditional_fusion_ablation_v2_codec_rerun_v1_latest.json",
                "fake_paths": fake_gaps,
                "real_paths": real_ok,
            },
            "raw_repair_v2": {
                "raw": {
                    "parse_ok_rate": None,
                    "alignment_pass_rate": None,
                    "global_token_saving_rate": raw.get("global_token_saving_rate"),
                    "avg_reconstruction_fidelity_jaccard": raw.get(
                        "avg_reconstruction_fidelity_jaccard"
                    ),
                    "cohort": "golden40_latent_best_sweep",
                },
                "repair_v2": {
                    "note": repair_note,
                    "alignment_pass_rate": None,
                },
                "delta": {
                    "alignment_pass_rate_delta_repair_v2_minus_raw": None,
                    "beat_frozen": (ng40.get("beat_check") or {}).get("beat_frozen"),
                    "conditional_beat_frozen": (fusion.get("beat_check_conditional_vs_frozen") or {}).get(
                        "beat_frozen"
                    ),
                },
            },
            "promotion": {
                "send_gate": "HOLD",
                "beat_frozen": False,
                "apply_active_forbidden": True,
                "human_signoff_required": True,
                "next_b_arms": [
                    c for c in candidates if c.get("b_arm_status") in ("not_wired", "lit_only")
                ],
            },
        },
        "merged_lit_review_pointer": MERGED.as_posix().replace(str(ROOT) + "/", ""),
        "reproducible_command": "py scripts/build_compression_nextgen_external_dr_verdict_four_slot_v1.py",
    }
    return doc


def _write_merged(verdict: dict[str, Any]) -> None:
    lines = [
        "# Compression nextgen latent indexer external DR — MERGED LIT_REVIEW [HYPO]",
        "",
        f"**Generated:** 2026-06-23 · **Tier:** 0→1 merge · **send_gate:** HOLD",
        "",
        "## Executive summary",
        "",
        verdict["four_slot"]["disk_verdict"]["summary_ko"],
        "",
        "## 4-slot",
        "",
        "| Slot | Verdict |",
        "|------|---------|",
        f"| Disk | Tier **C** — diagnosis wired; SOTA arms not implemented |",
        f"| Reproduce | digestion chain + `ng40_latent_eval_best` + fusion v2 |",
        f"| raw/repair_v2 | G40 saving+J only; repair_v2 N/A on this cohort |",
        f"| Promotion | HOLD · beat_frozen false |",
        "",
        "## Candidate tiers",
        "",
        "| ID | arXiv | Tier | B-arm |",
        "|----|-------|------|-------|",
    ]
    for c in verdict["four_slot"]["disk_verdict"]["candidates"]:
        lines.append(
            f"| {c['id']} | {c.get('arxiv') or '—'} | {c['tier']} | {c['b_arm_status']} |"
        )
    lines.extend(
        [
            "",
            "## SSOT pointers",
            "",
            f"- Tier 0: `{verdict['tier0_path']}`",
            f"- Digested: `{verdict['digested_facts_path']}`",
            f"- Verdict JSON: `reports/compression_nextgen_external_dr_verdict_four_slot_v1_latest.json`",
            "",
            "*B-track · research_only · not Track A promotion*",
        ]
    )
    MERGED.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    verdict = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(verdict, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _write_merged(verdict)
    print(json.dumps({"wrote": str(OUT), "tier": verdict["four_slot"]["disk_verdict"]["overall_tier"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
