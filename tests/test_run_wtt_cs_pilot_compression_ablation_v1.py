"""run_wtt_cs_pilot_compression_ablation_v1 — role prefix strip helper."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.run_wtt_cs_pilot_compression_ablation_v1 import strip_role_prefixes_from_text


def test_strip_role_prefixes_from_text() -> None:
    raw = "[user] hello [assistant] hi there [user] bye"
    assert strip_role_prefixes_from_text(raw) == "hello hi there bye"
