"""Personal-only Telegram digest — no prophecy English blocks."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import send_telegram_minimal_ops_digest_v1 as tg  # noqa: E402


def test_build_digest_personal_only_fortune(tmp_path: Path) -> None:
    fortune = {
        "schema": "commander_daily_fortune_v1_1",
        "telegram_append_lines": [
            "",
            "▸ 개인 일운 (명리)",
            "  일운 병신",
            "",
            "▸ 오늘 라이프 [HYPO]",
            "  점심: 닭곰탕",
        ],
    }
    (tmp_path / "reports").mkdir(parents=True, exist_ok=True)
    (tmp_path / "reports" / "commander_daily_fortune_latest.json").write_text(
        json.dumps(fortune, ensure_ascii=False), encoding="utf-8"
    )
    text = tg.build_digest_personal(tmp_path)
    assert "지휘관 오늘 일운" in text
    assert "KOSPI" not in text
    assert "BTC" not in text
    assert "예언 브리핑" not in text
    assert "닭곰탕" in text
    assert "일운 병신" in text


def test_build_digest_prophecy_korean_no_fortune(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("MKM_TELEGRAM_PROPHECY_INCLUDE_FORTUNE", "0")
    art = tmp_path / "docs" / "final" / "artifacts"
    art.mkdir(parents=True, exist_ok=True)
    (art / "internal_kospi_morning_brief_onepager_latest.json").write_text(
        json.dumps(
            {
                "today_action": "HOLD",
                "confidence_0_100": 40,
                "market_session_ko": "휴장(주말)",
                "dual_leg_kospi_n_evaluated": 15,
                "dual_leg_kospi_hit_rate": 0.533333,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (art / "trackc_prophecy_dual_leg_brief_latest.json").write_text(
        json.dumps({"legs": {"btc": {"n_evaluated": 0, "price_directional_hit_rate": None}}}, ensure_ascii=False),
        encoding="utf-8",
    )
    (art / "btrack_hypothesis_prophecy_latest.json").write_text(
        json.dumps({"prediction": {"instrument": "kospi", "direction": "bull", "confidence": 0.71}}, ensure_ascii=False),
        encoding="utf-8",
    )
    (art / "prophecy_hit_rate_eval_latest.json").write_text(
        json.dumps({"metrics": {"price_directional_hit_rate": 0.666667, "n_evaluated": 15}}, ensure_ascii=False),
        encoding="utf-8",
    )
    fortune = tmp_path / "reports" / "commander_daily_fortune_latest.json"
    fortune.parent.mkdir(parents=True, exist_ok=True)
    fortune.write_text(
        json.dumps({"schema": "commander_daily_fortune_v1", "telegram_append_lines": ["▸ 개인 일운"]}, ensure_ascii=False),
        encoding="utf-8",
    )
    text = tg.build_digest_prophecy(tmp_path)
    assert "MKM 장전 예언 브리핑" in text
    assert "관망" in text
    assert "코스피" in text
    assert "상승" in text
    assert "개인 일운" not in text
    assert "R-IBL" not in text
    assert "BTC" not in text
    assert "executive" not in text.lower()
    assert "HYPO" not in text
    assert "Internal brief" not in text
    assert "B-track" not in text
    assert "US prior" not in text


def test_sanitize_telegram_ko_strips_ops_english() -> None:
    raw = "▸ Field Final Call · attach OFF · pass_candidate · WF mean 56%"
    out = tg._sanitize_telegram_ko(raw)
    assert "Field Final Call" not in out
    assert "pass_candidate" not in out
    assert "WF mean" not in out
    assert "실물" in out or "합격후보" in out or "평균" in out


def test_ko_promotion_decision_does_not_mangle_conditional() -> None:
    assert tg._ko_promotion_decision("GO_CONDITIONAL") == "조건부실행"
    out = tg._sanitize_telegram_ko("▸ 오늘 장전: GO_CONDITIONAL · 승격 GO_CONDITIONAL")
    assert "켬DITI" not in out
    assert "조건부실행" in out


def test_ko_calendar_status_sealed_today() -> None:
    assert tg._ko_calendar_status("sealed_today") == "오늘봉인"


def test_build_digest_prophecy_includes_mission_c_shadow(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("MKM_TELEGRAM_PROPHECY_INCLUDE_FORTUNE", "0")
    monkeypatch.setenv("MKM_TELEGRAM_PROPHECY_INCLUDE_MISSION_C_SHADOW", "1")
    art = tmp_path / "docs" / "final" / "artifacts"
    art.mkdir(parents=True, exist_ok=True)
    (art / "internal_kospi_morning_brief_onepager_latest.json").write_text(
        json.dumps({"today_action": "HOLD", "confidence_0_100": 40}, ensure_ascii=False),
        encoding="utf-8",
    )
    (art / "trackc_prophecy_dual_leg_brief_latest.json").write_text("{}", encoding="utf-8")
    (art / "btrack_hypothesis_prophecy_latest.json").write_text(
        json.dumps({"prediction": {"instrument": "kospi", "direction": "bull"}}, ensure_ascii=False),
        encoding="utf-8",
    )
    (art / "prophecy_hit_rate_eval_latest.json").write_text(
        json.dumps({"metrics": {"price_directional_hit_rate": 0.5, "n_evaluated": 10}}, ensure_ascii=False),
        encoding="utf-8",
    )
    reports = tmp_path / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "mission_c_shadow_ops_status_v1_latest.json").write_text(
        json.dumps(
            {
                "schema": "mission_c_shadow_ops_status_v1",
                "telegram_digest_block": {
                    "enabled": True,
                    "one_liner": "WF mean 56.0% · stdev 9.98% · streak 2/5 · pass_candidate",
                },
                "gates": {"strict_pass_streak": 2, "strict_streak_required": 5},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    text = tg.build_digest_prophecy(tmp_path)
    assert "미션C 연습장" in text
    assert "연속합격 2/5" in text
    assert "WF mean" not in text
    assert "pass_candidate" not in text
    assert "본선 미변경" in text


def test_build_digest_prophecy_full_fortune_when_enabled(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("MKM_TELEGRAM_PROPHECY_INCLUDE_FORTUNE", "1")
    art = tmp_path / "docs" / "final" / "artifacts"
    art.mkdir(parents=True, exist_ok=True)
    (art / "internal_kospi_morning_brief_onepager_latest.json").write_text(
        json.dumps({"today_action": "WATCH", "confidence_0_100": 50}, ensure_ascii=False),
        encoding="utf-8",
    )
    (art / "trackc_prophecy_dual_leg_brief_latest.json").write_text("{}", encoding="utf-8")
    (art / "btrack_hypothesis_prophecy_latest.json").write_text("{}", encoding="utf-8")
    (art / "prophecy_hit_rate_eval_latest.json").write_text("{}", encoding="utf-8")
    reports = tmp_path / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "commander_daily_fortune_latest.json").write_text(
        json.dumps(
            {
                "schema": "commander_daily_fortune_v1_1",
                "myeongni_lines": ["일운 병신"],
                "mkm_ai_lines": ["▸ 태양 AI: 결단"],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    text = tg.build_digest_prophecy(tmp_path)
    assert "지휘관 사주·명리·일운" in text
    assert "MKM 4AI·조율" in text
    assert "일운 병신" in text


def test_build_digest_prophecy_omits_mission_c_when_disabled(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("MKM_TELEGRAM_PROPHECY_INCLUDE_MISSION_C_SHADOW", "0")
    art = tmp_path / "docs" / "final" / "artifacts"
    art.mkdir(parents=True, exist_ok=True)
    (art / "internal_kospi_morning_brief_onepager_latest.json").write_text("{}", encoding="utf-8")
    (art / "trackc_prophecy_dual_leg_brief_latest.json").write_text("{}", encoding="utf-8")
    (art / "btrack_hypothesis_prophecy_latest.json").write_text("{}", encoding="utf-8")
    (art / "prophecy_hit_rate_eval_latest.json").write_text("{}", encoding="utf-8")
    reports = tmp_path / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "mission_c_shadow_ops_status_v1_latest.json").write_text(
        json.dumps(
            {
                "schema": "mission_c_shadow_ops_status_v1",
                "telegram_digest_block": {"enabled": True, "one_liner": "hidden"},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    text = tg.build_digest_prophecy(tmp_path)
    assert "Mission C 연습장" not in text


def test_resolve_style_default_prophecy(monkeypatch) -> None:
    monkeypatch.delenv("MKM_TELEGRAM_DIGEST_STYLE", raising=False)
    assert tg._resolve_style(None) == "prophecy"


def test_build_digest_afternoon_korean_fortune_and_kospi(tmp_path: Path) -> None:
    from datetime import datetime
    from zoneinfo import ZoneInfo

    cal_kst = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d")
    reports = tmp_path / "reports"
    art = tmp_path / "docs" / "final" / "artifacts"
    reports.mkdir(parents=True, exist_ok=True)
    art.mkdir(parents=True, exist_ok=True)
    prof = tmp_path / "profile.json"
    prof.write_text(
        json.dumps(
            {
                "birth_anchor": {"local_label": "1973-12-10 04:30 Asia/Seoul"},
                "myeongni_fact_ref": {
                    "pillars": {"year": "계축", "month": "갑자", "day": "경진", "hour": "무인"}
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (reports / "commander_daily_fortune_latest.json").write_text(
        json.dumps(
            {
                "schema": "commander_daily_fortune_v1_1",
                "profile_path": str(prof),
                "myeongni_lines": ["일운 병진 · 루틴 정리"],
                "mkm_ai_lines": ["▸ 태양 AI: 결단"],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (reports / "kospi_june2026_daily_prophecy_calendar_v1.json").write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "session_date": cal_kst,
                        "predicted_direction_ko": "상승",
                        "session_direction_score": 0.1,
                        "pillars_session": {
                            "year": "병오",
                            "month": "갑오",
                            "day": "정사",
                            "hour": "을사",
                        },
                        "blend": {
                            "votes": {"bull": 0.78, "bear": 0.0, "neutral": 0.22},
                            "winner_resolution": "directional_bull",
                            "channels": [
                                {
                                    "channel": "session_myeongni",
                                    "direction": "bull",
                                    "weight": 0.3,
                                    "meta": {"score": 0.1},
                                },
                                {
                                    "channel": "sasang",
                                    "direction": "bull",
                                    "weight": 0.24,
                                    "meta": {"score": 0.17},
                                },
                            ],
                        },
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (reports / "kospi_june2026_4ai_prophecy_report_latest.json").write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "session_date": cal_kst,
                        "weekday_ko": "금",
                        "v2_multilens_direction_ko": "상승",
                        "four_ai_agents": [
                            {
                                "label_ko": "소양",
                                "direction_ko": "상승",
                                "score": 0.58,
                                "channels": [{"channel": "session_myeongni", "direction": "bull", "weight": 0.3}],
                            }
                        ],
                        "absolute_balance": {
                            "conflict_score": 0.41,
                            "agent_vote_split": {"bull": 3, "neutral": 1, "bear": 0},
                            "channel_consensus": {"direction_ko": "상승"},
                            "agent_mean_score": 0.64,
                        },
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    text = tg.build_digest_afternoon(tmp_path)
    assert "MKM 오후 브리핑" in text
    assert "지휘관 사주" in text
    assert "계축" in text
    assert f"코스피 {cal_kst}" in text
    assert "상승" in text
    assert "렌즈 채널" in text
    assert "4AI 코어" in text


def test_morning_blocks_evening_review_style(monkeypatch) -> None:
    monkeypatch.setenv("MKM_TELEGRAM_MORNING_KOSPI_ONLY", "1")
    monkeypatch.setattr(tg, "_morning_kospi_only_window", lambda: True)
    assert tg._resolve_style("evening_review") == "evening_review"


def test_fortune_lines_for_prophecy_morning_strips_world_pulse() -> None:
    raw = [
        "",
        "▸ 개인 일운 (명리)",
        "  일운 병진",
        "▸ 오늘 라이프 [가설]",
        "  점심: 닭곰탕",
        "▸ 성경 앵커 (Logos) [NON_GATING][가설]",
        "  앵커: 열왕기상 18:38",
        "",
        "▸ 찰나의 나라 (세상×나) [가설]",
        "  코스피·장면: WATCH",
        "▸ 오늘 초론 스트림 [가설]",
    ]
    kept = tg._fortune_lines_for_prophecy_morning(raw)
    text = "\n".join(kept)
    assert "개인 일운" in text
    assert "닭곰탕" in text
    assert "성경 앵커" in text
    assert "찰나의 나라" not in text
    assert "초론 스트림" not in text


def test_build_digest_prophecy_includes_filtered_fortune(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("MKM_TELEGRAM_PROPHECY_INCLUDE_FORTUNE", "1")
    art = tmp_path / "docs" / "final" / "artifacts"
    art.mkdir(parents=True, exist_ok=True)
    for name, payload in (
        ("internal_kospi_morning_brief_onepager_latest.json", {"today_action": "WATCH", "confidence_0_100": 42}),
        ("trackc_prophecy_dual_leg_brief_latest.json", {"legs": {"kospi": {"n_evaluated": 5, "price_directional_hit_rate": 0.4}}}),
        ("btrack_hypothesis_prophecy_latest.json", {"prediction": {"instrument": "KOSPI", "direction": "bull", "confidence": 0.6}}),
        ("prophecy_hit_rate_eval_latest.json", {"metrics": {"price_directional_hit_rate": 0.4, "n_evaluated": 5}}),
    ):
        (art / name).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    fortune = {
        "schema": "commander_daily_fortune_v1_1",
        "myeongni_lines": ["일운 병진 · 일간 경"],
        "mkm_ai_lines": ["▸ 태양 AI: 결단"],
        "lifestyle_concierge": {
            "telegram_append_lines": ["", "▸ 오늘 라이프 [가설]", "  점심: 닭곰탕"],
        },
        "telegram_append_lines": [
            "",
            "▸ 개인 일운 (명리)",
            "  일운 병진 · 일간 경",
            "▸ 찰나의 나라 (세상×나) [가설]",
            "  코스피·장면: WATCH",
        ],
    }
    (tmp_path / "reports").mkdir(parents=True, exist_ok=True)
    (tmp_path / "reports" / "commander_daily_fortune_latest.json").write_text(
        json.dumps(fortune, ensure_ascii=False), encoding="utf-8"
    )
    text = tg.build_digest_prophecy(tmp_path)
    assert "MKM 장전 예언 브리핑" in text
    assert "일운 병진" in text
    assert "닭곰탕" in text
    assert "찰나의 나라" not in text


def test_build_digest_prophecy_kospi_only_omits_btc(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("MKM_TELEGRAM_MORNING_KOSPI_ONLY", "1")
    art = tmp_path / "docs" / "final" / "artifacts"
    art.mkdir(parents=True, exist_ok=True)
    (art / "internal_kospi_morning_brief_onepager_latest.json").write_text(
        json.dumps({"today_action": "HOLD", "confidence_0_100": 40}, ensure_ascii=False),
        encoding="utf-8",
    )
    (art / "trackc_prophecy_dual_leg_brief_latest.json").write_text(
        json.dumps(
            {
                "legs": {
                    "kospi": {"n_evaluated": 10, "price_directional_hit_rate": 0.5},
                    "btc": {"n_evaluated": 30, "price_directional_hit_rate": 0.667},
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (art / "btrack_hypothesis_prophecy_latest.json").write_text(
        json.dumps({"prediction": {"instrument": "BTC", "direction": "bear", "confidence": 0.9}}, ensure_ascii=False),
        encoding="utf-8",
    )
    (art / "prophecy_hit_rate_eval_latest.json").write_text(
        json.dumps({"metrics": {"price_directional_hit_rate": 0.63, "n_evaluated": 30}}, ensure_ascii=False),
        encoding="utf-8",
    )
    text = tg.build_digest_prophecy(tmp_path)
    assert "코스피" in text
    assert "비트코인" not in text
    assert "통합" not in text
    assert "B트랙 가격 가설" not in text


def test_build_digest_prophecy_slim_under_twelve_lines(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("MKM_TELEGRAM_PROPHECY_SLIM", "1")
    monkeypatch.setenv("MKM_TELEGRAM_PROPHECY_INCLUDE_FORTUNE", "0")
    art = tmp_path / "docs" / "final" / "artifacts"
    art.mkdir(parents=True, exist_ok=True)
    (art / "internal_kospi_morning_brief_onepager_latest.json").write_text(
        json.dumps(
            {
                "today_action": "GO_CONDITIONAL",
                "confidence_0_100": 82,
                "market_session_ko": "개장일",
                "dual_leg_kospi_n_evaluated": 30,
                "dual_leg_kospi_hit_rate": 0.533333,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (art / "trackc_prophecy_dual_leg_brief_latest.json").write_text("{}", encoding="utf-8")
    (art / "btrack_hypothesis_prophecy_latest.json").write_text(
        json.dumps({"prediction": {"instrument": "kospi", "direction": "bull", "confidence": 0.71}}, ensure_ascii=False),
        encoding="utf-8",
    )
    (art / "prophecy_hit_rate_eval_latest.json").write_text("{}", encoding="utf-8")
    text = tg.build_digest_prophecy_slim(tmp_path)
    assert "MKM 장전 코스피" in text
    assert "조건부실행" in text
    assert "일운" not in text
    assert "4AI" not in text
    assert "미션C" not in text
    assert len([ln for ln in text.splitlines() if ln.strip()]) <= 10
