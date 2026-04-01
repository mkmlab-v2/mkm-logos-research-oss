from __future__ import annotations

import json
from pathlib import Path

from scripts import report_slack_advisory_history as mod


def test_slack_advisory_history_report(tmp_path: Path, monkeypatch) -> None:
    log = tmp_path / "fact_safe_slack_delivery_log.jsonl"
    rows = [
        {
            "ts_utc": "2026-04-01T00:00:00Z",
            "sent": True,
            "dry_run": False,
            "net_source_fallback_alert": False,
            "dual_regime_state_advisory": {"decision": "state_clamp_stable"},
            "auto_hold_override_advisory": {"decision": "override_mix_balanced"},
            "auto_hold_override_advisory_decision": "override_mix_balanced",
        },
        {
            "ts_utc": "2026-04-01T01:00:00Z",
            "sent": False,
            "dry_run": True,
            "net_source_fallback_alert": True,
            "dual_regime_state_advisory": {"decision": "state_signal_not_wired"},
            "auto_hold_override_advisory": {"decision": "override_skew_net_source_fallback"},
            "auto_hold_override_advisory_decision": "override_skew_net_source_fallback",
        },
    ]
    log.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    out = tmp_path / "slack_advisory_history_latest.json"

    monkeypatch.setattr(
        "sys.argv",
        [
            "prog",
            "--log",
            str(log),
            "--output",
            str(out),
            "--days",
            "3650",
        ],
    )
    rc = mod.main()
    assert rc == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["rows_total"] == 2
    assert doc["rows_in_window"] == 2
    assert doc["sent_count"] == 1
    assert doc["dry_run_count"] == 1
    assert doc["net_source_fallback_alert_count"] == 1
    assert doc["dual_regime_state_advisory_decision_counts"]["state_clamp_stable"] == 1
    assert doc["auto_hold_override_advisory_decision_counts"]["override_mix_balanced"] == 1
    assert doc["auto_hold_override_advisory_decision_key_counts"]["override_skew_net_source_fallback"] == 1

