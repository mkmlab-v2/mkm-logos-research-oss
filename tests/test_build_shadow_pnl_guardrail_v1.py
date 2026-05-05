from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_shadow_pnl_guardrail_v1.py"


def test_shadow_guardrail_build_basic(tmp_path: Path) -> None:
    readiness = tmp_path / "readiness.json"
    briefing = tmp_path / "briefing.json"
    out = tmp_path / "shadow.json"

    readiness.write_text(
        json.dumps(
            {
                "verification": {"judge_decision": "HOLD"},
            }
        ),
        encoding="utf-8",
    )
    briefing.write_text(
        json.dumps(
            {
                "market_snapshot": {"decision_state": "WATCH"},
                "action_frame": {"operator_action": "watch_tighten"},
            }
        ),
        encoding="utf-8",
    )

    cmd1 = [
        sys.executable,
        str(SCRIPT),
        "--workspace-root",
        str(tmp_path),
        "--readiness-json",
        "readiness.json",
        "--briefing-json",
        "briefing.json",
        "--out",
        "shadow.json",
        "--price-usd",
        "100",
        "--notional-usd",
        "1000",
    ]
    p1 = subprocess.run(cmd1, cwd=str(ROOT), capture_output=True, text=True, check=False)
    assert p1.returncode == 0, p1.stderr + p1.stdout

    cmd2 = cmd1.copy()
    cmd2[cmd2.index("--price-usd") + 1] = "90"
    p2 = subprocess.run(cmd2, cwd=str(ROOT), capture_output=True, text=True, check=False)
    assert p2.returncode == 0, p2.stderr + p2.stdout

    result = json.loads(out.read_text(encoding="utf-8"))
    assert result["schema"] == "shadow_pnl_guardrail_v1"
    assert result["state"]["guard_active"] is True
    assert result["impact"]["cumulative_avoided_loss_usd"] > 0

