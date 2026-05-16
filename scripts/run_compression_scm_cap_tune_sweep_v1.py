#!/usr/bin/env python3
"""RQ-016: scm-focused bridge/cap tuning without promoting broken global profiles."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.report_multilens_performance_eval import evaluate_report

INPUT_V2 = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
BASELINE_V2 = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_PERFORMANCE_EVAL_REPORT_V2.json"
DECISION = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_ULTRA_COMPRESSION_DECISION_V1.json"
RUNNER = ROOT / "scripts" / "run_ultra_compression_default.py"
KPI_SCRIPT = ROOT / "scripts" / "report_ultra_compression_kpi_summary.py"
OUT_DEFAULT = ROOT / "docs" / "final" / "artifacts" / "compression_scm_cap_tune_sweep_v1_latest.json"
POLICY_FLOOR = 0.47
SCM_IDS = frozenset({"cmp2_015", "cmp2_023", "cmp2_028"})


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _metrics(report: dict[str, Any], case_ids: frozenset[str]) -> dict[str, Any]:
    cm = report.get("compression_metrics") or {}
    saving = float(cm.get("global_token_saving_rate") or 0)
    cases = cm.get("cases") or []
    rows = [c for c in cases if str(c.get("id", "")) in case_ids]
    scm_min = min(float(r.get("reconstruction_fidelity_jaccard") or 0) for r in rows) if rows else None
    return {
        "global_token_saving_rate": saving,
        "ultra_saving_policy_ok": saving >= POLICY_FLOOR,
        "avg_jaccard": float(cm.get("avg_reconstruction_fidelity_jaccard") or 0),
        "scm_min_jaccard": scm_min,
        "scm_by_id": {
            str(r.get("id")): float(r.get("reconstruction_fidelity_jaccard") or 0) for r in rows
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    src = _load(INPUT_V2)
    base = _load(BASELINE_V2)
    dec = _load(DECISION)
    sel = dec.get("selected_candidate") or {}
    strategy = str(sel.get("strategy", "B"))
    intensity = str(sel.get("intensity", "extreme"))
    baseline_j = float(base.get("compression_metrics", {}).get("avg_reconstruction_fidelity_jaccard", 0))
    threshold_pp = float(dec.get("target", {}).get("jaccard_drop_threshold_pp", 2.0))

    def _gms(x: Any) -> float | None:
        return float(x) if x is not None else None

    common = dict(
        source_input="docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json",
        mode="experimental",
        strategy=strategy,
        intensity=intensity,
        must_keep={"사상의학", "체질", "sasang", "myeongri", "bible"},
        jaccard_drop_threshold_pp=threshold_pp,
        baseline_avg_jaccard=baseline_j,
        general_max_saving_rate=_gms(sel.get("general_max_saving_rate")),
        sensitive_max_saving_rate=_gms(sel.get("sensitive_max_saving_rate")),
        hangul_max_saving_rate=_gms(sel.get("hangul_max_saving_rate")),
        use_domain_router=True,
        use_master_codebook_lexicon_v1=True,
        include_gematria_metadata=True,
        include_gematria_4d_bridge=True,
        include_cee_core=True,
    )

    variants: list[tuple[str, dict[str, Any]]] = [
        ("baseline", {"apply_gematria_4d_bridge_policy": False, "bridge_policy_domain_allowlist": None}),
        (
            "scm_allowlist_only",
            {
                "apply_gematria_4d_bridge_policy": False,
                "bridge_policy_domain_allowlist": frozenset({"scm"}),
            },
        ),
        (
            "scm_bridge_default",
            {
                "apply_gematria_4d_bridge_policy": True,
                "bridge_policy_domain_allowlist": frozenset({"scm"}),
                "bridge_score_weights": None,
            },
        ),
        (
            "scm_bridge_saving_heavy",
            {
                "apply_gematria_4d_bridge_policy": True,
                "bridge_policy_domain_allowlist": frozenset({"scm"}),
                "bridge_score_weights": {
                    "fidelity": 1.0,
                    "guard": 0.4,
                    "saving": 0.65,
                    "distance_penalty": 1.5,
                },
            },
        ),
        (
            "scm_bridge_balanced",
            {
                "apply_gematria_4d_bridge_policy": True,
                "bridge_policy_domain_allowlist": frozenset({"scm"}),
                "bridge_score_weights": {
                    "fidelity": 1.25,
                    "guard": 0.45,
                    "saving": 0.35,
                    "distance_penalty": 2.5,
                },
            },
        ),
    ]

    results: list[dict[str, Any]] = []
    for vid, kw in variants:
        rep = evaluate_report(src, **common, **kw)
        results.append({"id": vid, **_metrics(rep, SCM_IDS)})

    passing = [
        r
        for r in results
        if r.get("ultra_saving_policy_ok")
        and (r.get("scm_min_jaccard") or 0) > (results[0].get("scm_min_jaccard") or 0)
    ]
    recommendation = passing[0]["id"] if passing else "keep_baseline"

    doc = {
        "schema": "compression_scm_cap_tune_sweep_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "hypothesis_tier": "B",
        "track_wall": "b_track_research_only",
        "rq": "RQ-016",
        "policy_floor": POLICY_FLOOR,
        "profile": {"strategy": strategy, "intensity": intensity},
        "variants": results,
        "recommendation": recommendation,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")

    subprocess.run([sys.executable, str(RUNNER), "--mode", "universal"], cwd=str(ROOT), check=False)
    subprocess.run([sys.executable, str(KPI_SCRIPT)], cwd=str(ROOT), check=False)

    print(json.dumps({"out": str(args.out), "recommendation": recommendation, "passing": len(passing)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
