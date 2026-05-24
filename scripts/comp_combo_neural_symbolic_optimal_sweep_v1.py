#!/usr/bin/env python3
"""B-track: neural-symbolic combo sweep — bridge × lexicon × selective domains × mode.

Never writes Track A active. SSOT: MISSION_LOG COMP-ATOM + worldview geumhwa/4D moat.
Writes: reports/constitution/btrack_pilot/comp_combo_optimal_sweep_v1.json
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.report_multilens_performance_eval import evaluate_report  # noqa: E402

PILOT = ROOT / "reports" / "constitution" / "btrack_pilot"
INPUT_V2 = ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
BASELINE_V2 = ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_REPORT_V2.json"
DECISION = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_DECISION_V1.json"
OUT = PILOT / "comp_combo_optimal_sweep_v1.json"
POLICY_FLOOR = 0.47
TOP5 = frozenset({"cmp2_002", "cmp2_004", "cmp2_005", "cmp2_006", "cmp2_009"})

FORBIDDEN = frozenset(
    {
        (ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json").resolve(),
    }
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _base_kwargs() -> dict[str, Any]:
    baseline = json.loads(BASELINE_V2.read_text(encoding="utf-8"))
    decision = json.loads(DECISION.read_text(encoding="utf-8"))
    selected = decision.get("selected_candidate") or {}
    baseline_j = float(
        baseline.get("compression_metrics", {}).get("avg_reconstruction_fidelity_jaccard", 0.0)
    )
    threshold_pp = float(decision.get("target", {}).get("jaccard_drop_threshold_pp", 2.0))
    return {
        "source_input": str(INPUT_V2.relative_to(ROOT)).replace("\\", "/"),
        "mode": "experimental",
        "strategy": str(selected.get("strategy", "A")),
        "intensity": str(selected.get("intensity", "extreme")),
        "must_keep": {"사상의학", "체질", "sasang", "myeongri", "bible"},
        "jaccard_drop_threshold_pp": threshold_pp,
        "baseline_avg_jaccard": baseline_j,
        "general_max_saving_rate": float(selected.get("general_max_saving_rate", 0.35)),
        "sensitive_max_saving_rate": float(selected.get("sensitive_max_saving_rate", 0.3)),
        "hangul_max_saving_rate": float(selected.get("hangul_max_saving_rate", 0.6)),
        "use_domain_router": True,
        "include_gematria_metadata": True,
        "include_gematria_4d_bridge": True,
        "include_cee_core": True,
    }


def _metrics(report: dict[str, Any]) -> dict[str, Any]:
    cm = report.get("compression_metrics") or {}
    qg = report.get("quality_gate") or {}
    prof = report.get("run_config") or {}
    saving = float(cm.get("global_token_saving_rate", 0.0))
    jaccard = float(cm.get("avg_reconstruction_fidelity_jaccard", 0.0))
    min_j = float(cm.get("min_reconstruction_fidelity_jaccard", 0.0))
    return {
        "global_token_saving_rate": saving,
        "avg_reconstruction_fidelity_jaccard": jaccard,
        "min_reconstruction_fidelity_jaccard": min_j,
        "avg_sensitive_integrity": float(cm.get("avg_sensitive_integrity", 0.0)),
        "sensitive_integrity_ok": bool(qg.get("sensitive_integrity_ok")),
        "ultra_saving_policy_ok": bool(qg.get("ultra_saving_policy_ok")),
        "apply_gematria_4d_bridge_policy": bool(prof.get("apply_gematria_4d_bridge_policy")),
        "use_master_codebook_lexicon_v1": bool(prof.get("use_master_codebook_lexicon_v1")),
        "bridge_policy_domain_allowlist": prof.get("bridge_policy_domain_allowlist"),
        "moat_score": round(0.55 * jaccard + 0.45 * saving, 6),
        "pareto_tier": (
            "economy"
            if saving >= POLICY_FLOOR and not prof.get("apply_gematria_4d_bridge_policy")
            else "fidelity"
            if prof.get("apply_gematria_4d_bridge_policy") and jaccard >= 0.94
            else "balanced"
        ),
    }


def _eval_combo(
    src: dict[str, Any],
    combo_id: str,
    *,
    lexicon: bool,
    bridge: bool,
    allowlist: frozenset[str] | None = None,
    relaxed_ssot: float | None = 0.45,
    strategy: str | None = None,
    intensity: str | None = None,
    general_cap: float | None = None,
    sensitive_cap: float | None = None,
    hangul_cap: float | None = None,
) -> dict[str, Any]:
    kw = _base_kwargs()
    if strategy:
        kw["strategy"] = strategy
    if intensity:
        kw["intensity"] = intensity
    if general_cap is not None:
        kw["general_max_saving_rate"] = general_cap
    if sensitive_cap is not None:
        kw["sensitive_max_saving_rate"] = sensitive_cap
    if hangul_cap is not None:
        kw["hangul_max_saving_rate"] = hangul_cap
    domain_relaxed = None
    case_allow = None
    if relaxed_ssot is not None:
        domain_relaxed = {"ssot": relaxed_ssot}
        case_allow = TOP5
    report = evaluate_report(
        src,
        use_master_codebook_lexicon_v1=lexicon,
        apply_gematria_4d_bridge_policy=bridge,
        bridge_policy_domain_allowlist=allowlist,
        domain_relaxed_max_saving_overrides=domain_relaxed,
        domain_relaxed_max_saving_case_allowlist=case_allow,
        **kw,
    )
    m = _metrics(report)
    return {"combo_id": combo_id, "metrics": m, "run_config_snapshot": report.get("run_config")}


def _rank(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_saving = sorted(rows, key=lambda r: r["metrics"]["global_token_saving_rate"], reverse=True)
    by_jaccard = sorted(
        rows, key=lambda r: r["metrics"]["avg_reconstruction_fidelity_jaccard"], reverse=True
    )
    by_moat = sorted(rows, key=lambda r: r["metrics"]["moat_score"], reverse=True)
    floor_ok = [r for r in rows if r["metrics"]["ultra_saving_policy_ok"]]
    best_economy = floor_ok[0] if floor_ok else None
    best_fidelity = by_jaccard[0] if by_jaccard else None
    best_moat = by_moat[0] if by_moat else None
    return {
        "best_economy_floor_pass": best_economy["combo_id"] if best_economy else None,
        "best_fidelity_jaccard": best_fidelity["combo_id"] if best_fidelity else None,
        "best_moat_score_heuristic": best_moat["combo_id"] if best_moat else None,
        "top3_saving": [r["combo_id"] for r in by_saving[:3]],
        "top3_jaccard": [r["combo_id"] for r in by_jaccard[:3]],
    }


def main() -> int:
    PILOT.mkdir(parents=True, exist_ok=True)
    src = json.loads(INPUT_V2.read_text(encoding="utf-8"))
    combos: list[dict[str, Any]] = []

    combos.append(
        _eval_combo(
            src,
            "track_a_replay",
            lexicon=True,
            bridge=False,
            relaxed_ssot=0.45,
        )
    )
    combos.append(
        _eval_combo(src, "economy_no_lexicon", lexicon=False, bridge=False, relaxed_ssot=0.45)
    )
    combos.append(
        _eval_combo(src, "fidelity_bridge_full", lexicon=True, bridge=True, relaxed_ssot=0.45)
    )
    combos.append(
        _eval_combo(
            src, "fidelity_bridge_no_lexicon", lexicon=False, bridge=True, relaxed_ssot=0.45
        )
    )
    combos.append(
        _eval_combo(
            src,
            "selective_bridge_health_scm",
            lexicon=True,
            bridge=True,
            allowlist=frozenset({"health", "scm"}),
            relaxed_ssot=0.45,
        )
    )
    combos.append(
        _eval_combo(
            src,
            "selective_bridge_ssot",
            lexicon=True,
            bridge=True,
            allowlist=frozenset({"ssot"}),
            relaxed_ssot=0.45,
        )
    )
    combos.append(
        _eval_combo(
            src,
            "economy_ssot_cap_048",
            lexicon=True,
            bridge=False,
            relaxed_ssot=0.48,
        )
    )
    combos.append(
        _eval_combo(
            src,
            "literal_profile",
            lexicon=True,
            bridge=False,
            relaxed_ssot=None,
            strategy="C",
            intensity="high",
            general_cap=0.28,
            sensitive_cap=0.26,
            hangul_cap=0.30,
        )
    )

    ranking = _rank(combos)
    doc = {
        "schema": "comp_combo_optimal_sweep_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "track_wall": "b_track_research_only",
        "active_report_untouched": True,
        "worldview_ssot": "docs/final/MKM_WORLDVIEW_AND_PHILOSOPHY_CONSTITUTION_V1.md",
        "mission_log_anchor": "MISSION_LOG.md §최종 목표 — 압축·4D",
        "policy_floor": POLICY_FLOOR,
        "combo_count": len(combos),
        "combos": combos,
        "ranking": ranking,
        "interpretation": {
            "track_a_frozen": "track_a_replay should match comp_atom01 control (~47.5% / 0.890).",
            "geumhwa_moat": "fidelity_bridge_* raises Jaccard at saving cost; not MS-paste headline.",
            "no_better_than_both": (
                "If no combo beats economy saving AND fidelity jaccard jointly, "
                "keep API 3-tier (economy|fidelity|literal) — do not promote single knob to Track A."
            ),
        },
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "wrote": str(OUT.relative_to(ROOT)),
                "ranking": ranking,
                "track_a_replay": next(
                    (c["metrics"] for c in combos if c["combo_id"] == "track_a_replay"), {}
                ),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
