from __future__ import annotations

import json
from pathlib import Path

from scripts import emit_sasang_supplemental_trend_alert as mod


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_emit_alert_when_trend_alert_true(tmp_path: Path, monkeypatch) -> None:
    trend = tmp_path / "trend.json"
    out = tmp_path / "alert.json"
    _write(trend, {"trend_status": "DOWN", "delta": -0.12, "alert": True})

    monkeypatch.setattr(
        "sys.argv",
        [
            "emit_sasang_supplemental_trend_alert.py",
            "--trend",
            str(trend),
            "--out",
            str(out),
        ],
    )

    assert mod.main() == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["non_gating_policy"] is True
    assert doc["notify_operator"] is True
    assert doc["severity"] == "warn"
