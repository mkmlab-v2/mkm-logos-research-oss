#!/usr/bin/env python3
"""Run the selected ultra compression profile as operational default."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.core.multilens_bridge_policy_env import env_apply_gematria_4d_bridge_policy
from scripts.report_multilens_performance_eval import evaluate_report


INPUT_V2 = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
BASELINE_V2 = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_PERFORMANCE_EVAL_REPORT_V2.json"
DECISION = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_ULTRA_COMPRESSION_DECISION_V1.json"
ACTIVE_REPORT = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
ACTIVE_REPORT_LITERAL = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_LITERAL_V1.json"
ACTIVE_REPORT_ULTRA_LITERAL = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_ULTRA_LITERAL_V1.json"
PROMOTION_SIGNOFF = (
    ROOT / "docs" / "final" / "artifacts" / "multilens_ultra_compression_track_a_promotion_signoff_v1_latest.json"
)


def _promotion_signoff_run_config() -> dict[str, Any] | None:
    if not PROMOTION_SIGNOFF.is_file():
        return None
    doc = json.loads(PROMOTION_SIGNOFF.read_text(encoding="utf-8"))
    cfg = doc.get("selected_run_config")
    return cfg if isinstance(cfg, dict) else None

# Track B (literal-priority): conservative caps — see docs/final/COMPRESSION_SLA_POLICY_V1.md
LITERAL_STRATEGY = "C"
LITERAL_INTENSITY = "high"
LITERAL_GENERAL_MAX_SAVING = 0.28
LITERAL_SENSITIVE_MAX_SAVING = 0.26
LITERAL_HANGUL_MAX_SAVING = 0.30

# Track B — Ultra-Literal (research): maximize Jaccard toward 1.0; accept very low saving — same strategy C.
# Bench proxy: cmp2_001–010 = EN policy/ops (finance-adjacent); cmp2_011–040 = Korean medical/sasang lines.
ULTRA_LITERAL_STRATEGY = "C"
ULTRA_LITERAL_INTENSITY = "high"
ULTRA_LITERAL_GENERAL_MAX_SAVING = 0.06
ULTRA_LITERAL_SENSITIVE_MAX_SAVING = 0.06
ULTRA_LITERAL_HANGUL_MAX_SAVING = 0.08

_FINANCE_OPS_PROXY_IDS = frozenset(f"cmp2_{i:03d}" for i in range(1, 11))
_MEDICAL_KO_PROXY_IDS = frozenset(f"cmp2_{i:03d}" for i in range(11, 41))


def _precision_subset_metrics(cases: list[dict]) -> dict[str, object]:
    """Aggregate Jaccard/saving by bench proxy domain (MULTILENS V2 id bands)."""

    def _agg(id_set: frozenset, label: str) -> dict[str, object] | None:
        rows = [c for c in cases if str(c.get("id", "")) in id_set]
        if not rows:
            return None
        n = len(rows)
        jac = sum(float(r.get("reconstruction_fidelity_jaccard") or 0.0) for r in rows) / n
        sav = sum(float(r.get("token_saving_rate") or 0.0) for r in rows) / n
        o200k = [float(r["o200k_saving_rate"]) for r in rows if r.get("o200k_saving_rate") is not None]
        return {
            "label": label,
            "case_count": n,
            "avg_reconstruction_fidelity_jaccard": jac,
            "avg_token_saving_rate": sav,
            "avg_o200k_saving_rate": (sum(o200k) / len(o200k)) if o200k else None,
        }

    out: dict[str, object] = {
        "schema": "compression_precision_domain_subsets_v1",
        "note": "Proxy bands on MULTILENS_PERFORMANCE_EVAL_INPUT_V2: finance_ops_en=cmp2_001–010; medical_ko=cmp2_011–040.",
    }
    fo = _agg(_FINANCE_OPS_PROXY_IDS, "finance_ops_en_proxy")
    mk = _agg(_MEDICAL_KO_PROXY_IDS, "medical_ko_proxy")
    if fo:
        out["finance_ops_en_proxy"] = fo
    if mk:
        out["medical_ko_proxy"] = mk
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Run ultra compression default profile (Track A universal or Track B literal).")
    ap.add_argument(
        "--mode",
        choices=("universal", "literal", "ultra-literal"),
        default="universal",
        help=(
            "universal: decision-driven ops profile (default). "
            "literal: conservative caps for higher fidelity. "
            "ultra-literal: research profile — very low saving caps, Jaccard toward 1.0 (see COMPRESSION_SLA_POLICY_V1)."
        ),
    )
    ap.add_argument(
        "--apply-gematria-4d-bridge-policy",
        action="store_true",
        help=(
            "Pass apply_gematria_4d_bridge_policy=True into evaluate_report (requires include_gematria_4d_bridge; "
            "adds must_keep terms, may tighten caps, runs _bridge_aware_candidate_select). "
            "Default OFF to match historical active reports."
        ),
    )
    ap.add_argument(
        "--selective-bridge-policy-domains",
        default="",
        metavar="DOMAINS",
        help=(
            "Comma-separated domain ids (e.g. scm,health). When set, bridge policy runs only on those domains; "
            "overrides global --apply-gematria-4d-bridge-policy for non-listed domains (RQ-016 selective pin)."
        ),
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Optional output path for the report JSON (default: Track A/B active report paths by --mode).",
    )
    ap.add_argument(
        "--domain-relaxed-max-saving-overrides",
        default="",
        metavar="SPEC",
        help="Comma-separated domain:cap pairs (e.g. ssot:0.45). RQ-016 promotion profile.",
    )
    ap.add_argument(
        "--domain-relaxed-max-saving-case-allowlist",
        default="",
        metavar="IDS",
        help="Comma-separated case ids; relaxed caps apply only on these cases when set.",
    )
    ap.add_argument(
        "--domain-relaxed-max-saving-exclude-case-ids",
        default="",
        metavar="IDS",
        help="Comma-separated case ids never receiving domain relaxed caps.",
    )
    ap.add_argument(
        "--ignore-promotion-signoff",
        action="store_true",
        help="Do not load domain-relaxed caps from multilens_ultra_compression_track_a_promotion_signoff_v1_latest.json.",
    )
    args = ap.parse_args()
    sla_track = str(args.mode)
    apply_bridge_policy = bool(args.apply_gematria_4d_bridge_policy) or env_apply_gematria_4d_bridge_policy()
    selective_domains_raw = str(args.selective_bridge_policy_domains or "").strip()
    bridge_policy_domain_allowlist: frozenset[str] | None = None
    if selective_domains_raw:
        bridge_policy_domain_allowlist = frozenset(
            d.strip() for d in selective_domains_raw.split(",") if d.strip()
        )

    domain_relaxed: dict[str, float] = {}
    for part in str(args.domain_relaxed_max_saving_overrides or "").split(","):
        part = part.strip()
        if not part or ":" not in part:
            continue
        dom, cap = part.split(":", 1)
        domain_relaxed[dom.strip()] = float(cap.strip())
    relaxed_case_allowlist: frozenset[str] | None = None
    allow_raw = str(args.domain_relaxed_max_saving_case_allowlist or "").strip()
    if allow_raw:
        relaxed_case_allowlist = frozenset(i.strip() for i in allow_raw.split(",") if i.strip())
    relaxed_case_exclude: frozenset[str] | None = None
    exclude_raw = str(args.domain_relaxed_max_saving_exclude_case_ids or "").strip()
    if exclude_raw:
        relaxed_case_exclude = frozenset(i.strip() for i in exclude_raw.split(",") if i.strip())

    promotion_signoff_applied: dict[str, Any] | None = None
    if (
        sla_track == "universal"
        and not args.ignore_promotion_signoff
        and not domain_relaxed
        and relaxed_case_allowlist is None
        and relaxed_case_exclude is None
    ):
        signoff_doc = json.loads(PROMOTION_SIGNOFF.read_text(encoding="utf-8"))
        signoff_cfg = signoff_doc.get("selected_run_config")
        if isinstance(signoff_cfg, dict):
            overrides = signoff_cfg.get("domain_relaxed_max_saving_overrides") or {}
            if isinstance(overrides, dict):
                domain_relaxed = {str(k): float(v) for k, v in overrides.items()}
            allow_list = signoff_cfg.get("domain_relaxed_max_saving_case_allowlist")
            if isinstance(allow_list, list) and allow_list:
                relaxed_case_allowlist = frozenset(str(x) for x in allow_list)
            exclude_list = signoff_cfg.get("domain_relaxed_max_saving_exclude_case_ids")
            if isinstance(exclude_list, list) and exclude_list:
                relaxed_case_exclude = frozenset(str(x) for x in exclude_list)
            promotion_signoff_applied = {
                "path": str(PROMOTION_SIGNOFF.relative_to(ROOT)).replace("\\", "/"),
                "selected_variant_id": signoff_doc.get("selected_variant_id"),
            }

    src_doc = json.loads(INPUT_V2.read_text(encoding="utf-8"))
    baseline_doc = json.loads(BASELINE_V2.read_text(encoding="utf-8"))
    decision_doc = json.loads(DECISION.read_text(encoding="utf-8"))

    selected = decision_doc.get("selected_candidate") or {}
    if sla_track == "literal":
        strategy = LITERAL_STRATEGY
        intensity = LITERAL_INTENSITY
        general_max_saving_rate = LITERAL_GENERAL_MAX_SAVING
        sensitive_max_saving_rate = LITERAL_SENSITIVE_MAX_SAVING
        hangul_max_saving_rate = LITERAL_HANGUL_MAX_SAVING
    elif sla_track == "ultra-literal":
        strategy = ULTRA_LITERAL_STRATEGY
        intensity = ULTRA_LITERAL_INTENSITY
        general_max_saving_rate = ULTRA_LITERAL_GENERAL_MAX_SAVING
        sensitive_max_saving_rate = ULTRA_LITERAL_SENSITIVE_MAX_SAVING
        hangul_max_saving_rate = ULTRA_LITERAL_HANGUL_MAX_SAVING
    else:
        strategy = str(selected.get("strategy", "B"))
        intensity = str(selected.get("intensity", "extreme"))
        general_max_saving_rate = selected.get("general_max_saving_rate")
        sensitive_max_saving_rate = selected.get("sensitive_max_saving_rate")
        hangul_max_saving_rate = selected.get("hangul_max_saving_rate")
        if general_max_saving_rate is not None:
            general_max_saving_rate = float(general_max_saving_rate)
        if sensitive_max_saving_rate is not None:
            sensitive_max_saving_rate = float(sensitive_max_saving_rate)
        if hangul_max_saving_rate is not None:
            hangul_max_saving_rate = float(hangul_max_saving_rate)
    baseline_avg_jaccard = float(
        baseline_doc.get("compression_metrics", {}).get("avg_reconstruction_fidelity_jaccard", 0.0)
    )
    threshold_pp = float(decision_doc.get("target", {}).get("jaccard_drop_threshold_pp", 2.0))

    report = evaluate_report(
        src_doc,
        source_input="docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json",
        mode="experimental",
        strategy=strategy,
        intensity=intensity,
        must_keep={"사상의학", "체질", "sasang", "myeongri", "bible"},
        jaccard_drop_threshold_pp=threshold_pp,
        baseline_avg_jaccard=baseline_avg_jaccard,
        general_max_saving_rate=general_max_saving_rate,
        sensitive_max_saving_rate=sensitive_max_saving_rate,
        hangul_max_saving_rate=hangul_max_saving_rate,
        use_domain_router=True,
        use_master_codebook_lexicon_v1=True,
        include_gematria_metadata=True,
        include_gematria_4d_bridge=True,
        apply_gematria_4d_bridge_policy=apply_bridge_policy,
        bridge_policy_domain_allowlist=bridge_policy_domain_allowlist,
        domain_relaxed_max_saving_overrides=domain_relaxed or None,
        domain_relaxed_max_saving_case_allowlist=relaxed_case_allowlist,
        domain_relaxed_max_saving_exclude_case_ids=relaxed_case_exclude,
        include_cee_core=True,
    )
    report["active_profile"] = {
        "sla_track": sla_track,
        "from_decision": "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_DECISION_V1.json",
        "strategy": strategy,
        "intensity": intensity,
        "general_max_saving_rate": general_max_saving_rate,
        "sensitive_max_saving_rate": sensitive_max_saving_rate,
        "hangul_max_saving_rate": hangul_max_saving_rate,
        "apply_gematria_4d_bridge_policy": apply_bridge_policy,
        "apply_gematria_4d_bridge_policy_env": env_apply_gematria_4d_bridge_policy(),
        "bridge_policy_domain_allowlist": (
            sorted(bridge_policy_domain_allowlist)
            if bridge_policy_domain_allowlist is not None
            else None
        ),
        "domain_relaxed_max_saving_overrides": domain_relaxed or None,
        "domain_relaxed_max_saving_case_allowlist": (
            sorted(relaxed_case_allowlist) if relaxed_case_allowlist is not None else None
        ),
        "domain_relaxed_max_saving_exclude_case_ids": (
            sorted(relaxed_case_exclude) if relaxed_case_exclude is not None else None
        ),
        "promotion_signoff_applied": promotion_signoff_applied,
    }
    if sla_track == "ultra-literal":
        cases = (report.get("compression_metrics") or {}).get("cases") or []
        if cases:
            report["compression_metrics"]["precision_domain_subsets"] = _precision_subset_metrics(cases)
        report["active_profile"]["research_note"] = (
            "Ultra-Literal: minimize token economy to approach lossless reconstruction on the V2 bench; "
            "not a compliance seal for regulated medical/financial advice."
        )
    out_path = args.out
    if out_path is None:
        out_path = (
            ACTIVE_REPORT_ULTRA_LITERAL
            if sla_track == "ultra-literal"
            else (ACTIVE_REPORT_LITERAL if sla_track == "literal" else ACTIVE_REPORT)
        )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
