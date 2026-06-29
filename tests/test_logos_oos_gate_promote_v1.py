"""Logos OOS gate promote."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from logos_oos_gate_promote_v1 import promote_best_logos_oos_gate  # noqa: E402


def test_promote_picks_highest_hit_go(tmp_path: Path) -> None:
    art = tmp_path / "artifacts"
    art.mkdir(parents=True)
    (art / "prophecy_logos_revalidation_oos_gate_120d_latest.json").write_text(
        json.dumps(
            {
                "gate": {"go": True},
                "oos_metrics": {"directional_hit_rate_active": 0.52},
            }
        ),
        encoding="utf-8",
    )
    (art / "prophecy_logos_revalidation_oos_gate_252d_latest.json").write_text(
        json.dumps(
            {
                "gate": {"go": True},
                "oos_metrics": {"directional_hit_rate_active": 0.534884},
            }
        ),
        encoding="utf-8",
    )
    doc = promote_best_logos_oos_gate(art)
    assert doc["promoted"] is True
    latest = json.loads((art / "prophecy_logos_revalidation_oos_gate_latest.json").read_text(encoding="utf-8"))
    assert latest["oos_metrics"]["directional_hit_rate_active"] == 0.534884
