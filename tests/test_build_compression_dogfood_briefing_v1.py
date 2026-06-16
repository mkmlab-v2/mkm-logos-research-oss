from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/build_compression_dogfood_briefing_v1.py"
OUT = ROOT / "docs/final/artifacts/compression_dogfood_briefing_v1_latest.json"


def test_build_compression_dogfood_briefing_exit0() -> None:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert OUT.is_file()

    doc = json.loads(OUT.read_text(encoding="utf-8-sig"))
    assert doc["schema"] == "compression_dogfood_briefing_v1"
    assert doc["latest_tenant_id"] == "mkm-internal-dogfood-v4-cursor"
    assert "v4_cursor_transcript_pack" in doc
    assert "one_click_latest" in doc
    assert "mkm-internal-dogfood-v4-cursor" in doc["one_click_latest"]

    v4 = doc["v4_cursor_transcript_pack"]
    assert v4["tenant_id"] == "mkm-internal-dogfood-v4-cursor"
    assert v4["measured_proxy"]["raw"]["rows"] >= 20
    assert v4["measured_proxy"]["delta_repair_v2_minus_raw"] == 0.0

