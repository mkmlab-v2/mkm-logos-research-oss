#!/usr/bin/env python3
"""Regenerate B-track ssot relaxed-cap pinpoint report (RQ-016 A-plan).

Writes **only** to ``docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_SSOT_RELAXED_CAP_PINPOINT_V1.json``.
Never touches ``MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json`` (Track A SSOT).

Pin: ``domain_relaxed_max_saving_overrides: {ssot: 0.45}`` — no lexicon edits, bridge OFF.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.report_multilens_performance_eval import evaluate_report

OUT_PINPOINT = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_SSOT_RELAXED_CAP_PINPOINT_V1.json"
INPUT_V2 = ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
BASELINE_V2 = ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_REPORT_V2.json"
DECISION = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_DECISION_V1.json"
TRACK_A_ACTIVE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
POLICY_FLOOR = 0.47
SSOT_DOMAIN = "ssot"
TOP5_LOW_SAVING_IDS = frozenset({"cmp2_006", "cmp2_004", "cmp2_002", "cmp2_005", "cmp2_009"})

PIN_CONFIG = {
    "domain_relaxed_max_saving_overrides": {SSOT_DOMAIN: 0.45},
    "apply_gematria_4d_bridge_policy": False,
    "bridge_policy_domain_allowlist": None,
}

FORBIDDEN_WRITE = frozenset(
    {
        (ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json").resolve(),
        (ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_LITERAL_V1.json").resolve(),
        (ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_ULTRA_LITERAL_V1.json").resolve(),
    }
)


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _assert_safe_out(path: Path) -> Path:
    resolved = path.resolve()
    if resolved in FORBIDDEN_WRITE:
        raise SystemExit(
            "Refusing to write Track A active report. "
            f"Use default out only: {OUT_PINPOINT.relative_to(ROOT)}"
        )
    return resolved


def _case_map(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    cases = (report.get("compression_metrics") or {}).get("cases") or []
    return {str(c.get("id", "")): c for c in cases}


def _by_id_diff(pin: dict[str, dict[str, Any]], ref: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for cid in sorted(set(pin) | set(ref)):
        p = pin.get(cid) or {}
        r = ref.get(cid) or {}
        ps = p.get("token_saving_rate")
        rs = r.get("token_saving_rate")
        pj = p.get("reconstruction_fidelity_jaccard")
        rj = r.get("reconstruction_fidelity_jaccard")
        route_p = p.get("route") or {}
        route_r = r.get("route") or {}
        rows.append(
            {
                "id": cid,
                "domain": route_p.get("domain") or route_r.get("domain"),
                "shard_id": route_p.get("shard_id") or route_r.get("shard_id"),
                "token_saving_rate_ref": rs,
                "token_saving_rate_pin": ps,
                "delta_saving": (
                    round(float(ps) - float(rs), 6)
                    if ps is not None and rs is not None
                    else None
                ),
                "jaccard_ref": rj,
                "jaccard_pin": pj,
                "delta_jaccard": (
                    round(float(pj) - float(rj), 6) if pj is not None and rj is not None else None
                ),
            }
        )
    return rows


def _subset_agg(rows: list[dict[str, Any]], case_ids: frozenset[str]) -> dict[str, Any]:
    sub = [r for r in rows if r["id"] in case_ids]
    if not sub:
        return {"case_count": 0}
    n = len(sub)
    return {
        "case_count": n,
        "avg_delta_saving": sum(float(r["delta_saving"] or 0) for r in sub) / n,
        "avg_delta_jaccard": sum(float(r["delta_jaccard"] or 0) for r in sub) / n,
        "min_delta_jaccard": min(float(r["delta_jaccard"] or 0) for r in sub),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=OUT_PINPOINT)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    out_path = _assert_safe_out(args.out_json)

    if args.dry_run:
        print(
            json.dumps(
                {
                    "dry_run": True,
                    "out_json": str(out_path.relative_to(ROOT)).replace("\\", "/"),
                    "pin_config": PIN_CONFIG,
                    "track_a_readonly": str(TRACK_A_ACTIVE.relative_to(ROOT)).replace("\\", "/"),
                },
                ensure_ascii=False,
            )
        )
        return 0

    src = _load(INPUT_V2)
    base = _load(BASELINE_V2)
    dec = _load(DECISION)
    sel = dec.get("selected_candidate") or {}
    baseline_j = float(base.get("compression_metrics", {}).get("avg_reconstruction_fidelity_jaccard", 0))
    threshold_pp = float(dec.get("target", {}).get("jaccard_drop_threshold_pp", 2.0))

    def _gms(x: Any) -> float | None:
        return float(x) if x is not None else None

    report = evaluate_report(
        src,
        source_input="docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json",
        mode="experimental",
        strategy=str(sel.get("strategy", "A")),
        intensity=str(sel.get("intensity", "extreme")),
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
        apply_gematria_4d_bridge_policy=False,
        bridge_policy_domain_allowlist=None,
        domain_relaxed_max_saving_overrides=dict(PIN_CONFIG["domain_relaxed_max_saving_overrides"]),
    )

    cm = report.get("compression_metrics") or {}
    saving = float(cm.get("global_token_saving_rate") or 0)
    avg_j = float(cm.get("avg_reconstruction_fidelity_jaccard") or 0)
    min_j = float(cm.get("min_reconstruction_fidelity_jaccard") or 0)
    jaccard_drop_pp = max(0.0, (baseline_j - avg_j) * 100.0)

    track_a_ref: dict[str, Any] | None = None
    by_id_diff: list[dict[str, Any]] = []
    if TRACK_A_ACTIVE.is_file():
        ta = _load(TRACK_A_ACTIVE)
        tacm = ta.get("compression_metrics") or {}
        track_a_ref = {
            "path": str(TRACK_A_ACTIVE.relative_to(ROOT)).replace("\\", "/"),
            "global_token_saving_rate": tacm.get("global_token_saving_rate"),
            "avg_reconstruction_fidelity_jaccard": tacm.get("avg_reconstruction_fidelity_jaccard"),
            "min_reconstruction_fidelity_jaccard": tacm.get("min_reconstruction_fidelity_jaccard"),
            "apply_gematria_4d_bridge_policy": (ta.get("run_config") or {}).get(
                "apply_gematria_4d_bridge_policy"
            ),
        }
        by_id_diff = _by_id_diff(_case_map(report), _case_map(ta))

    ssot_rows = [r for r in by_id_diff if str(r.get("domain") or "") == SSOT_DOMAIN]
    degraded = [r for r in by_id_diff if (r.get("delta_jaccard") or 0) < -1e-9]
    worst_j = min(by_id_diff, key=lambda r: float(r.get("jaccard_pin") or 1)) if by_id_diff else None

    ta_min_j = float((track_a_ref or {}).get("min_reconstruction_fidelity_jaccard") or 0)
    promotion_gates = {
        "ultra_saving_policy_ok": saving >= POLICY_FLOOR,
        "jaccard_drop_pp_vs_v2_baseline": round(jaccard_drop_pp, 4),
        "jaccard_drop_within_decision_threshold": jaccard_drop_pp <= threshold_pp,
        "min_jaccard_pin": min_j,
        "min_jaccard_not_below_track_a": min_j >= ta_min_j - 1e-9 if track_a_ref else None,
        "cases_with_jaccard_regression_count": len(degraded),
        "auto_track_a_promotion_allowed": False,
        "human_review_required": True,
    }

    envelope = {
        "schema": "multilens_ultra_compression_ssot_relaxed_cap_pinpoint_envelope_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "track_wall": "b_track_research_only",
        "rq": "RQ-016-A-plan",
        "policy_floor": POLICY_FLOOR,
        "pin_config": PIN_CONFIG,
        "pinpoint_metrics": {
            "global_token_saving_rate": saving,
            "delta_global_saving_vs_track_a": (
                round(
                    saving - float(track_a_ref.get("global_token_saving_rate") or 0),
                    6,
                )
                if track_a_ref
                else None
            ),
            "ultra_saving_policy_ok": saving >= POLICY_FLOOR,
            "avg_reconstruction_fidelity_jaccard": avg_j,
            "min_reconstruction_fidelity_jaccard": min_j,
        },
        "by_id_diff_vs_track_a": by_id_diff,
        "ssot_domain_diff_summary": {
            "case_count": len(ssot_rows),
            "avg_delta_saving": (
                sum(float(r["delta_saving"] or 0) for r in ssot_rows) / len(ssot_rows)
                if ssot_rows
                else None
            ),
            "avg_delta_jaccard": (
                sum(float(r["delta_jaccard"] or 0) for r in ssot_rows) / len(ssot_rows)
                if ssot_rows
                else None
            ),
            "min_jaccard_pin_among_ssot": (
                min(float(r["jaccard_pin"] or 1) for r in ssot_rows) if ssot_rows else None
            ),
        },
        "top5_low_saving_diff_summary": _subset_agg(by_id_diff, TOP5_LOW_SAVING_IDS),
        "worst_jaccard_case": (
            {
                "id": worst_j.get("id"),
                "jaccard_pin": worst_j.get("jaccard_pin"),
                "delta_jaccard": worst_j.get("delta_jaccard"),
            }
            if worst_j
            else None
        ),
        "promotion_gates": promotion_gates,
        "track_a_reference_readonly": track_a_ref,
        "promotion_note": (
            "Does not replace MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json. "
            "ssot domain_relaxed_max_saving 0.45 only; lexicon untouched; bridge OFF."
        ),
        "evidence_refs": [
            "docs/final/artifacts/compression_low_saving_local_cap_sweep_v1_latest.json",
            "docs/final/artifacts/compression_b_track_bridge_evidence_summary_v1.json",
        ],
    }
    report["b_track_envelope"] = envelope
    report["active_profile"] = {
        "sla_track": "b_track_ssot_relaxed_cap_pinpoint",
        "pin_config": PIN_CONFIG,
        "must_not_overwrite": "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json",
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "wrote": str(out_path.relative_to(ROOT)).replace("\\", "/"),
                "global_token_saving_rate": saving,
                "ultra_saving_policy_ok": saving >= POLICY_FLOOR,
                "avg_jaccard": avg_j,
                "min_jaccard": min_j,
                "promotion_gates": promotion_gates,
                "track_a_touched": False,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
