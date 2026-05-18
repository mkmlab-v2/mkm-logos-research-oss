#!/usr/bin/env python3
"""Regenerate B-track health selective-bridge pinpoint report (RQ-016).

Writes **only** to ``docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_HEALTH_BRIDGE_PINPOINT_V1.json``.
Never touches ``MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json`` (Track A SSOT).
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

# Hard-coded isolation: Track A active report must not be a write target.
OUT_PINPOINT = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_ULTRA_COMPRESSION_HEALTH_BRIDGE_PINPOINT_V1.json"
FORBIDDEN_WRITE_TARGETS = frozenset(
    {
        OUT_PINPOINT.resolve(),
        (ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json").resolve(),
        (ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_LITERAL_V1.json").resolve(),
        (ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_ULTRA_LITERAL_V1.json").resolve(),
    }
)

INPUT_V2 = ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
BASELINE_V2 = ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_REPORT_V2.json"
DECISION = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_DECISION_V1.json"
TRACK_A_ACTIVE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
HEALTH_CASE_ID = "cmp2_014"

# Phase-2 sweep winner (health allowlist + saving_heavy weights).
PIN_CONFIG = {
    "bridge_policy_domain_allowlist": ["health"],
    "apply_gematria_4d_bridge_policy": True,
    "bridge_score_weights": {
        "fidelity": 1.0,
        "guard": 0.4,
        "saving": 0.65,
        "distance_penalty": 1.5,
    },
}


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _assert_safe_out(path: Path) -> Path:
    resolved = path.resolve()
    active = (ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json").resolve()
    if resolved == active:
        raise SystemExit(
            "Refusing to write Track A active report. "
            f"Use default out only: {OUT_PINPOINT.relative_to(ROOT)}"
        )
    if resolved in FORBIDDEN_WRITE_TARGETS and resolved != OUT_PINPOINT.resolve():
        raise SystemExit(f"Refusing forbidden write target: {path}")
    return resolved


def _health_case_row(report: dict[str, Any]) -> dict[str, Any] | None:
    cases = (report.get("compression_metrics") or {}).get("cases") or []
    for c in cases:
        if str(c.get("id", "")) == HEALTH_CASE_ID:
            return {
                "id": HEALTH_CASE_ID,
                "jaccard": c.get("reconstruction_fidelity_jaccard"),
                "token_saving_rate": c.get("token_saving_rate"),
                "gematria_4d_bridge_policy_applied": c.get("gematria_4d_bridge_policy_applied"),
            }
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--out-json",
        type=Path,
        default=OUT_PINPOINT,
        help=f"Output path (default hard-pinned B-track artifact). Track A path rejected.",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Print config and paths only; do not evaluate or write.",
    )
    args = ap.parse_args()

    out_path = _assert_safe_out(args.out_json)
    if out_path != OUT_PINPOINT.resolve():
        print(
            json.dumps(
                {
                    "warning": "custom_out_not_default_pinpoint",
                    "expected": str(OUT_PINPOINT.relative_to(ROOT)),
                    "got": str(out_path.relative_to(ROOT)),
                },
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )

    if args.dry_run:
        print(
            json.dumps(
                {
                    "dry_run": True,
                    "out_json": str(out_path.relative_to(ROOT)).replace("\\", "/"),
                    "track_a_active_read_only": str(TRACK_A_ACTIVE.relative_to(ROOT)).replace("\\", "/"),
                    "pin_config": PIN_CONFIG,
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

    def _gms(x: Any) -> float | None:
        return float(x) if x is not None else None

    report = evaluate_report(
        src,
        source_input="docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json",
        mode="experimental",
        strategy=str(sel.get("strategy", "A")),
        intensity=str(sel.get("intensity", "extreme")),
        must_keep={"사상의학", "체질", "sasang", "myeongri", "bible"},
        jaccard_drop_threshold_pp=float(dec.get("target", {}).get("jaccard_drop_threshold_pp", 2.0)),
        baseline_avg_jaccard=baseline_j,
        general_max_saving_rate=_gms(sel.get("general_max_saving_rate")),
        sensitive_max_saving_rate=_gms(sel.get("sensitive_max_saving_rate")),
        hangul_max_saving_rate=_gms(sel.get("hangul_max_saving_rate")),
        use_domain_router=True,
        use_master_codebook_lexicon_v1=True,
        include_gematria_metadata=True,
        include_gematria_4d_bridge=True,
        include_cee_core=True,
        apply_gematria_4d_bridge_policy=bool(PIN_CONFIG["apply_gematria_4d_bridge_policy"]),
        bridge_policy_domain_allowlist=frozenset(PIN_CONFIG["bridge_policy_domain_allowlist"]),
        bridge_score_weights=dict(PIN_CONFIG["bridge_score_weights"]),
    )

    cm = report.get("compression_metrics") or {}
    saving = float(cm.get("global_token_saving_rate") or 0)
    avg_j = float(cm.get("avg_reconstruction_fidelity_jaccard") or 0)

    track_a_ref: dict[str, Any] | None = None
    if TRACK_A_ACTIVE.is_file():
        ta = _load(TRACK_A_ACTIVE)
        tacm = ta.get("compression_metrics") or {}
        track_a_ref = {
            "path": str(TRACK_A_ACTIVE.relative_to(ROOT)).replace("\\", "/"),
            "global_token_saving_rate": tacm.get("global_token_saving_rate"),
            "avg_reconstruction_fidelity_jaccard": tacm.get("avg_reconstruction_fidelity_jaccard"),
            "apply_gematria_4d_bridge_policy": (ta.get("run_config") or {}).get(
                "apply_gematria_4d_bridge_policy"
            ),
        }

    envelope = {
        "schema": "multilens_ultra_compression_health_bridge_pinpoint_envelope_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "track_wall": "b_track_research_only",
        "rq": "RQ-016",
        "policy_floor": 0.47,
        "pin_config": PIN_CONFIG,
        "pinpoint_metrics": {
            "global_token_saving_rate": saving,
            "ultra_saving_policy_ok": saving >= 0.47,
            "avg_reconstruction_fidelity_jaccard": avg_j,
            "health_case": _health_case_row(report),
        },
        "track_a_reference_readonly": track_a_ref,
        "promotion_note": (
            "Does not replace MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json. "
            "Track A remains bridge_policy OFF."
        ),
        "evidence_refs": [
            "docs/final/artifacts/compression_domain_bridge_sweep_v1_latest.json",
            "docs/final/artifacts/compression_scm_bridge_weight_grid_v2_latest.json",
        ],
    }
    report["b_track_envelope"] = envelope
    report["active_profile"] = {
        "sla_track": "b_track_health_bridge_pinpoint",
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
                "avg_jaccard": avg_j,
                "health_case": envelope["pinpoint_metrics"].get("health_case"),
                "track_a_touched": False,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
