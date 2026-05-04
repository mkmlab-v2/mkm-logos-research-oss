"""TP/SL offset + trigger validation (no API keys, no network)."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SRC = _ROOT / "projects" / "bitcoin-trading" / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from api.binance_client import compute_offset_stop_prices, validate_protective_triggers  # noqa: E402


def test_long_offsets() -> None:
    sl, tp = compute_offset_stop_prices(entry=100_000.0, position_side="LONG", sl_pct=1.0, tp_pct=2.0)
    assert sl == 99_000.0
    assert tp == 102_000.0


def test_short_offsets() -> None:
    sl, tp = compute_offset_stop_prices(entry=100_000.0, position_side="SHORT", sl_pct=1.0, tp_pct=2.0)
    assert sl == 101_000.0
    assert tp == 98_000.0


def test_validate_long_ok() -> None:
    assert validate_protective_triggers(position_side="LONG", mark=100_000.0, sl_px=99_000.0, tp_px=102_000.0) is None


def test_validate_long_sl_above_mark() -> None:
    err = validate_protective_triggers(position_side="LONG", mark=100_000.0, sl_px=100_001.0, tp_px=102_000.0)
    assert err and "below mark" in err


def test_validate_short_ok() -> None:
    assert validate_protective_triggers(position_side="SHORT", mark=100_000.0, sl_px=101_000.0, tp_px=98_000.0) is None
