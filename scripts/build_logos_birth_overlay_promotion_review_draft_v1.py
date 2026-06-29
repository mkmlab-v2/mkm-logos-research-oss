#!/usr/bin/env python3
"""Human sign-off draft for Logos OOS / birth overlay — does NOT write SSOT until approved."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/logos_birth_overlay_promotion_review_draft_v1_latest.json"
SSOT_GATE = ROOT / "docs/final/artifacts/prophecy_logos_revalidation_oos_gate_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    ssot = _read(SSOT_GATE)
    ssot_oos = ssot.get("oos_metrics") if isinstance(ssot.get("oos_metrics"), dict) else {}
    holdout = _read(ROOT / "reports/logos_oos_blind_holdout_fixed_dates_v1_latest.json")
    compare = _read(ROOT / "reports/logos_oos_sidecar_variant_compare_v1_latest.json")
    birth_oos = _read(ROOT / "reports/logos_oos_kospi_birth_overlay_sw025_band006_v1_latest.json")
    birth_hold = next(
        (
            v
            for v in (holdout.get("variants") or [])
            if isinstance(v, dict) and v.get("label") == "birth_overlay_sw025_band006"
        ),
        {},
    )

    draft = {
        "schema": "logos_birth_overlay_promotion_review_draft_v1",
        "generated_at_utc": _now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "status": "pending_commander_signoff",
        "apply_forbidden": True,
        "would_update_paths_on_approval": [
            "docs/final/artifacts/prophecy_logos_revalidation_oos_gate_latest.json",
        ],
        "would_not_update_without_signoff": [
            "docs/final/artifacts/btrack_prophecy_score_insight_sidecar_v1_latest.json",
            "Track A live trading gates",
        ],
        "current_ssot": {
            "path": str(SSOT_GATE.relative_to(ROOT)).replace("\\", "/"),
            "oos_hit": ssot_oos.get("directional_hit_rate_active"),
            "oos_n_active": ssot_oos.get("n_active_days"),
            "recipe_ko": "KOSPI + 30y dual score + sparse_orig(202604) sidecar · lb28 nz0.15 oos252",
        },
        "candidate_birth_overlay_sw025_band006": {
            "sidecar": "docs/final/artifacts/btrack_prophecy_score_insight_sidecar_30y_birth_overlay_sw025_band006_v1.json",
            "full_oos_report": "reports/logos_oos_kospi_birth_overlay_sw025_band006_v1_latest.json",
            "oos_hit": (birth_oos.get("oos_metrics") or {}).get("directional_hit_rate_active"),
            "oos_n_active": (birth_oos.get("oos_metrics") or {}).get("n_active_days"),
            "train_n_active": ((birth_oos.get("best_train_candidate") or {}).get("train_metrics") or {}).get(
                "n_active_days"
            ),
            "blind_holdout": birth_hold.get("blind_window"),
            "confirm_holdout": birth_hold.get("confirm_window"),
            "promotion_candidate_holdout": birth_hold.get("promotion_candidate"),
        },
        "variant_compare_pointer": "reports/logos_oos_sidecar_variant_compare_v1_latest.json",
        "variant_compare_best_label": compare.get("best_oos_hit_label"),
        "gate_checks_for_approval": {
            "blind_hit_min_0_52": bool(birth_hold.get("blind_hit_pass")),
            "confirm_hit_min_0_52": bool(birth_hold.get("confirm_hit_pass")),
            "both_halves_pass": bool(birth_hold.get("promotion_candidate")),
            "beats_ssot_full_oos": (
                float((birth_oos.get("oos_metrics") or {}).get("directional_hit_rate_active") or 0)
                > float(ssot_oos.get("directional_hit_rate_active") or 0)
            ),
        },
        "recommendation_ko": (
            "현재 SSOT 유지 권장. birth full-OOS 0.643는 blind 0.50(<0.52)으로 "
            "고정일 홀드아웃 promotion_candidate=false. "
            "승격 시에도 성숙도 D·[NON_GATING] 문구는 golden 0.565 근거 유지, "
            "birth는 연구 각주·별도 sidecar 경로만."
        ),
        "approval_block": {
            "commander_signoff": False,
            "legal_counsel_signoff": False,
            "notes": "",
        },
        "if_approved_apply_commands_ko": [
            "지휘관 명시 승인 후에만: prophecy_logos_revalidation_oos_gate_latest.json 을 "
            "birth OOS 리포트로 교체하지 말 것(권장) — 대신 research appendix JSON 갱신.",
            "대안(비권장): human이 직접 SSOT gate JSON 편집 + build_lens_maturity 재실행.",
        ],
        "disclaimer_ko": "본 초안은 승인 전 효력 없음. Track A·실매매 자동 GO 아님.",
    }

    text = json.dumps(draft, ensure_ascii=False, indent=2) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text, encoding="utf-8")
    print(text)
    print(f"WROTE: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
