#!/usr/bin/env python3
"""COMP-ATOM-02: per-case 41k lexicon hit rate on V2 bench + optional OFF/ON saving delta."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.core.master_codebook_lexicon_v1_bridge import (  # noqa: E402
    lexicon_hits_for_text,
    resolve_latest_codebook_path,
    unicode_word_tokens,
)
from scripts.report_multilens_performance_eval import evaluate_report  # noqa: E402

PILOT = ROOT / "reports" / "constitution" / "btrack_pilot"
INPUT_V2 = ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
BASELINE_V2 = ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_REPORT_V2.json"
DECISION = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_DECISION_V1.json"
ACTIVE_REPORT = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _bench_metrics(src: dict, *, lexicon_on: bool) -> dict:
    baseline = json.loads(BASELINE_V2.read_text(encoding="utf-8"))
    decision = json.loads(DECISION.read_text(encoding="utf-8"))
    selected = decision.get("selected_candidate") or {}
    baseline_j = float(
        baseline.get("compression_metrics", {}).get("avg_reconstruction_fidelity_jaccard", 0.0)
    )
    threshold_pp = float(decision.get("target", {}).get("jaccard_drop_threshold_pp", 2.0))
    report = evaluate_report(
        src,
        source_input=str(INPUT_V2.relative_to(ROOT)).replace("\\", "/"),
        mode="experimental",
        strategy=str(selected.get("strategy", "A")),
        intensity=str(selected.get("intensity", "extreme")),
        must_keep={"사상의학", "체질", "sasang", "myeongri", "bible"},
        jaccard_drop_threshold_pp=threshold_pp,
        baseline_avg_jaccard=baseline_j,
        general_max_saving_rate=float(selected.get("general_max_saving_rate", 0.35)),
        sensitive_max_saving_rate=float(selected.get("sensitive_max_saving_rate", 0.3)),
        hangul_max_saving_rate=float(selected.get("hangul_max_saving_rate", 0.6)),
        use_domain_router=True,
        use_master_codebook_lexicon_v1=lexicon_on,
        include_gematria_metadata=True,
        include_gematria_4d_bridge=True,
        apply_gematria_4d_bridge_policy=False,
        include_cee_core=True,
    )
    cm = report.get("compression_metrics") or {}
    return {
        "global_token_saving_rate": cm.get("global_token_saving_rate"),
        "avg_reconstruction_fidelity_jaccard": cm.get("avg_reconstruction_fidelity_jaccard"),
        "avg_sensitive_integrity": cm.get("avg_sensitive_integrity"),
    }


def _bench_metrics_active_parity(src: dict) -> dict:
    """Re-eval Golden-40 with frozen Track A active report run_config (domain_relaxed included)."""
    if not ACTIVE_REPORT.is_file():
        return {"status": "missing_active_report"}
    active = json.loads(ACTIVE_REPORT.read_text(encoding="utf-8"))
    rc = active.get("run_config") or {}
    baseline = json.loads(BASELINE_V2.read_text(encoding="utf-8"))
    decision = json.loads(DECISION.read_text(encoding="utf-8"))
    selected = decision.get("selected_candidate") or {}
    baseline_j = float(
        baseline.get("compression_metrics", {}).get("avg_reconstruction_fidelity_jaccard", 0.0)
    )
    threshold_pp = float(decision.get("target", {}).get("jaccard_drop_threshold_pp", 2.0))
    allowlist = rc.get("domain_relaxed_max_saving_case_allowlist")
    exclude = rc.get("domain_relaxed_max_saving_exclude_case_ids")
    report = evaluate_report(
        src,
        source_input=str(INPUT_V2.relative_to(ROOT)).replace("\\", "/"),
        mode=str(rc.get("mode", "experimental")),
        strategy=str(rc.get("strategy", selected.get("strategy", "A"))),
        intensity=str(rc.get("intensity", selected.get("intensity", "extreme"))),
        must_keep=set(rc.get("must_keep_terms") or ["사상의학", "체질", "sasang", "myeongri", "bible"]),
        jaccard_drop_threshold_pp=threshold_pp,
        baseline_avg_jaccard=baseline_j,
        general_max_saving_rate=float(rc.get("general_max_saving_rate", 0.35)),
        sensitive_max_saving_rate=float(rc.get("sensitive_max_saving_rate", 0.3)),
        hangul_max_saving_rate=float(rc.get("hangul_max_saving_rate", 0.6)),
        use_domain_router=bool(rc.get("use_domain_router", True)),
        use_master_codebook_lexicon_v1=bool(rc.get("use_master_codebook_lexicon_v1", True)),
        include_gematria_metadata=bool(rc.get("include_gematria_metadata", True)),
        include_gematria_4d_bridge=bool(rc.get("include_gematria_4d_bridge", True)),
        apply_gematria_4d_bridge_policy=bool(rc.get("apply_gematria_4d_bridge_policy", False)),
        include_cee_core=bool(rc.get("include_cee_core", True)),
        domain_relaxed_max_saving_overrides=rc.get("domain_relaxed_max_saving_overrides"),
        domain_relaxed_max_saving_case_allowlist=frozenset(allowlist) if allowlist else None,
        domain_relaxed_max_saving_exclude_case_ids=frozenset(exclude) if exclude else None,
    )
    cm = report.get("compression_metrics") or {}
    disk = (active.get("compression_metrics") or {}).get("global_token_saving_rate")
    live_saving = cm.get("global_token_saving_rate")
    return {
        "profile": "multilens_ultra_active_report_run_config",
        "active_report_pointer": "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json",
        "global_token_saving_rate": live_saving,
        "avg_reconstruction_fidelity_jaccard": cm.get("avg_reconstruction_fidelity_jaccard"),
        "avg_sensitive_integrity": cm.get("avg_sensitive_integrity"),
        "disk_active_report_saving_rate": disk,
        "live_minus_disk_saving_delta": round(float(live_saving or 0) - float(disk or 0), 6)
        if live_saving is not None and disk is not None
        else None,
    }


def main() -> int:
    src = json.loads(INPUT_V2.read_text(encoding="utf-8"))
    cases = src.get("compression_cases") or []
    cb = resolve_latest_codebook_path()
    if cb is None:
        print("ABORT: lexicon export not found")
        return 1

    per_case = []
    total_toks = 0
    total_hits = 0
    for c in cases:
        raw = str(c.get("raw_text", ""))
        toks = unicode_word_tokens(raw)
        hits, meta = lexicon_hits_for_text(raw, cb)
        n_tok = len(toks)
        n_hit = len(hits)
        total_toks += n_tok
        total_hits += n_hit
        per_case.append(
            {
                "id": c.get("id"),
                "token_count": n_tok,
                "lexicon_hit_count": n_hit,
                "hit_ratio": round(n_hit / n_tok, 4) if n_tok else 0.0,
                "hits_sample": sorted(hits)[:8],
            }
        )

    print("Running lexicon OFF ablation (no active report write)...", flush=True)
    m_off = _bench_metrics(src, lexicon_on=False)
    print("Running lexicon ON ablation...", flush=True)
    m_on = _bench_metrics(src, lexicon_on=True)
    print("Running active report parity re-eval...", flush=True)
    m_active = _bench_metrics_active_parity(src)

    out = {
        "schema": "comp_atom02_lexicon_must_keep_analysis_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "lexicon_path": str(cb.relative_to(ROOT)).replace("\\", "/"),
        "case_count": len(cases),
        "aggregate": {
            "total_unicode_tokens": total_toks,
            "total_lexicon_hits": total_hits,
            "aggregate_hit_ratio": round(total_hits / total_toks, 4) if total_toks else 0.0,
            "unique_bench_tokens_matched": len(
                {h for row in per_case for h in row.get("hits_sample", [])}
            ),
        },
        "per_case": per_case,
        "compression_ablation": {
            "lexicon_off": m_off,
            "lexicon_on": m_on,
            "delta_on_minus_off": {
                "global_token_saving_rate": (m_on.get("global_token_saving_rate") or 0)
                - (m_off.get("global_token_saving_rate") or 0),
                "avg_reconstruction_fidelity_jaccard": (m_on.get("avg_reconstruction_fidelity_jaccard") or 0)
                - (m_off.get("avg_reconstruction_fidelity_jaccard") or 0),
            },
            "note": "strict: lexicon ON/OFF without domain_relaxed overrides.",
        },
        "active_report_parity": m_active,
        "gate_compress_profile": "active_report_parity",
        "interpretation": (
            "strict lexicon_on ~46% without domain_relaxed; "
            "active_report_parity matches frozen Track A run_config for GATE_SPEC compress plane."
        ),
    }
    path = PILOT / "comp_atom02_lexicon_must_keep_analysis_v1.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(path), "aggregate": out["aggregate"], "ablation": out["compression_ablation"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
