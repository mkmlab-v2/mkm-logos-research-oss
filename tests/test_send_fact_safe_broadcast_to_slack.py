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
            "reliability_badge": "LOW",
            "high_reliability_decision": "HOLD",
            "gate_reason": "low_badge_forced_hold",
            "net": "1.23",
            "history_samples": "1",
            "history_net_delta": "0.0",
            "overlap_drift_alert": False,
            "overlap_drift_alert_threshold": -0.05,
        }
    )
    assert "Fact-Safe Monthly Broadcast" in text
    assert "next_month_risk_hint: 4월 선행 리스크: 압박/방어 구간" in text
    assert "reliability_badge: LOW" in text


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
from scripts.send_fact_safe_broadcast_to_slack import build_slack_text


def test_build_slack_text_contains_core_fields():
    payload = {
        "ts_utc": "2026-03-31T05:34:07Z",
        "reliability_badge": "LOW",
        "high_reliability_decision": "HOLD",
        "gate_reason": "low_badge_forced_hold",
        "net": "21.41",
        "history_samples": "12",
        "history_net_delta": "-0.3",
        "overlap_drift_alert": False,
        "overlap_drift_alert_threshold": -0.05,
    }
    text = build_slack_text(payload)
    assert "Fact-Safe Monthly Broadcast" in text
    assert "reliability_badge: LOW" in text
    assert "high_reliability_decision: HOLD" in text
    assert "gate_reason: low_badge_forced_hold" in text
