#!/usr/bin/env python3
"""Build docs/final/artifacts/ATHENA_UPLOAD_ONEFILE_LATEST.md from live JSON artifacts."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
OUT = ART / "ATHENA_UPLOAD_ONEFILE_LATEST.md"


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def getv(data: dict[str, Any], *keys: str) -> Any:
    cur: Any = data
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return "확인 필요"
        cur = cur[k]
    return cur


def q(value: Any) -> str:
    if isinstance(value, str):
        return f'"{value}"'
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return json.dumps(value, ensure_ascii=False)


def main() -> int:
    prophecy_p = ART / "prophecy_2026_monthly_kospi_btc_fact_safe_v1.json"
    governance_p = ART / "integrated_governance_v1_latest.json"
    go_nogo_p = ART / "a_track_go_nogo_status_latest.json"
    myeongri_p = ART / "kospi_myeongri_standalone_commercial_gate_v1_latest.json"
    sasang_p = ART / "kospi_sasang_single_lane_commercial_gate_v1_latest.json"
    biblical_p = ART / "kospi_biblical_single_lane_commercial_gate_v1_latest.json"

    prophecy = load_json(prophecy_p)
    governance = load_json(governance_p)
    go_nogo = load_json(go_nogo_p)
    myeongri = load_json(myeongri_p)
    sasang = load_json(sasang_p)
    biblical = load_json(biblical_p)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    lines = [
        "# ATHENA Upload Onefile (Latest)",
        "",
        "Use this single file for Gemini/NotebookLM upload.",
        "Do not move original artifacts. This file is a derived snapshot only.",
        "",
        f"Generated At (UTC): {now}",
        "",
        "## Source of truth (unchanged original paths)",
        "- `docs/final/artifacts/prophecy_2026_monthly_kospi_btc_fact_safe_v1.json`",
        "- `docs/final/artifacts/integrated_governance_v1_latest.json`",
        "- `docs/final/artifacts/a_track_go_nogo_status_latest.json`",
        "- `docs/final/artifacts/kospi_myeongri_standalone_commercial_gate_v1_latest.json`",
        "- `docs/final/artifacts/kospi_sasang_single_lane_commercial_gate_v1_latest.json`",
        "- `docs/final/artifacts/kospi_biblical_single_lane_commercial_gate_v1_latest.json`",
        "",
        "## Canonical path/key/value snapshot",
        "",
        "### 1) prophecy_2026_monthly_kospi_btc_fact_safe_v1.json",
        "- path: `docs/final/artifacts/prophecy_2026_monthly_kospi_btc_fact_safe_v1.json`",
        f"- key/value: `meta.high_reliability_decision` / {q(getv(prophecy, 'meta', 'high_reliability_decision'))}",
        f"- key/value: `meta.price_output_locked` / {q(getv(prophecy, 'meta', 'price_output_locked'))}",
        f"- key/value: `risk_profile.mode` / {q(getv(prophecy, 'risk_profile', 'mode'))}",
        "",
        "### 2) integrated_governance_v1_latest.json",
        "- path: `docs/final/artifacts/integrated_governance_v1_latest.json`",
        f"- key/value: `final_regime` / {q(getv(governance, 'final_regime'))}",
        f"- key/value: `final_score` / {q(getv(governance, 'final_score'))}",
        f"- key/value: `final_action_allowed` / {q(getv(governance, 'final_action_allowed'))}",
        "",
        "### 3) a_track_go_nogo_status_latest.json",
        "- path: `docs/final/artifacts/a_track_go_nogo_status_latest.json`",
        f"- key/value: `result.overall_go_no_go` / {q(getv(go_nogo, 'result', 'overall_go_no_go'))}",
        f"- key/value: `result.recommended_stage` / {q(getv(go_nogo, 'result', 'recommended_stage'))}",
        f"- key/value: `snapshot.chronos_holdout_direction_match_rate` / {q(getv(go_nogo, 'snapshot', 'chronos_holdout_direction_match_rate'))}",
        f"- key/value: `result.failed_reasons` / {q(getv(go_nogo, 'result', 'failed_reasons'))}",
        "",
        "### Lens readiness",
        "- path: `docs/final/artifacts/kospi_myeongri_standalone_commercial_gate_v1_latest.json`",
        f"- key/value: `standalone_commercial_ready` / {q(getv(myeongri, 'standalone_commercial_ready'))}",
        f"- key/value: `metrics.abs_train_test_acc_gap` / {q(getv(myeongri, 'metrics', 'abs_train_test_acc_gap'))}",
        "",
        "- path: `docs/final/artifacts/kospi_sasang_single_lane_commercial_gate_v1_latest.json`",
        f"- key/value: `commercial_ready` / {q(getv(sasang, 'commercial_ready'))}",
        f"- key/value: `latest_single_lane_gate.precommercial_ready` / {q(getv(sasang, 'latest_single_lane_gate', 'precommercial_ready'))}",
        "",
        "- path: `docs/final/artifacts/kospi_biblical_single_lane_commercial_gate_v1_latest.json`",
        f"- key/value: `precommercial_ready` / {q(getv(biblical, 'precommercial_ready'))}",
        f"- key/value: `stability.current_ready_streak` / {q(getv(biblical, 'stability', 'current_ready_streak'))}",
        f"- key/value: `stability.stability_go` / {q(getv(biblical, 'stability', 'stability_go'))}",
        "",
        "## Forced decision rules for Athena",
        '- If `meta.high_reliability_decision=="HOLD"` OR `meta.price_output_locked==true`, Final Action must be `HOLD`.',
        '- Even if `final_regime=="ATTACK"`, apply `most_conservative_wins`.',
        "- Final Action reason must reuse `result.failed_reasons` raw array.",
        "",
        "## Final fixed line",
        '"현재 증거 범위에서는 운영 가능하나, Unverified Items 해소 전까지 HOLD 가드레일을 유지합니다."',
        "",
    ]

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"written: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

