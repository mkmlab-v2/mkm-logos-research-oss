from __future__ import annotations

import json
from pathlib import Path

from scripts import authorize_sasang_promotion_to_atrack as mod


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_authorize_promotion_passes_when_all_checks_true(tmp_path: Path, monkeypatch) -> None:
    ready = tmp_path / "ready.json"
    signoff = tmp_path / "signoff.json"
    drift = tmp_path / "drift.json"
    out = tmp_path / "auth.json"

    _write(ready, {"decision": "READY", "go_no_go": {"go": True}})
    _write(signoff, {"decision": "APPROVED"})
    _write(drift, {"drift_detected": False})

    monkeypatch.setattr(
        "sys.argv",
        [
            "authorize_sasang_promotion_to_atrack.py",
            "--ready",
            str(ready),
            "--signoff",
            str(signoff),
            "--drift",
            str(drift),
            "--out",
            str(out),
        ],
    )
    assert mod.main() == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["promotion_to_a_track_allowed"] is True
