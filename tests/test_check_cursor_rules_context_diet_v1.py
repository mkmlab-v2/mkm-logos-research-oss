# Purpose: cursor rules context diet audit contract.

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_context_diet_strict_passes() -> None:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/check_cursor_rules_context_diet_v1.py"), "--strict"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    doc = json.loads(
        (ROOT / "reports/cursor_rules_context_diet_v1_latest.json").read_text(encoding="utf-8")
    )
    assert doc["ok"] is True
    assert doc["always_apply_count"] == len(doc["core_always_apply_expected"])
    assert set(doc["always_apply_names"]) == set(doc["core_always_apply_expected"])
    inject = doc["inject_docs"]
    assert inject["agents_md_lines"] <= doc["budget"]["max_agents_md_lines"]
    assert inject["claude_md_lines"] <= doc["budget"]["max_claude_md_lines"]
    assert inject["cursorrules_lines"] <= doc["budget"]["max_cursorrules_lines"]
    assert inject["cursorrules_template_in_sync"] is True
