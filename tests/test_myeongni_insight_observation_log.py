# @MKM12-METADATA
# Type: Logic
# Purpose: B-track insight JSONL contract (MYEONGRI_INSIGHT_SSOT.md §2).
# Keywords: myeongni, insight, jsonl

"""Validate insight_observation_log.sample.jsonl and insight_observation_log.jsonl lines."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_SAMPLE = _ROOT / "data" / "myeongni" / "insight_observation_log.sample.jsonl"
_LOG = _ROOT / "data" / "myeongni" / "insight_observation_log.jsonl"


def _iter_jsonl(path: Path):
    text = path.read_text(encoding="utf-8")
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        yield json.loads(line)


def _validate_row(obj: dict, *, label: str) -> None:
    assert obj.get("hypothesis_tier") == "B", f"{label}: hypothesis_tier must be B"
    assert obj.get("boundary_ack") is True, f"{label}: boundary_ack must be true"
    for k in ("inputs_summary", "insight_one_liner", "falsification_hook"):
        assert isinstance(obj.get(k), str) and str(obj[k]).strip(), f"{label}: {k} required"
    cf = obj.get("confidence")
    assert cf is None or (isinstance(cf, (int, float)) and 0.0 <= float(cf) <= 1.0), (
        f"{label}: confidence"
    )
    ts = obj.get("ts_utc")
    assert isinstance(ts, str) and ts.strip(), f"{label}: ts_utc"
    datetime.fromisoformat(ts.replace("Z", "+00:00"))  # parse check


@pytest.mark.parametrize("path", [_SAMPLE, _LOG])
def test_insight_observation_jsonl_contract(path: Path) -> None:
    if not path.is_file():
        pytest.skip(f"optional insight log missing in this environment: {path}")
    rows = list(_iter_jsonl(path))
    assert len(rows) >= 1, path
    for i, obj in enumerate(rows):
        _validate_row(obj, label=f"{path.name}[{i}]")


def test_fusion_interface_stub_json() -> None:
    stub = _ROOT / "docs" / "final" / "MYEONGNI_FUSION_INTERFACE_STUB.json"
    assert stub.is_file()
    doc = json.loads(stub.read_text(encoding="utf-8"))
    assert doc.get("schema") == "myeongni_fusion_interface_stub_v1"
    assert "myeongri_stream_outputs" in doc
    assert "fusion_stream_expectations" in doc
    if "manseryeok_provenance" in doc:
        assert isinstance(doc["manseryeok_provenance"], dict)
