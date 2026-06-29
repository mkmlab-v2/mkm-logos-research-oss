"""Four-lens Telegram report builders."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_telegram_four_lens_reports_v1 import build_four_lens_reports  # noqa: E402


def test_build_four_lens_keys_and_headers(tmp_path: Path) -> None:
    art = tmp_path / "docs" / "final" / "artifacts"
    art.mkdir(parents=True, exist_ok=True)
    (art / "myeongni_independent_lens_from_chain_latest.json").write_text(
        json.dumps(
            {
                "scores": {"direction_score": 0.02, "confidence": 0.5},
                "advanced": {
                    "input_summary": {"pillars": {"year": "갑자", "month": "병인", "day": "무진", "hour": "경오"}},
                    "coordinator": {"mkm_myeongni_math": {"status": "ok", "day_master_stem": "무"}},
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (art / "myeongni_independent_lens_latest.json").write_text(
        json.dumps({"scores": {"direction_score": 0.02}}), encoding="utf-8"
    )
    (art / "logos_independent_lens_latest.json").write_text(
        json.dumps({"scores": {"direction_score": -0.1, "confidence": 0.6}}), encoding="utf-8"
    )
    (art / "sasang_independent_lens_latest.json").write_text(
        json.dumps(
            {
                "scores": {"direction_score": 0.05},
                "sasang_stream_outputs": {
                    "regime_hypothesis": "heat_watch",
                    "machine_readables": {"heat_proxy": 0.7, "cold_proxy": 0.2},
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (art / "global_market_overnight_signals_v1_latest.json").write_text(
        json.dumps({"composite_tilt": "risk_off"}), encoding="utf-8"
    )
    (art / "btrack_hypothesis_prophecy_latest.json").write_text(
        json.dumps({"prediction": {"instrument": "btc", "direction": "bear", "confidence": 0.55}}),
        encoding="utf-8",
    )
    (art / "trading_go_no_go_latest.json").write_text(
        json.dumps({"go_no_go": "NO_GO", "risk_mode": "LOCKED_MODE"}), encoding="utf-8"
    )
    (art / "independent_lens_shadow_gate_latest.json").write_text(
        json.dumps({"decision": "research_only"}), encoding="utf-8"
    )
    reports = tmp_path / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "logos_2026_market_news_prophecy_graphrag_v1_latest.md").write_text(
        "## 0. 해석\nWATCH 서사\n\n## 1. Field→Lens→Conflict→Final\nField risk_off\n",
        encoding="utf-8",
    )
    (reports / "sasang_rule_based_response_v1_latest.md").write_text(
        "- top_axis: heat\n## 5) 결론\nWATCH_CONFIRMATION\n",
        encoding="utf-8",
    )
    out = build_four_lens_reports(tmp_path)
    assert set(out.keys()) == {"myeongni", "logos", "sasang", "synthesis"}
    assert "명리" in out["myeongni"]
    assert "성경" in out["logos"] or "Logos" in out["logos"]
    assert "사상" in out["sasang"]
    assert "종합" in out["synthesis"]
    assert "WATCH" in out["synthesis"]
    assert "[HYPO]" in out["myeongni"]
