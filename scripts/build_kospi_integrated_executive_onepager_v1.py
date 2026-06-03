#!/usr/bin/env python3
"""Build KOSPI integrated executive one-pager from disk SSOT [HYPO]."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_OUT = ROOT / "reports/kospi_integrated_executive_onepager_latest.md"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _ko_dir(raw: Any) -> str:
    table = {"bull": "상승", "bear": "하락", "neutral": "중립"}
    return table.get(str(raw or "").lower(), str(raw or "—"))


def build_markdown(*, workspace: Path = ROOT) -> str:
    art = workspace / "docs" / "final" / "artifacts"
    hypo = _read_json(art / "btrack_hypothesis_prophecy_latest.json")
    brief = _read_json(art / "internal_kospi_morning_brief_onepager_latest.json")
    overnight = _read_json(art / "global_market_overnight_signals_v1_latest.json")
    dual = _read_json(art / "trackc_prophecy_dual_leg_brief_latest.json")
    sasang = _read_json(art / "sasang_independent_lens_latest.json")
    myeongni = _read_json(art / "myeongni_independent_lens_latest.json")
    logos = _read_json(art / "logos_independent_lens_latest.json")
    resonance = _read_json(art / "logos_regime_resonance_shadow_signal_latest.json")

    pred = hypo.get("prediction") or {}
    rm = hypo.get("runtime_meta") or {}
    lv = rm.get("lens_values") or {}
    overlay = ((rm.get("price_meta") or {}).get("kospi_overnight_overlay") or {})
    bh = brief.get("btrack_hypothesis") or {}
    kospi_hr = ((dual.get("legs") or {}).get("kospi") or {}).get("price_directional_hit_rate")
    best_regime = ((resonance.get("summary") or {}).get("best_regime")) or "—"
    sasang_ax = sasang.get("b_track_axis_scores_v1") or {}

    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        "# KOSPI 통합 Executive One-Pager",
        "",
        f"- generated_at_utc: `{now_utc}`",
        "- tier: `[HYPO]` · `research_only` · Track A/실매매 자동 연동 없음",
        "",
        "## Final (운영·연구 분리)",
        "",
        f"| 구분 | 값 |",
        f"|------|-----|",
        f"| B-track 1D 방향 | **{_ko_dir(pred.get('direction'))}** · conf `{pred.get('confidence')}` |",
        f"| weighted_score | `{rm.get('weighted_score')}` |",
        f"| Internal brief | `{brief.get('today_action')}` · `{brief.get('confidence_0_100')}/100` |",
        f"| 운영 Final | **WATCH** (KOSPI hit `{kospi_hr}`) |",
        "",
        "## Field → Lens → Conflict",
        "",
        f"- **Field:** `{overnight.get('composite_tilt')}` · 2차 Logos `{best_regime}` `[NON_GATING]`",
        f"- **price:** `{lv.get('price', {}).get('score')}` (overlay `{overlay.get('price_score_after_blend')}`)",
        f"- **news/macro:** `{lv.get('news', {}).get('score')}` / `{lv.get('macro', {}).get('score')}`",
        f"- **사상:** heat `{sasang_ax.get('heat_proxy')}` · phase `{((sasang.get('sasang_stream_outputs') or {}).get('regime_hypothesis'))}`",
        f"- **명리:** state `{((myeongni.get('myeongri_stream_outputs') or {}).get('state_id'))}` · arb `{((myeongni.get('advanced') or {}).get('coordinator') or {}).get('mkm_myeongni_math', {}).get('arbitrated_direction_score')}`",
        f"- **성경:** `{logos.get('scores', {}).get('direction_score')}` `[NON_GATING]`",
        f"- **Conflict:** 국내 모멘텀↑ vs US overnight↓ · 사상 heat vs news cold",
        "",
        f"## Overnight board (anchor `{overnight.get('session_anchor_date') or '—'}`)",
        "",
    ]
    for row in overnight.get("indices") or []:
        if not isinstance(row, dict):
            continue
        lines.append(
            f"- {row.get('id')}: `{row.get('change_pct')}%` ({row.get('source', 'snapshot')})"
        )
    lines.extend(
        [
            "",
            "## Evidence",
            "",
            "- `docs/final/artifacts/btrack_hypothesis_prophecy_latest.json`",
            "- `docs/final/artifacts/internal_kospi_morning_brief_onepager_latest.json`",
            "- `reports/kospi_hypothesis_reroute_phase_b_v1_latest.json`",
            "",
            f"_hypothesis_ts: `{hypo.get('ts_utc')}` · brief_ts: `{brief.get('generated_at_utc')}`_",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    out = DEFAULT_OUT
    if len(sys.argv) > 1:
        out = Path(sys.argv[1])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build_markdown(), encoding="utf-8")
    print(f"WROTE: {out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
