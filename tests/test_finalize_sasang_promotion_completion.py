from __future__ import annotations

import json
from pathlib import Path

from scripts import finalize_sasang_promotion_completion as mod


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_finalize_completion_when_ready_and_authorized(tmp_path: Path, monkeypatch) -> None:
    auth = tmp_path / "auth.json"
    ready = tmp_path / "ready.json"
    out = tmp_path / "completion.json"
    _write(auth, {"promotion_to_a_track_allowed": True})
    _write(ready, {"decision": "READY", "go_no_go": {"go": True}})

    monkeypatch.setattr(
        "sys.argv",
        [
            "finalize_sasang_promotion_completion.py",
            "--authorization",
            str(auth),
            "--ready",
            str(ready),
            "--out",
            str(out),
        ],
    )
    assert mod.main() == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["promotion_completed"] is True
