#!/usr/bin/env python3
"""Re-eval Golden-40 ACTIVE profile with production 41687 lexicon — candidate only (FAIL-COMP-004)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.report_multilens_performance_eval import evaluate_report  # noqa: E402
from scripts.run_ultra_compression_default import (  # noqa: E402
    BASELINE_V2,
    DECISION,
    INPUT_V2,
)
from scripts.ultra_compression_track_a_policy_floor_v1 import (  # noqa: E402
    apply_promoted_policy_floor_to_quality_gate,
)

ACTIVE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
DEFAULT_CANDIDATE = (
    ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_HANGUL_CURATED_CANDIDATE_V1.json"
)
PROD_LEXICON = ROOT / "reports/constitution/btrack_pilot/master_codebook_lexicon_v1_41687_rows_latest.json"
LEXICON_SIGNOFF = ROOT / "docs/final/artifacts/hangul_curated_track_a_lexicon_promotion_signoff_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    return str(p.relative_to(ROOT)).replace("\\", "/")


def _run_config_from_active(active: dict[str, Any]) -> dict[str, Any]:
    cfg = active.get("run_config")
    return cfg if isinstance(cfg, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--active-report", type=Path, default=ACTIVE)
    ap.add_argument("--lexicon-path", type=Path, default=PROD_LEXICON)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_CANDIDATE)
    ap.add_argument("--require-lexicon-signoff", action="store_true", default=True)
    ap.add_argument("--no-require-lexicon-signoff", action="store_false", dest="require_lexicon_signoff")
    args = ap.parse_args()

    active_path = args.active_report.resolve()
    lex_path = args.lexicon_path.resolve()
    if not active_path.is_file():
        print(f"ABORT: missing frozen ACTIVE: {active_path}", file=sys.stderr)
        return 1
    if not lex_path.is_file():
        print(f"ABORT: missing production lexicon: {lex_path}", file=sys.stderr)
        return 1

    if args.require_lexicon_signoff:
        if not LEXICON_SIGNOFF.is_file():
            print("ABORT: lexicon promotion signoff missing", file=sys.stderr)
            return 1
        sig = json.loads(LEXICON_SIGNOFF.read_text(encoding="utf-8"))
        if not sig.get("approved"):
            print("ABORT: lexicon signoff not approved", file=sys.stderr)
            return 1

    frozen = json.loads(active_path.read_text(encoding="utf-8"))
    rcfg = _run_config_from_active(frozen)
    src_doc = json.loads(INPUT_V2.read_text(encoding="utf-8"))
    baseline_doc = json.loads(BASELINE_V2.read_text(encoding="utf-8"))
    decision_doc = json.loads(DECISION.read_text(encoding="utf-8"))
    baseline_avg_jaccard = float(
        baseline_doc.get("compression_metrics", {}).get("avg_reconstruction_fidelity_jaccard", 0.0)
    )
    threshold_pp = float(decision_doc.get("target", {}).get("jaccard_drop_threshold_pp", 2.0))

    strategy = str(rcfg.get("strategy", "A"))
    intensity = str(rcfg.get("intensity", "extreme"))
    general_max = rcfg.get("general_max_saving_rate")
    sensitive_max = rcfg.get("sensitive_max_saving_rate")
    hangul_max = rcfg.get("hangul_max_saving_rate")
    if general_max is not None:
        general_max = float(general_max)
    if sensitive_max is not None:
        sensitive_max = float(sensitive_max)
    if hangul_max is not None:
        hangul_max = float(hangul_max)

    overrides = rcfg.get("domain_relaxed_max_saving_overrides") or {}
    domain_relaxed = (
        {str(k): float(v) for k, v in overrides.items()} if isinstance(overrides, dict) else {}
    )
    allow_list = rcfg.get("domain_relaxed_max_saving_case_allowlist")
    relaxed_allow = frozenset(str(x) for x in allow_list) if isinstance(allow_list, list) and allow_list else None
    exclude_list = rcfg.get("domain_relaxed_max_saving_exclude_case_ids")
    relaxed_exclude = (
        frozenset(str(x) for x in exclude_list) if isinstance(exclude_list, list) and exclude_list else None
    )

    report = evaluate_report(
        src_doc,
        source_input="docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json",
        mode=str(rcfg.get("mode", "experimental")),
        strategy=strategy,
        intensity=intensity,
        must_keep={"사상의학", "체질", "sasang", "myeongri", "bible"},
        jaccard_drop_threshold_pp=threshold_pp,
        baseline_avg_jaccard=baseline_avg_jaccard,
        general_max_saving_rate=general_max,
        sensitive_max_saving_rate=sensitive_max,
        hangul_max_saving_rate=hangul_max,
        use_domain_router=bool(rcfg.get("use_domain_router", True)),
        use_master_codebook_lexicon_v1=True,
        master_codebook_lexicon_path=str(lex_path),
        include_gematria_metadata=bool(rcfg.get("include_gematria_metadata", True)),
        include_gematria_4d_bridge=bool(rcfg.get("include_gematria_4d_bridge", True)),
        apply_gematria_4d_bridge_policy=bool(rcfg.get("apply_gematria_4d_bridge_policy", False)),
        domain_relaxed_max_saving_overrides=domain_relaxed or None,
        domain_relaxed_max_saving_case_allowlist=relaxed_allow,
        domain_relaxed_max_saving_exclude_case_ids=relaxed_exclude,
        include_cee_core=bool(rcfg.get("include_cee_core", True)),
    )
    apply_promoted_policy_floor_to_quality_gate(report)

    report["active_profile"] = {
        "sla_track": "universal",
        "hangul_curated_candidate": True,
        "frozen_active_source": _rel(active_path),
        "production_lexicon_path": _rel(lex_path),
        "lexicon_signoff": _rel(LEXICON_SIGNOFF) if LEXICON_SIGNOFF.is_file() else None,
        "rebuilt_at_utc": _utc(),
        "run_config_source": "frozen_active_run_config",
        "fail_comp_004": "Candidate only until hangul_curated_active_promotion_signoff apply.",
    }
    report["hangul_curated_lineage"] = {
        "schema": "hangul_curated_active_report_candidate_lineage_v1",
        "curated_lemma_manifest": "docs/final/artifacts/hangul_lexicon_curated_lemma_manifest_v1.json",
        "lexicon_row_count": 41687,
        "note": "29 curated ko lemmas; not 392 harvest overlay.",
    }

    out_path = args.out_json.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    m = report.get("compression_metrics") or {}
    print(
        json.dumps(
            {
                "wrote": _rel(out_path),
                "global_token_saving_rate": m.get("global_token_saving_rate"),
                "avg_reconstruction_fidelity_jaccard": m.get("avg_reconstruction_fidelity_jaccard"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
