from __future__ import annotations

import json
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_FIXTURE = _ROOT / "docs" / "final" / "artifacts" / "fixtures" / "log_metabolism_smoke_v1.jsonl"
_CONFIG = _ROOT / "docs" / "final" / "artifacts" / "inference_config_v1.json"


@pytest.mark.skipif(not _FIXTURE.is_file(), reason="fixture jsonl missing")
def test_aggregate_fixture_smoke() -> None:
    from scripts.aggregate_log_metabolism_from_jsonl import _load_json, aggregate_rows

    cfg = _load_json(_CONFIG) if _CONFIG.is_file() else {}
    mj = cfg.get("metabolism_jsonl") or {}
    pk = mj.get("primary_keys") or {}
    al = mj.get("aliases") or {}
    th = cfg.get("metabolism_thresholds") or {}

    rows = []
    with _FIXTURE.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))

    s = aggregate_rows(
        rows,
        egress_key=str(pk.get("egress_pressure") or "egress_pressure"),
        throttle_key=str(pk.get("throttle_events") or "throttle_events"),
        egress_aliases=[str(x) for x in (al.get("egress_pressure") or [])],
        throttle_aliases=[str(x) for x in (al.get("throttle_events") or [])],
        high_egress=float(th.get("high_egress", 0.75)),
        high_persistence=float(th.get("high_persistence", 0.75)),
    )
    assert s["row_count_valid"] == 3
    assert abs(s["egress_pressure"]["mean"] - (120 + 400 + 95) / 3.0) < 1e-6
