from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import jsonschema


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n"
    path.write_text(body, encoding="utf-8")


def test_run_lens_penalty_shadow_v1_penalty_recommendation(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    script = repo / "scripts" / "run_lens_penalty_shadow_v1.py"
    schema_path = repo / "docs" / "final" / "artifacts" / "schemas" / "lens_penalty_daily_v1.schema.json"

    events_jsonl = tmp_path / "events.jsonl"
    state_json = tmp_path / "state.json"
    policy_json = tmp_path / "policy.json"
    out_json = tmp_path / "out.json"

    _write_jsonl(
        events_jsonl,
        [
            {"lens_id": "myeongni", "result": "FAIL"},
            {"lens_id": "myeongni", "result": "FAIL"},
            {"lens_id": "myeongni", "result": "HIT"},
            {"lens_id": "sasang", "result": "HIT"},
            {"lens_id": "sasang", "result": "HIT"},
            {"lens_id": "sasang", "result": "HIT"},
        ],
    )
    _write_json(
        state_json,
        {
            "schema": "lens_penalty_shadow_state_v1",
            "updated_at_utc": "2026-05-07T00:00:00Z",
            "lens_state": {
                "myeongni": {"multiplier": 1.0, "cooldown_left": 0},
                "sasang": {"multiplier": 0.9, "cooldown_left": 0},
            },
        },
    )
    _write_json(
        policy_json,
        {
            "schema": "lens_penalty_policy_v1",
            "max_daily_penalty": 0.1,
            "penalty_step": 0.05,
            "recovery_step": 0.02,
            "min_multiplier": 0.5,
            "max_multiplier": 1.0,
            "fail_rate_trigger": 0.5,
            "lookback_rows": 50,
            "cooldown_events": 3,
        },
    )

    subprocess.run(
        [
            sys.executable,
            str(script),
            "--events-jsonl",
            str(events_jsonl),
            "--state-json",
            str(state_json),
            "--policy-json",
            str(policy_json),
            "--out",
            str(out_json),
        ],
        check=True,
        cwd=repo,
    )

    payload = json.loads(out_json.read_text(encoding="utf-8"))
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.validate(payload, schema)

    rec = {x["lens_id"]: x for x in payload["recommendations"]}
    assert payload["mode"] == "shadow"
    assert rec["myeongni"]["proposed_multiplier"] == 0.95
    assert rec["myeongni"]["delta"] == -0.05
    assert rec["sasang"]["proposed_multiplier"] == 0.92
    assert rec["sasang"]["delta"] == 0.02
