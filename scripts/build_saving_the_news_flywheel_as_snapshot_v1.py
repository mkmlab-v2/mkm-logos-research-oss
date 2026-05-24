#!/usr/bin/env python3
"""Saving the News flywheel A/S transparency snapshot (axis-separated, B-track)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
OUT = ART / "saving_the_news_flywheel_as_snapshot_v1_latest.json"

HIT_RATE = ART / "prophecy_hit_rate_eval_latest.json"
NEWS_RT = ART / "saving_the_news_news_rt_bench_result_v1_latest.json"
PANEL = ROOT / "reports" / "prophecy_panel_24h_alerts_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def build_snapshot() -> dict[str, Any]:
    hit = _read(HIT_RATE) or {}
    news_rt = _read(NEWS_RT) or {}
    panel = _read(PANEL) or {}

    hit_metrics = hit.get("metrics") if isinstance(hit.get("metrics"), dict) else {}
    price_hit = hit_metrics.get("price_directional_hit_rate")
    n_eval = hit_metrics.get("n_evaluated")

    rt_metrics = news_rt.get("metrics") if isinstance(news_rt.get("metrics"), dict) else {}
    j_proxy = rt_metrics.get("jaccard_fidelity_proxy")
    saving = rt_metrics.get("token_saving_ratio")

    panel_alerts = panel.get("alerts") if isinstance(panel.get("alerts"), list) else []
    alert_1 = next(
        (a for a in panel_alerts if isinstance(a, dict) and a.get("alert_id") == "ALERT_1_PERFORMANCE"),
        None,
    )

    axes: list[dict[str, Any]] = []
    if price_hit is not None:
        axes.append(
            {
                "axis_id": "BTRACK_PRICE_HIT_RATE",
                "label": "B-track price directional hit rate (30d window typical)",
                "value": price_hit,
                "n_evaluated": n_eval,
                "source": "docs/final/artifacts/prophecy_hit_rate_eval_latest.json",
                "not_news_universal_saving_claim": True,
            }
        )
    if j_proxy is not None:
        axes.append(
            {
                "axis_id": "NEWS_RT_OFFLINE",
                "label": "NEWS-RT offline cohort Jaccard proxy",
                "value": j_proxy,
                "token_saving_ratio": saving,
                "source": "docs/final/artifacts/saving_the_news_news_rt_bench_result_v1_latest.json",
                "not_logos_cap_axis": True,
            }
        )
    if alert_1:
        axes.append(
            {
                "axis_id": "PANEL_ALERT_1",
                "label": "24h panel performance alert (observation)",
                "observed": alert_1.get("observed"),
                "threshold": alert_1.get("threshold"),
                "source": "reports/prophecy_panel_24h_alerts_latest.json",
            }
        )

    return {
        "schema": "saving_the_news_flywheel_as_snapshot_v1",
        "version": "1.0.0",
        "lane": "research_only",
        "hypothesis_tier": "B",
        "ready_for_external_send": False,
        "generated_at_utc": _utc_now(),
        "flywheel_stage": "4_as_transparency",
        "autonomous_evolution_note": (
            "Weight/filter tuning remains B-track + human sign-off; "
            "no code or manseryeok auto-mutation."
        ),
        "axes": axes,
        "forbidden_claims": [
            "Do not cite LOGOS-CAP 84.5% as news prophecy accuracy.",
            "Do not auto-promote to Track A or live routing from this snapshot.",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output-json", type=Path, default=OUT)
    args = ap.parse_args()

    doc = build_snapshot()
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output_json} axes={len(doc.get('axes') or [])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
