#!/usr/bin/env python3
"""Build candidate_pool_on Track A *candidate* envelope from 41k combo grid SSOT.

Never overwrites MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json.
Commander/human gate required for any Track A promotion.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GRID = ROOT / "reports/compression_41k_best_combo_grid_v1_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/compression_candidate_pool_on_track_a_candidate_v1_latest.json"
TRACK_A_ACTIVE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
SIGNOFF = ROOT / "docs/final/artifacts/multilens_ultra_compression_track_a_promotion_signoff_v1_latest.json"

# Field corpora used for Tier A gates (exclude open_structured_long artifact).
TIER_A_FIELD_CORPORA = frozenset({"public_open_web_v1", "wtt_premium_cs_customer_v1"})


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _track_a_baseline() -> dict[str, Any]:
    if not TRACK_A_ACTIVE.is_file():
        return {"available": False}
    doc = _load(TRACK_A_ACTIVE)
    cm = doc.get("compression_metrics") or {}
    return {
        "available": True,
        "path": _rel(TRACK_A_ACTIVE),
        "global_token_saving_rate": cm.get("global_token_saving_rate"),
        "avg_reconstruction_fidelity_jaccard": cm.get("avg_reconstruction_fidelity_jaccard"),
        "min_reconstruction_fidelity_jaccard": cm.get("min_reconstruction_fidelity_jaccard"),
        "note": "Read-only frozen ACTIVE; candidate does not auto-merge.",
    }


def _find_combo_config(grid: dict[str, Any], combo_id: str) -> dict[str, Any]:
    for row in grid.get("golden40_ranking") or []:
        if isinstance(row, dict) and row.get("combo_id") == combo_id:
            cfg = row.get("config")
            return dict(cfg) if isinstance(cfg, dict) else {}
    best = grid.get("best_combo") or {}
    if best.get("combo_id") == combo_id:
        for row in grid.get("golden40_ranking") or []:
            if row.get("combo_id") == combo_id:
                cfg = row.get("config")
                return dict(cfg) if isinstance(cfg, dict) else {}
    return {}


def _field_tier_a_summary(best: dict[str, Any]) -> dict[str, Any]:
    corpora = best.get("field_corpora") or []
    tier_rows = [c for c in corpora if isinstance(c, dict) and c.get("corpus_id") in TIER_A_FIELD_CORPORA]
    pass_rates = [float(c["case_pass_rate"]) for c in tier_rows if isinstance(c.get("case_pass_rate"), (int, float))]
    return {
        "corpus_ids": sorted(TIER_A_FIELD_CORPORA),
        "excluded_artifact_corpus": "open_structured_long_v1",
        "mean_case_pass_rate": sum(pass_rates) / len(pass_rates) if pass_rates else None,
        "corpora": tier_rows,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--grid-json", type=Path, default=DEFAULT_GRID)
    ap.add_argument("--combo-id", default="candidate_pool_on")
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    grid_path = args.grid_json.resolve()
    if not grid_path.is_file():
        print(f"error: missing grid artifact: {grid_path}", file=sys.stderr)
        return 2

    grid = _load(grid_path)
    best = grid.get("best_combo") or {}
    if best.get("combo_id") != args.combo_id:
        print(
            f"error: grid best_combo={best.get('combo_id')!r} != requested {args.combo_id!r}",
            file=sys.stderr,
        )
        return 2

    cfg = _find_combo_config(grid, args.combo_id)
    frozen = grid.get("frozen_active_baseline") or {}
    golden = best.get("golden40") or {}
    active_baseline = _track_a_baseline()

    allow = cfg.get("domain_relaxed_max_saving_case_allowlist")
    allow_list = list(allow) if allow else None

    run_config: dict[str, Any] = {
        "use_master_codebook_lexicon_v1": bool(cfg.get("use_master_codebook_lexicon_v1", True)),
        "apply_gematria_4d_bridge_policy": bool(cfg.get("apply_gematria_4d_bridge_policy", False)),
        "enable_candidate_pool_expansion": True,
        "enable_router_blend_candidate": bool(cfg.get("enable_router_blend_candidate", False)),
        "domain_relaxed_max_saving_overrides": dict(cfg.get("domain_relaxed_max_saving_overrides") or {}),
        "domain_relaxed_max_saving_case_allowlist": allow_list,
        "routing_profile": "candidate_pool_on",
        "compression_profile": "economy",
        "source_input": "api:v2_trust_packet",
        "mode": "experimental",
    }

    doc: dict[str, Any] = {
        "schema": "compression_candidate_pool_on_track_a_candidate_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "send_gate": "HOLD",
        "track_a_active_untouched": True,
        "candidate_id": args.combo_id,
        "label_ko": best.get("label_ko") or "41k ON · candidate pool expansion",
        "source_grid_artifact": _rel(grid_path),
        "promotion_signoff_pointer": _rel(SIGNOFF) if SIGNOFF.is_file() else None,
        "run_config": run_config,
        "evidence": {
            "composite_score": best.get("composite_score"),
            "golden40": golden,
            "field_corpora_all": best.get("field_corpora") or [],
            "field_tier_a": _field_tier_a_summary(best),
            "delta_vs_frozen_active": {
                "global_token_saving_rate_pp": (
                    float(golden.get("global_token_saving_rate", 0))
                    - float(frozen.get("global_token_saving_rate", 0))
                )
                if golden.get("global_token_saving_rate") is not None
                and frozen.get("global_token_saving_rate") is not None
                else None,
                "avg_jaccard_pp": (
                    float(golden.get("avg_reconstruction_fidelity_jaccard", 0))
                    - float(frozen.get("avg_reconstruction_fidelity_jaccard", 0))
                )
                if golden.get("avg_reconstruction_fidelity_jaccard") is not None
                and frozen.get("avg_reconstruction_fidelity_jaccard") is not None
                else None,
            },
        },
        "track_a_frozen_baseline": active_baseline,
        "gates": {
            "golden40_jaccard_floor": grid.get("field_jaccard_floor", 0.73),
            "golden40_saving_policy_floor": grid.get("policy_floor", 0.47),
            "tier_a_field_corpora": sorted(TIER_A_FIELD_CORPORA),
            "tier_a_exclude_corpus": "open_structured_long_v1",
            "auto_promote_ready": False,
            "human_approval_required": True,
        },
        "boundary_ack": (
            "evaluate_report bench path with candidate pool expansion. "
            "Does not overwrite ACTIVE report or enable SEND. "
            "v2 economy stateless path remains separate (~8% in sota ablation)."
        ),
        "reproduce": (
            "py scripts/run_compression_41k_best_combo_grid_v1.py && "
            "py scripts/build_compression_candidate_pool_on_track_a_candidate_v1.py"
        ),
    }

    out_path = args.out_json.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "candidate_id": args.combo_id}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
