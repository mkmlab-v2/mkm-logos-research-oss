from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_build_lens_penalty_s1_shadow_streak_gate_v1(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    script = repo / "scripts" / "build_lens_penalty_s1_shadow_streak_gate_v1.py"
    history = tmp_path / "history.jsonl"
    out = tmp_path / "streak.json"

    rows = [
        {"decision": "HOLD"},
        {"decision": "GO_REVIEW"},
        {"decision": "GO_REVIEW"},
        {"decision": "GO_REVIEW"},
    ]
    history.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")

    subprocess.run(
        [sys.executable, str(script), "--history-jsonl", str(history), "--required-streak", "3", "--out", str(out)],
        check=True,
        cwd=repo,
    )

    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["decision"] == "READY_FOR_COMMANDER_REVIEW"
    assert payload["snapshot"]["current_go_streak"] == 3
