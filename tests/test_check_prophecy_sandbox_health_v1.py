from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_health_ok_when_artifacts_present(tmp_path: Path) -> None:
    spec = importlib.util.spec_from_file_location(
        "check_prophecy_sandbox_health_v1",
        ROOT / "scripts/check_prophecy_sandbox_health_v1.py",
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)

    stream = tmp_path / "stream.jsonl"
    stream.write_text(
        json.dumps({"hypothesis_tier": "SANDBOX", "target_id": "x", "ok": True}) + "\n",
        encoding="utf-8",
    )
    panel = {
        "targets": [{"target_id": "x", "ok": True}],
        "n_ok": 1,
    }
    chain = {"ok": True, "n_ok": 1, "n_targets": 1}
    bridge = {
        "status": "DRAFT_BRIDGE_ONLY",
        "runtime_constraints": {"prod_score_mutation": False},
        "n_total_draft_rows": 0,
    }
    rollup = {"targets": [{"target_id": "x", "n_calendar_days": 2}]}
    prod = tmp_path / "score.json"
    prod.write_text("{}", encoding="utf-8")

    artifacts_verify = {"ok": True, "n_missing": 0, "n_bad_schema": 0}

    doc = mod.build_health(
        chain=chain,
        chain_path="reports/sandbox_prophecy_daily_chain_v1_latest.json",
        panel=panel,
        stream_path=stream,
        bridge=bridge,
        rollup=rollup,
        prod_score_path=prod,
        artifacts_verify=artifacts_verify,
        strict=False,
    )
    assert doc["ok"] is True
    assert doc["checks"]["rollup_progress"]["max_n_calendar_days"] == 2

    doc_strict = mod.build_health(
        chain=chain,
        chain_path="reports/sandbox_prophecy_daily_chain_v1_latest.json",
        panel=panel,
        stream_path=stream,
        bridge=bridge,
        rollup=rollup,
        prod_score_path=prod,
        artifacts_verify=artifacts_verify,
        strict=True,
    )
    assert doc_strict["ok"] is False


def test_lib_finalize_stream_row() -> None:
    spec = importlib.util.spec_from_file_location(
        "sandbox_prophecy_lib_v1",
        ROOT / "scripts/sandbox_prophecy_lib_v1.py",
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    row = mod.finalize_stream_row({"generated_at_utc": "2026-05-18T12:00:00Z"})
    assert row["snapshot_calendar_date_utc"] == "2026-05-18"
