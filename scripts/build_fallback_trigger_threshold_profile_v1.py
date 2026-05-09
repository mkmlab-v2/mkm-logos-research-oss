#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

STRESS_GRID = ART / "trackb_quaternion_top_combo_stress_grid_latest.json"
NEWS_PLUS = ART / "news_grade_plus_scorecard_latest.json"
PUBLIC_SAFE = ART / "trackb_quaternion_top_combo_public_safe_profile_latest.json"

OUT_PROFILE = ART / "fallback_trigger_threshold_profile_latest.json"
OUT_STATUS = ART / "fallback_trigger_status_latest.json"
OUT_MD = ART / "fallback_trigger_status_latest.md"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    for enc in ("utf-8", "utf-8-sig"):
        try:
            return json.loads(path.read_text(encoding=enc))
        except Exception:
            continue
    return {}


def main() -> int:
    stress = _read_json(STRESS_GRID)
    news = _read_json(NEWS_PLUS)
    public_safe = _read_json(PUBLIC_SAFE)

    rows = stress.get("rows") if isinstance(stress.get("rows"), list) else []
    min_rates: list[float] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        ss = row.get("stress_summary") if isinstance(row.get("stress_summary"), dict) else {}
        v = ss.get("min_exact_sequence_match_rate_over_grid")
        if isinstance(v, (int, float)):
            min_rates.append(float(v))

    collapse_detected = any(v < 0.75 for v in min_rates)
    news_ready = bool(news.get("news_grade_plus_ready", False))

    # Conservative starting thresholds for production-safe rollout.
    profile = {
        "schema": "fallback_trigger_threshold_profile_v1",
        "generated_at_utc": _now(),
        "profile_name": "conservative_v1",
        "signals": {
            "oov_ratio_threshold": 0.15 if collapse_detected else 0.20,
            "typo_ratio_threshold": 0.05,
            # v3: raised from 12000 after post-cutoff diagnosis showed p90~16200 and input-token threshold dominance.
            "input_tokens_threshold": 14000,
            "unknown_token_rate_threshold": 0.15,
            "detected_noise_mode_threshold": 0.50,
        },
        "trigger_logic": {
            "mode": "any_of",
            "rule": "If any signal exceeds threshold, force fallback-safe mode.",
        },
        "fallback_actions": [
            "disable_aggressive_decode_path",
            "enable_dictionary_safe_decode",
            "cap_reconstruction_confidence",
            "emit_non_blocking_warning_flag",
        ],
        "track_wall": {
            "track_a_autobind_forbidden": True,
            "research_only_tuning": True,
        },
        "fact_safe_note": (
            "Conservative defaults; input_tokens_threshold v3=14000 from post-cutoff diagnosis. "
            "Re-run build_fallback_trigger_daily_summary_v1 after changes; track_wall research_only_tuning remains."
        ),
    }

    OUT_PROFILE.write_text(json.dumps(profile, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    status = {
        "schema": "fallback_trigger_status_v1",
        "generated_at_utc": _now(),
        "decision": "ENABLE_FALLBACK_CONSERVATIVE",
        "reason": (
            "TrackB stress includes collapse candidates; public profile already filters them. "
            "Fallback guard should remain enabled for unknown/edge conditions."
        ),
        "inputs": {
            "news_grade_plus_ready": news_ready,
            "stress_candidate_count": len(rows),
            "stress_min_exact_min": min(min_rates) if min_rates else None,
            "public_safe_selected_count": public_safe.get("selected_count"),
            "public_safe_dropped_count": public_safe.get("dropped_count"),
        },
        "active_profile": str(OUT_PROFILE.relative_to(ROOT)).replace("\\", "/"),
        "out_of_scope": "Not a production SLA guarantee. Guardrail control only.",
    }
    OUT_STATUS.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md_lines = [
        "# Fallback Trigger Status (Latest)",
        "",
        f"- decision: `{status['decision']}`",
        f"- reason: {status['reason']}",
        f"- active_profile: `{status['active_profile']}`",
        "",
        "## Inputs",
        f"- news_grade_plus_ready: `{status['inputs']['news_grade_plus_ready']}`",
        f"- stress_candidate_count: `{status['inputs']['stress_candidate_count']}`",
        f"- stress_min_exact_min: `{status['inputs']['stress_min_exact_min']}`",
        f"- public_safe_selected_count: `{status['inputs']['public_safe_selected_count']}`",
        f"- public_safe_dropped_count: `{status['inputs']['public_safe_dropped_count']}`",
        "",
    ]
    OUT_MD.write_text("\n".join(md_lines), encoding="utf-8")

    print(str(OUT_PROFILE))
    print(str(OUT_STATUS))
    print(str(OUT_MD))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
