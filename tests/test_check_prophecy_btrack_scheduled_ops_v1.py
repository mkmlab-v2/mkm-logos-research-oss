"""Tests for scripts/check_prophecy_btrack_scheduled_ops_v1.py"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(workspace: Path, extra: list[str] | None = None) -> tuple[int, dict]:
    script = Path(__file__).resolve().parents[1] / "scripts" / "check_prophecy_btrack_scheduled_ops_v1.py"
    cmd = [
        sys.executable,
        str(script),
        "--workspace-root",
        str(workspace),
        "--skip-scheduled-tasks",
    ]
    if extra:
        cmd.extend(extra)
    p = subprocess.run(cmd, capture_output=True, text=True, check=False)
    out = workspace / "reports" / "prophecy_btrack_scheduled_ops_latest.json"
    data = json.loads(out.read_text(encoding="utf-8")) if out.is_file() else {}
    return p.returncode, data


def test_observe_mode_exit_zero_when_stale(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    art = root / "docs/final/artifacts"
    art.mkdir(parents=True)
    old = datetime.now(timezone.utc) - timedelta(hours=200)
    hit = {
        "schema": "prophecy_hit_rate_eval_report_v2",
        "generated_at_utc": _iso(old),
        "metrics": {"price_directional_hit_rate": 0.5},
    }
    (art / "prophecy_hit_rate_eval_latest.json").write_text(json.dumps(hit), encoding="utf-8")

    code, data = _run(root)
    assert code == 0
    assert data.get("overall_ok") is False
    assert any(c["id"] == "btrack_hit_rate_eval_fresh" and not c["ok"] for c in data["checks"])


def test_strict_fails_when_hit_rate_stale(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    art = root / "docs/final/artifacts"
    art.mkdir(parents=True)
    old = datetime.now(timezone.utc) - timedelta(hours=200)
    hit = {"schema": "x", "generated_at_utc": _iso(old), "metrics": {}}
    (art / "prophecy_hit_rate_eval_latest.json").write_text(json.dumps(hit), encoding="utf-8")

    code, data = _run(root, ["--strict", "--max-hit-rate-age-hours", "96"])
    assert code == 1
    assert data.get("overall_ok") is False


def _write_pipeline_stub_artifacts(root: Path, *, ts: datetime) -> None:
    stamp = _iso(ts)
    stubs: list[tuple[Path, dict]] = [
        (root / "reports/btrack_ensemble_per_date_directions_dual_v1_latest.json", {"generated_at_utc": stamp}),
        (root / "docs/final/artifacts/btrack_prophecy_score_latest.json", {"generated_at_utc": stamp}),
        (root / "reports/morning_prophecy_briefing_report_latest.json", {"generated_at_utc": stamp}),
        (
            root / "projects/mkm/mkm-life/public/data/three_lens_sphere_envelope_public_v1.json",
            {"ts_utc": stamp},
        ),
    ]
    for path, body in stubs:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(body), encoding="utf-8")


def test_fresh_hit_rate_ok(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    art = root / "docs/final/artifacts"
    art.mkdir(parents=True)
    now = datetime.now(timezone.utc) - timedelta(hours=1)
    hit = {"schema": "x", "generated_at_utc": _iso(now), "metrics": {}}
    (art / "prophecy_hit_rate_eval_latest.json").write_text(json.dumps(hit), encoding="utf-8")
    _write_pipeline_stub_artifacts(root, ts=now)

    code, data = _run(root, ["--strict"])
    assert code == 0
    assert data.get("overall_ok") is True
