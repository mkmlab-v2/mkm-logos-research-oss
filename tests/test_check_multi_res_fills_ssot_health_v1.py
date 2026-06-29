"""SSOT health guard smoke ([HYPO])."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from check_multi_res_fills_ssot_health_v1 import build_health  # noqa: E402


def test_live_ssot_health_ok_when_primary_populated() -> None:
    doc = build_health()
    if (ROOT / "projects/bitcoin-trading/exports/cursor_trade_history/trades_treatment.json").is_file():
        primary = json.loads(
            (
                ROOT / "projects/bitcoin-trading/exports/cursor_trade_history/trades_treatment.json"
            ).read_text(encoding="utf-8")
        )
        if isinstance(primary, list) and len(primary) > 0:
            assert doc["ok"] is True, doc.get("issues")
