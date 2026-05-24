# @MKM12-METADATA
# Type: Logic
# Purpose: Prophecy headline integrity observation gate (B-track, no live side effects).

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_CHECKER = _ROOT / "scripts" / "check_prophecy_headline_integrity_v1.py"


def _hit_eval(hit_rate: float = 0.5) -> dict:
    return {
        "schema": "prophecy_hit_rate_eval_report_v2",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "metrics": {
            "price_directional_hit_rate": hit_rate,
            "n_evaluated": 30,
            "price_hits": int(hit_rate * 30),
        },
        "inputs": {"headline_instrument": "auto"},
    }


def _score(*, per_date: str | None = None, rows: list | None = None, ts_offset_hours: int = 0) -> dict:
    ts = datetime.now(timezone.utc) + timedelta(hours=ts_offset_hours)
    ts_s = ts.strftime("%Y-%m-%dT%H:%M:%SZ")
    if rows is None:
        rows = [{"predicted_direction": "bear", "actual_direction": "bull"} for _ in range(20)]
    return {
        "schema": "btrack_prophecy_score_v1",
        "generated_at_utc": ts_s,
        "inputs": {"per_date_direction_json": per_date},
        "meta": {"frozen_prediction_note": "frozen batch"},
        "rows": rows,
    }


def _run(tmp_path: Path, hit: dict, score: dict | None = None, extra: list[str] | None = None) -> subprocess.CompletedProcess[str]:
    hit_p = tmp_path / "hit.json"
    score_p = tmp_path / "score.json"
    out_p = tmp_path / "out.json"
    dedup_p = tmp_path / "dedup.json"
    hit_p.write_text(json.dumps(hit), encoding="utf-8")
    if score is not None:
        score_p.write_text(json.dumps(score), encoding="utf-8")
    args = [
        sys.executable,
        str(_CHECKER),
        "--workspace-root",
        str(tmp_path),
        "--hit-eval-json",
        str(hit_p),
        "--score-json",
        str(score_p),
        "--out-json",
        str(out_p),
        "--dedup-state-json",
        str(dedup_p),
        "--skip-webhook",
    ]
    if extra:
        args.extend(extra)
    return subprocess.run(args, cwd=str(_ROOT), capture_output=True, text=True, timeout=30)


def test_missing_hit_exit_1(tmp_path: Path) -> None:
    cp = _run(tmp_path, _hit_eval(), score=_score())
    # score exists but hit path wrong - rewrite without hit file
    (tmp_path / "hit.json").unlink()
    cp = subprocess.run(
        [
            sys.executable,
            str(_CHECKER),
            "--workspace-root",
            str(tmp_path),
            "--hit-eval-json",
            str(tmp_path / "hit.json"),
            "--skip-webhook",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 1


def test_ok_high_hit_rate(tmp_path: Path) -> None:
    rows = [
        {"predicted_direction": "bull", "actual_direction": "bull"},
        {"predicted_direction": "bear", "actual_direction": "bull"},
    ]
    cp = _run(
        tmp_path,
        _hit_eval(0.5),
        _score(per_date="reports/per_date.json", rows=rows),
    )
    assert cp.returncode == 0, cp.stderr
    out = json.loads((tmp_path / "out.json").read_text(encoding="utf-8"))
    assert out["status"] == "HEADLINE_OK"


def test_low_hit_warn_exit_0(tmp_path: Path) -> None:
    cp = _run(tmp_path, _hit_eval(0.25), _score(per_date=None))
    assert cp.returncode == 0, cp.stderr
    out = json.loads((tmp_path / "out.json").read_text(encoding="utf-8"))
    assert out["status"] in ("HEADLINE_WARN", "HEADLINE_WARN_NO_WEBHOOK", "ALERT_FIRED")
    assert "LOW_HEADLINE_HIT_RATE" in out["warning_flags"]


def test_uniform_bear_flag(tmp_path: Path) -> None:
    rows = [{"predicted_direction": "bear"} for _ in range(15)]
    cp = _run(tmp_path, _hit_eval(0.3), _score(rows=rows))
    assert cp.returncode == 0
    out = json.loads((tmp_path / "out.json").read_text(encoding="utf-8"))
    assert any("UNIFORM_PREDICTED_DIRECTION_BEAR" in f for f in out["warning_flags"])
