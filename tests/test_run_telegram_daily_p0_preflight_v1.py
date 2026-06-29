"""Telegram daily P0 preflight + prophecy Field Final Call block."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import send_telegram_minimal_ops_digest_v1 as tg  # noqa: E402


def test_build_digest_prophecy_includes_field_final_call(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("MKM_TELEGRAM_PROPHECY_INCLUDE_FORTUNE", "0")
    art = tmp_path / "docs" / "final" / "artifacts"
    art.mkdir(parents=True, exist_ok=True)
    (art / "internal_kospi_morning_brief_onepager_latest.json").write_text(
        json.dumps(
            {
                "today_action": "WATCH",
                "confidence_0_100": 55,
                "market_session_ko": "개장일",
                "promotion_decision": "HOLD_OPERATIONAL_V1",
                "field_final_call": {
                    "attach_mode": "OFF",
                    "operator_posture": "watch_tighten",
                },
                "dual_leg_kospi_n_evaluated": 30,
                "dual_leg_kospi_hit_rate": 0.3,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    for name, payload in (
        ("trackc_prophecy_dual_leg_brief_latest.json", {"legs": {"kospi": {"n_evaluated": 30}}}),
        ("btrack_hypothesis_prophecy_latest.json", {"prediction": {"instrument": "kospi", "direction": "bear"}}),
        ("prophecy_hit_rate_eval_latest.json", {"metrics": {"price_directional_hit_rate": 0.3, "n_evaluated": 30}}),
    ):
        (art / name).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    text = tg.build_digest_prophecy(tmp_path)
    assert "Field Final Call" in text
    assert "NON_GATING" in text
    assert "attach OFF" in text
    assert "주시·긴장" in text


def test_telegram_daily_preflight_manifest_skip_build() -> None:
    rc = subprocess.call(
        [sys.executable, str(ROOT / "scripts/run_telegram_daily_p0_preflight_v1.py"), "--skip-build"],
        cwd=str(ROOT),
    )
    assert rc == 0
    out = ROOT / "reports/telegram_daily_wiring_v1_latest.json"
    assert out.is_file()
    doc = json.loads(out.read_text(encoding="utf-8-sig"))
    assert doc["schema"] == "telegram_daily_wiring_v1"
    assert doc["p3_hard_lock"]["p3_forbidden"] is True
    assert doc["telegram_contract"]["field_final_call_in_digest"] is True
