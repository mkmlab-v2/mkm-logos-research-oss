from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_build_lens_penalty_auto_apply_guardrail_v1_rollback_on_consecutive_worsening(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    script = repo / "scripts" / "build_lens_penalty_auto_apply_guardrail_v1.py"
    daily = tmp_path / "daily.json"
    weekly = tmp_path / "weekly.json"
    history = tmp_path / "history.jsonl"
    out = tmp_path / "guardrail.json"

    daily.write_text(json.dumps({"mode": "apply", "applied": True, "summary": {"recommendations_with_penalty": 2}}), encoding="utf-8")
    weekly.write_text(json.dumps({"summary": {"strict_gap": 0.40}}), encoding="utf-8")
    history.write_text(
        json.dumps({"strict_gap": 0.30, "gap_worsening": True}) + "\n",
        encoding="utf-8",
    )

    subprocess.run(
        [
            sys.executable,
            str(script),
            "--daily-json",
            str(daily),
            "--weekly-json",
            str(weekly),
            "--history-jsonl",
            str(history),
            "--out",
            str(out),
        ],
        check=True,
        cwd=repo,
    )

    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["decision"] == "ROLLBACK_REQUIRED"
    assert payload["should_rollback"] is True
