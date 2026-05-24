# @MKM12-METADATA
# Type: Logic
# Purpose: O-P22 coordinator lens conflict observation gate (no live trading side effects).

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_CHECKER = _ROOT / "scripts" / "check_coordinator_lens_conflict_observation_v1.py"


def _minimal_stub(
    *,
    conflict_count: int = 0,
    veto: bool = False,
    ts_utc: str | None = None,
) -> dict:
    now = datetime.now(timezone.utc)
    ts = ts_utc or now.strftime("%Y-%m-%dT%H:%M:%SZ")
    fresh = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    market_row: dict = {
        "lens_id": "market_sasang",
        "available": True,
        "direction_score": 0.1,
        "confidence": 0.5,
        "direction_sign": "bull",
        "artifact_ts_utc": fresh,
    }
    if veto:
        market_row["market_sasang_lens_v1"] = {
            "veto_force_hold": True,
            "veto_reason_codes": ["HIGH_ENTROPY_SOFTMAX"],
        }
    return {
        "schema": "independent_lens_fusion_stub_v0",
        "version": "0.3.0",
        "ts_utc": ts,
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "mode": "observation_only",
        "inputs": [
            {
                "lens_id": "myeongni",
                "available": True,
                "direction_score": 0.1,
                "confidence": 0.7,
                "direction_sign": "bull",
                "artifact_ts_utc": fresh,
            },
            {
                "lens_id": "sasang",
                "available": True,
                "direction_score": 0.1,
                "confidence": 0.7,
                "direction_sign": "bull",
                "artifact_ts_utc": fresh,
            },
            {
                "lens_id": "logos",
                "available": True,
                "direction_score": -0.2,
                "confidence": 0.2,
                "direction_sign": "bear",
                "artifact_ts_utc": fresh,
            },
            market_row,
        ],
        "consensus": {
            "available_count": 4,
            "agreement_rate": 0.75 if conflict_count else 1.0,
            "conflict_count": conflict_count,
            "consensus_sign": "bull",
            "consensus_score": 0.05,
            "consensus_confidence": 0.4,
        },
        "conflict_summary": {
            "conflict_narrative_guarded": "Lens direction alignment test narrative.",
            "minority_lens_ids": ["logos"] if conflict_count else [],
            "majority_sign": "bull",
            "logos_evidence_verse_ids": ["v-1"] if conflict_count else [],
            "narrative_policy": "template_only",
        },
    }


def _run(
    tmp_path: Path,
    stub: dict | None = None,
    *,
    missing_stub: bool = False,
    extra_args: list[str] | None = None,
) -> subprocess.CompletedProcess[str]:
    stub_path = tmp_path / "fusion.json"
    out_path = tmp_path / "observation.json"
    dedup_path = tmp_path / "dedup.json"
    if not missing_stub and stub is not None:
        stub_path.write_text(json.dumps(stub, ensure_ascii=False), encoding="utf-8")
    args = [
        sys.executable,
        str(_CHECKER),
        "--workspace-root",
        str(tmp_path),
        "--fusion-stub-json",
        str(stub_path),
        "--out-json",
        str(out_path),
        "--dedup-state-json",
        str(dedup_path),
        "--skip-webhook",
    ]
    if extra_args:
        args.extend(extra_args)
    return subprocess.run(
        args,
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_missing_stub_exit_1(tmp_path: Path) -> None:
    cp = _run(tmp_path, stub=_minimal_stub(), missing_stub=True)
    assert cp.returncode == 1


def test_consensus_exit_0_no_webhook_trigger(tmp_path: Path) -> None:
    cp = _run(tmp_path, _minimal_stub(conflict_count=0, veto=False))
    assert cp.returncode == 0, cp.stderr
    out = json.loads((tmp_path / "observation.json").read_text(encoding="utf-8"))
    assert out["status"] == "CONSENSUS"
    assert out["webhook"]["status"] == "skipped_no_trigger"


def test_conflict_exit_0_observation_only(tmp_path: Path) -> None:
    cp = _run(tmp_path, _minimal_stub(conflict_count=1))
    assert cp.returncode == 0, cp.stderr
    out = json.loads((tmp_path / "observation.json").read_text(encoding="utf-8"))
    assert out["status"] in ("CONFLICT_NO_WEBHOOK", "CONFLICT_DUPLICATE_GUARDED", "ALERT_FIRED")
    assert out["conflict_active"] is True


def test_veto_only_exit_0(tmp_path: Path) -> None:
    cp = _run(tmp_path, _minimal_stub(conflict_count=0, veto=True))
    assert cp.returncode == 0, cp.stderr
    out = json.loads((tmp_path / "observation.json").read_text(encoding="utf-8"))
    assert out["market_sasang_veto"]["veto_force_hold"] is True
    assert out["status"] != "CONSENSUS"


def test_stale_stub_skips_webhook(tmp_path: Path) -> None:
    old = (datetime.now(timezone.utc) - timedelta(hours=48)).strftime("%Y-%m-%dT%H:%M:%SZ")
    cp = _run(tmp_path, _minimal_stub(conflict_count=1, ts_utc=old))
    assert cp.returncode == 0, cp.stderr
    out = json.loads((tmp_path / "observation.json").read_text(encoding="utf-8"))
    assert out["status"] == "STALE"
    assert out["stale_inputs"] is True
    assert out["webhook"]["status"] == "skipped_stale_inputs"


def test_dedup_blocks_second_fire(tmp_path: Path) -> None:
    stub = _minimal_stub(conflict_count=1)
    dedup_path = tmp_path / "dedup.json"
    dedup_path.write_text(
        json.dumps(
            {
                "schema": "coordinator_lens_conflict_dedup_state_v1",
                "last_fingerprint": "placeholder",
                "last_fired_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
        ),
        encoding="utf-8",
    )
    # First run to compute real fingerprint
    cp1 = _run(tmp_path, stub)
    assert cp1.returncode == 0
    out1 = json.loads((tmp_path / "observation.json").read_text(encoding="utf-8"))
    fp = out1["alert_fingerprint"]
    dedup_path.write_text(
        json.dumps(
            {
                "schema": "coordinator_lens_conflict_dedup_state_v1",
                "last_fingerprint": fp,
                "last_fired_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
        ),
        encoding="utf-8",
    )
    cp2 = _run(tmp_path, stub)
    assert cp2.returncode == 0
    out2 = json.loads((tmp_path / "observation.json").read_text(encoding="utf-8"))
    assert out2["status"] == "CONFLICT_DUPLICATE_GUARDED"
    assert out2["webhook"]["status"] == "skipped_dedup_guard"


def test_bad_schema_exit_1(tmp_path: Path) -> None:
    bad = _minimal_stub(conflict_count=1)
    bad["schema"] = "wrong_schema"
    cp = _run(tmp_path, bad)
    assert cp.returncode == 1
