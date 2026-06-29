#!/usr/bin/env python3
"""[HYPO] Prophecy edge shadow chain closure index (B-track, research_only).

Aggregates pointers + headline metrics from fABBA/Moirai/RQ-026/ensemble-v2
shadow work. No Track A mutation.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/prophecy_edge_shadow_chain_closure_v1_latest.json"
SCHEMA = "prophecy_edge_shadow_chain_closure_v1"

POINTERS: list[tuple[str, Path, str]] = [
    ("lit_review", ROOT / "docs/research/PROPHECY_EDGE_NEURO_SYMBOLIC_FINANCE_LIT_REVIEW_2026-06-22.md", "md"),
    ("fabba_sidecar_wf", ROOT / "reports/prophecy_fabba_sidecar_wf_shadow_v1_latest.json", "fabba_sidecar_ngram_pooled_hr"),
    ("fabba_dual_leg", ROOT / "reports/prophecy_fabba_sidecar_dual_leg_wf_v1_latest.json", "ngram_pooled"),
    ("fabba_sweep_revalidate", ROOT / "reports/prophecy_fabba_sidecar_sweep_dual_leg_revalidate_v1_latest.json", "dual_leg_best"),
    ("fabba_backend_ab", ROOT / "reports/prophecy_fabba_backend_ab_dual_leg_v1_latest.json", "compare"),
    ("fabba_backend_ab_linux_wsl", ROOT / "reports/prophecy_fabba_backend_ab_linux_wsl_v1_latest.json", "compare"),
    ("fabba_lut_ablation", ROOT / "reports/prophecy_fabba_lut_wf_ablation_smoke_v1_latest.json", "wf_parity"),
    ("moirai_dual_leg", ROOT / "reports/rq025_moirai2_dual_leg_wf_shadow_v1_latest.json", "moirai_pooled"),
    ("tsfm_stack_dual", ROOT / "reports/rq026_dual_leg_tsfm_stack_ensemble_wf_shadow_v1_latest.json", "best_honest"),
    ("ensemble_v2_compare", ROOT / "reports/btrack_ensemble_v2_wf_compare_v1_latest.json", "lanes"),
    ("ensemble_structural_ablation", ROOT / "reports/prophecy_dual_ensemble_structural_ablation_v1_latest.json", "lanes"),
    ("ensemble_hybrid_ablation", ROOT / "reports/prophecy_ensemble_v2_lens_opt_in_hybrid_ablation_v1_latest.json", "compare"),
    ("ensemble_hybrid_conf_sweep", ROOT / "reports/prophecy_ensemble_v2_lens_opt_in_confidence_sweep_v1_latest.json", "best_by_lens_mean"),
    ("primary_recommended", ROOT / "reports/prophecy_hit_rate_eval_recommended_chain_run_latest.json", "metrics"),
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        o = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None
    return o if isinstance(o, dict) else None


def _extract(doc: dict[str, Any] | None, kind: str) -> Any:
    if not doc:
        return None
    if kind == "metrics":
        return doc.get("metrics")
    if kind == "compare":
        return doc.get("compare")
    if kind == "lanes":
        return doc.get("lanes")
    if kind == "wf_parity":
        return doc.get("wf_parity")
    if kind == "best_by_lens_mean":
        return doc.get("best_by_lens_mean")
    if kind == "best_honest":
        c = doc.get("compare") or {}
        return {
            "arm_id": c.get("best_honest_arm_id"),
            "pooled_hr": c.get("best_honest_dual_leg_pooled_hr"),
        }
    if kind == "moirai_pooled":
        c = doc.get("compare") or {}
        return c.get("moirai_dual_leg_pooled_hr")
    if kind == "dual_leg_best":
        variants = doc.get("variants") or {}
        if isinstance(variants, dict):
            sb = variants.get("sweep_best_dual_leg") or {}
            ns = sb.get("ngram_summary") or {}
            if ns.get("pooled_hr") is not None:
                return ns.get("pooled_hr")
        v = doc.get("sweep_revalidated") or {}
        ns = (v.get("ngram_summary") or {}) if isinstance(v, dict) else {}
        if ns.get("pooled_hr") is not None:
            return ns.get("pooled_hr")
        v2 = doc.get("dual_leg_revalidated_best") or {}
        return v2.get("pooled_test_directional_hit_rate")
    if kind == "ngram_pooled":
        for a in doc.get("dual_leg_pooled_arms") or []:
            if a.get("arm_id") == "fabba_sidecar_ngram_lut":
                return a.get("pooled_test_directional_hit_rate")
        return None
    if kind == "fabba_sidecar_ngram_pooled_hr":
        s = doc.get("kospi_5bps_summary") or {}
        return s.get("fabba_sidecar_ngram_lut_pooled_hr")
    return None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    entries: list[dict[str, Any]] = []
    missing: list[str] = []
    for name, path, kind in POINTERS:
        if path.suffix == ".md":
            exists = path.is_file()
            entries.append({"id": name, "path": str(path), "kind": kind, "exists": exists})
            if not exists:
                missing.append(name)
            continue
        doc = _load(path)
        entries.append(
            {
                "id": name,
                "path": str(path),
                "kind": kind,
                "exists": doc is not None,
                "headline": _extract(doc, kind),
            }
        )
        if doc is None:
            missing.append(name)

    primary = _load(ROOT / "reports/prophecy_hit_rate_eval_recommended_chain_run_latest.json")
    primary_hr = ((primary or {}).get("metrics") or {}).get("price_directional_hit_rate")

    out: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "send_gate": "HOLD",
        "track_a_mutated": False,
        "primary_recommended_chain_hr": primary_hr,
        "headline_shadow_table": {
            "primary_ensemble_price_hit": primary_hr,
            "fabba_ngram_dual_leg_apca_stub": _extract(_load(ROOT / "reports/prophecy_fabba_backend_ab_linux_wsl_v1_latest.json"), "compare"),
            "moirai_dual_leg": _extract(_load(ROOT / "reports/rq025_moirai2_dual_leg_wf_shadow_v1_latest.json"), "moirai_pooled"),
            "tsfm_stack_dual_honest": _extract(_load(ROOT / "reports/rq026_dual_leg_tsfm_stack_ensemble_wf_shadow_v1_latest.json"), "best_honest"),
            "ensemble_v2_lens_hybrid_best": (_extract(_load(ROOT / "reports/prophecy_ensemble_v2_lens_opt_in_confidence_sweep_v1_latest.json"), "best_by_lens_mean") or {}).get("lens_mean_test_accuracy"),
            "fabba_linux_wsl_ngram_delta_fabba_minus_apca": (_extract(_load(ROOT / "reports/prophecy_fabba_backend_ab_linux_wsl_v1_latest.json"), "compare") or {}).get("ngram_hr_delta_fabba_minus_apca"),
        "fabba_linux_wsl_chain_exact_match_kospi": (
            (_load(ROOT / "reports/prophecy_fabba_backend_ab_linux_wsl_v1_latest.json") or {})
            .get("arms", {})
            .get("apca_stub", {})
            .get("symbolic_chain_compare", {})
            .get("kospi", {})
            .get("exact_chain_match_rate")
        ),
        },
        "artifacts": entries,
        "missing_artifacts": missing,
        "verdict_ko": [
            "모든 shadow KPI는 Primary 45%와 protocol·consumer 분리 보고",
            "combined_all_passed=false 유지 — Track A 승격 없음",
            "fabba real wheel A/B = Linux repro pending if fabba_native_available=false",
            "Linux WSL repro: apca vs fabba ngram HR delta 0 when chains 100% match — apca_stub sufficient for ngram arm",
        ],
        "reproduce": "py scripts/run_prophecy_edge_shadow_chain_closure_v1.py",
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output} missing={len(missing)} primary={primary_hr}")
    return 0 if not missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
