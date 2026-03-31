import os
import json
from pathlib import Path

from scripts.send_fact_safe_broadcast_to_slack import _load_env_from_dotenv, build_slack_text, main


def test_load_env_from_dotenv_sets_missing_keys(tmp_path: Path):
    dotenv = tmp_path / ".env"
    dotenv.write_text("FACT_SAFE_SLACK_WEBHOOK_URL=https://example.invalid/webhook\n", encoding="utf-8")
    os.environ.pop("FACT_SAFE_SLACK_WEBHOOK_URL", None)
    _load_env_from_dotenv(dotenv)
    assert os.environ.get("FACT_SAFE_SLACK_WEBHOOK_URL") == "https://example.invalid/webhook"


def test_load_env_from_dotenv_keeps_existing_value(tmp_path: Path):
    dotenv = tmp_path / ".env"
    dotenv.write_text("FACT_SAFE_SLACK_WEBHOOK_URL=https://new.invalid/webhook\n", encoding="utf-8")
    os.environ["FACT_SAFE_SLACK_WEBHOOK_URL"] = "https://keep.invalid/webhook"
    _load_env_from_dotenv(dotenv)
    assert os.environ.get("FACT_SAFE_SLACK_WEBHOOK_URL") == "https://keep.invalid/webhook"


def test_build_slack_text_contains_core_fields():
    text = build_slack_text(
        {
            "ts_utc": "2026-03-31T00:00:00Z",
            "next_month_risk_hint": "4월 선행 리스크: 압박/방어 구간",
            "price_output_locked": True,
            "lock_reason": "low_or_hold_mode_price_output_forbidden",
            "reliability_badge": "LOW",
            "high_reliability_decision": "HOLD",
            "gate_reason": "low_badge_forced_hold",
            "core_score": 0.25,
            "core_decision": "HOLD",
            "core_reason": "score_inside_locked_band",
            "k_shield_candidate_name": "k_shield_h1_soft",
            "k_shield_candidate_max_drawdown_pct": 8.285629,
            "net": "1.23",
            "net_source": "kpi_history_fallback",
            "history_samples": "1",
            "history_net_delta": "0.0",
            "overlap_drift_alert": False,
            "overlap_drift_alert_threshold": -0.05,
        }
    )
    assert "Fact-Safe Monthly Broadcast" in text
    assert "LOCKED_MODE" in text
    assert "next_month_risk_hint: 4월 선행 리스크: 압박/방어 구간" in text
    assert "reliability_badge: LOW" in text
    assert "core_decision: HOLD" in text
    assert "k_shield_candidate: k_shield_h1_soft" in text
    assert "net_source: kpi_history_fallback" in text
    assert "NET_SOURCE_FALLBACK_ACTIVE" in text


def test_build_slack_text_shows_escalation_when_streak_high():
    text = build_slack_text(
        {
            "price_output_locked": False,
            "net_source": "kpi_history_fallback",
            "net_source_fallback_streak": 4,
            "net_source_fallback_escalated": True,
        }
    )
    assert "NET_SOURCE_FALLBACK_STREAK=4" in text


def test_load_env_from_dotenv_strips_inline_comment_and_quotes(tmp_path: Path):
    dotenv = tmp_path / ".env"
    dotenv.write_text('FACT_SAFE_SLACK_WEBHOOK_URL="https://quoted.invalid/hook" # comment\n', encoding="utf-8")
    os.environ.pop("FACT_SAFE_SLACK_WEBHOOK_URL", None)
    _load_env_from_dotenv(dotenv)
    assert os.environ.get("FACT_SAFE_SLACK_WEBHOOK_URL") == "https://quoted.invalid/hook"


def test_main_writes_status_when_payload_missing(tmp_path: Path, monkeypatch):
    missing = tmp_path / "missing.json"
    status = tmp_path / "status.json"
    status_log = tmp_path / "status_log.jsonl"
    monkeypatch.setattr(
        "sys.argv",
        ["prog", "--input", str(missing), "--status-out", str(status), "--status-log-out", str(status_log)],
    )
    rc = main()
    assert rc == 0
    doc = json.loads(status.read_text(encoding="utf-8"))
    assert doc["status"] == "skipped"
    assert doc["reason"] == "invalid_or_missing_payload"
    lines = [x for x in status_log.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(lines) == 1
    logged = json.loads(lines[0])
    assert logged["reason"] == "invalid_or_missing_payload"


def test_main_dry_run_persists_k_shield_status_fields(tmp_path: Path, monkeypatch):
    payload = tmp_path / "payload.json"
    payload.write_text(
        json.dumps(
            {
                "ts_utc": "2026-03-31T00:00:00Z",
                "price_output_locked": True,
                "lock_reason": "low_or_hold_mode_price_output_forbidden",
                "reliability_badge": "MID",
                "high_reliability_decision": "PASS",
                "gate_reason": "monthly_check_gate",
                "core_score": 0.0,
                "core_decision": "HOLD",
                "core_reason": "score_inside_locked_band",
                "k_shield_candidate_name": "k_shield_h1_soft",
                "k_shield_candidate_max_drawdown_pct": 8.285629,
                "net": "-2.8",
                "net_source": "exchange_snapshot_24h",
                "history_samples": "28",
                "history_net_delta": "-24.2",
                "overlap_drift_alert": False,
                "overlap_drift_alert_threshold": -0.05,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    status = tmp_path / "status.json"
    status_log = tmp_path / "status_log.jsonl"
    monkeypatch.setattr(
        "sys.argv",
        [
            "prog",
            "--input",
            str(payload),
            "--status-out",
            str(status),
            "--status-log-out",
            str(status_log),
            "--dry-run",
        ],
    )
    rc = main()
    assert rc == 0
    doc = json.loads(status.read_text(encoding="utf-8"))
    assert doc["status"] == "skipped"
    assert doc["reason"] == "dry_run"
    assert doc["k_shield_candidate_name"] == "k_shield_h1_soft"
    assert doc["k_shield_candidate_max_drawdown_pct"] == 8.285629
