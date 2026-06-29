#!/usr/bin/env python3
"""Refresh Path B Pareto knee summary from dual-axis sweep + optional prior_41k eval."""
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

ACTIVE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
SWEEP = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_latent_eval_path_b_sweep_v1_latest.json"
)
PRIOR_41K = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_latent_eval_path_b_prior_41k_v1_latest.json"
)
PUSH_MANIFEST = ROOT / "reports/ng40_path_b_dual_axis_push_v1_latest.json"
OUT_DEFAULT = ROOT / "reports/ng40_path_b_knee_summary_v1_latest.json"
SCHEMA = "ng40_path_b_knee_summary_v1"

FROZEN_SAVING = 0.47538677918424754
FROZEN_J = 0.8904921794966301


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _knee_row(row: dict[str, Any]) -> dict[str, Any]:
    agg = row.get("aggregate") or {}
    beat = row.get("beat_check") or {}
    caps = row.get("caps") or {}
    return {
        "global_token_saving_rate": agg.get("global_token_saving_rate"),
        "avg_reconstruction_fidelity_jaccard": agg.get("avg_reconstruction_fidelity_jaccard"),
        "delta_saving_pp": beat.get("delta_saving_pp"),
        "delta_jaccard_pp": beat.get("delta_jaccard_pp"),
        "beat_frozen": beat.get("beat_frozen"),
        "caps": caps,
    }


def build(*, sweep_path: Path, prior_path: Path, push_path: Path) -> dict[str, Any]:
    sweep = _load(sweep_path)
    if not sweep:
        raise FileNotFoundError(f"missing sweep: {sweep_path}")

    rows = [r for r in (sweep.get("rows") or []) if isinstance(r, dict)]
    if not rows:
        raise ValueError("sweep has no rows")

    j_best = max(
        rows,
        key=lambda r: float((r.get("aggregate") or {}).get("avg_reconstruction_fidelity_jaccard") or 0),
    )
    s_best = max(
        rows,
        key=lambda r: float((r.get("aggregate") or {}).get("global_token_saving_rate") or 0),
    )

    frozen_ref = sweep.get("frozen_active_reference") or {}
    frozen_saving = float(frozen_ref.get("global_token_saving_rate") or FROZEN_SAVING)
    frozen_j = float(frozen_ref.get("avg_reconstruction_fidelity_jaccard") or FROZEN_J)

    live = _load(ACTIVE) or {}
    live_cm = live.get("compression_metrics") or {}

    prior_doc = _load(prior_path)
    prior_agg = (prior_doc or {}).get("aggregate") or {}
    prior_beat = (prior_doc or {}).get("beat_check") or {}

    push = _load(push_path) or {}

    doc: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "frozen_active": {
            "global_token_saving_rate": frozen_saving,
            "avg_reconstruction_fidelity_jaccard": frozen_j,
            "ssot": str(ACTIVE.relative_to(ROOT)).replace("\\", "/"),
            "beat_baseline": "canonical_frozen_constants",
        },
        "live_active_on_disk": {
            "global_token_saving_rate": live_cm.get("global_token_saving_rate"),
            "avg_reconstruction_fidelity_jaccard": live_cm.get(
                "avg_reconstruction_fidelity_jaccard"
            ),
            "note": "informational only — beat_check uses frozen_active above",
        },
        "sweep": {
            "script": "scripts/run_ng40_path_b_dual_axis_push_v1.py",
            "sweep_pointer": str(sweep_path.relative_to(ROOT)).replace("\\", "/"),
            "generated_at_utc": sweep.get("generated_at_utc"),
            "combo_count": sweep.get("combo_count", len(rows)),
            "lane": "41k_on + active_track_parity",
            "any_beat_frozen_vs_active": sweep.get("any_beat_frozen_vs_active"),
            "beat_rows_count": sweep.get("beat_rows_count"),
        },
        "knee_j_first": {
            "label_ko": "품질(J) 우선 — saving은 본선보다 낮을 수 있음",
            **_knee_row(j_best),
        },
        "knee_saving_first": {
            "label_ko": "절감(saving) 우선 — J는 본선보다 낮을 수 있음",
            **_knee_row(s_best),
            "note_ko": "path_b_sweep saving-max; promotion floor jaccard_drop_within_2pp도 미달 가능",
        },
        "path_b_blocker_ko": (
            f"동일 Golden-40·evaluate_report 경로에서는 cap 튜닝만으로 "
            f"saving≥본선 AND J≥본선 동시 달성 조합 없음({sweep.get('combo_count', len(rows))}/{sweep.get('combo_count', len(rows))})."
            if not sweep.get("any_beat_frozen_vs_active")
            else "일부 beat 조합 존재 — sweep beat_rows_count 확인"
        ),
        "forbidden": [
            "--apply-active without beat_frozen on ACTIVE",
            "shard_merged_parallel(0.488/0.868)을 beat 성공으로 서술",
        ],
    }

    if prior_doc:
        doc["prior_41k_wired_eval"] = {
            "path": str(prior_path.relative_to(ROOT)).replace("\\", "/"),
            "prior_terms": prior_doc.get("prior_terms_count"),
            "beat_frozen_vs_active": prior_beat.get("beat_frozen"),
            "saving": prior_agg.get("global_token_saving_rate"),
            "jaccard": prior_agg.get("avg_reconstruction_fidelity_jaccard"),
            "note_ko": "LUT salience must_keep + 41k knee caps; dual-axis 여전히 미달 가능",
        }

    if push.get("best"):
        doc["dual_axis_push_manifest"] = {
            "path": str(push_path.relative_to(ROOT)).replace("\\", "/"),
            "generated_at_utc": push.get("generated_at_utc"),
            "any_beat_frozen_vs_active": push.get("any_beat_frozen_vs_active"),
        }

    doc["next_options"] = [
        "코덱/디코더 변경(잠재 단일축 → spine+sidecar 분리는 경로 A)",
        "벤치 분리(상용=byte_exact, 경쟁=latent) 후 게이트 재정의",
        "지휘관 Pareto 승인: knee_j_first만 연구 헤드라인(본선 교체 아님)",
    ]
    return doc


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sweep", type=Path, default=SWEEP)
    ap.add_argument("--prior-41k", type=Path, default=PRIOR_41K)
    ap.add_argument("--push-manifest", type=Path, default=PUSH_MANIFEST)
    ap.add_argument("--output", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args(argv)

    try:
        doc = build(sweep_path=args.sweep, prior_path=args.prior_41k, push_path=args.push_manifest)
    except (FileNotFoundError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 2

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "output": str(args.output),
                "knee_j_saving": doc["knee_j_first"].get("global_token_saving_rate"),
                "knee_j_jaccard": doc["knee_j_first"].get("avg_reconstruction_fidelity_jaccard"),
                "knee_s_saving": doc["knee_saving_first"].get("global_token_saving_rate"),
                "knee_s_jaccard": doc["knee_saving_first"].get("avg_reconstruction_fidelity_jaccard"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
