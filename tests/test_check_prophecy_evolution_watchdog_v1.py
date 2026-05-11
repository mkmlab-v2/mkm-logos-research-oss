"""Tests for scripts/check_prophecy_evolution_watchdog_v1.py"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(workspace: Path, extra: list[str] | None = None) -> tuple[int, dict]:
    script = Path(__file__).resolve().parents[1] / "scripts" / "check_prophecy_evolution_watchdog_v1.py"
    cmd = [sys.executable, str(script), "--workspace-root", str(workspace)]
    if extra:
        cmd.extend(extra)
    p = subprocess.run(cmd, capture_output=True, text=True, check=False)
    out = workspace / "reports" / "prophecy_evolution_watchdog_latest.json"
    data = json.loads(out.read_text(encoding="utf-8")) if out.is_file() else {}
    return p.returncode, data


def test_watchdog_ok_fresh(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    art = root / "docs/final/artifacts"
    art.mkdir(parents=True)
    now = datetime.now(timezone.utc)
    ablation = {
        "schema": "general_prophecy_holdout_evolution_ablation_v1",
        "generated_at_utc": _iso(now - timedelta(hours=1)),
        "recommended_candidate_id": "noop",
    }
    (art / "general_prophecy_holdout_evolution_ablation_latest.json").write_text(
        json.dumps(ablation), encoding="utf-8"
    )
    hit = {
        "schema": "prophecy_hit_rate_eval_report_v2",
        "generated_at_utc": _iso(now - timedelta(hours=2)),
        "metrics": {"price_directional_hit_rate": 0.5},
    }
    (art / "prophecy_hit_rate_eval_latest.json").write_text(json.dumps(hit), encoding="utf-8")

    code, data = _run(root, ["--max-ablation-age-hours", "96", "--max-hit-rate-age-hours", "96"])
    assert code == 0
    assert data.get("overall_ok") is True
    assert any(c["id"] == "general_prophecy_ablation_fresh" for c in data["checks"])


def test_watchdog_fail_stale_ablation(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    art = root / "docs/final/artifacts"
    art.mkdir(parents=True)
    old = datetime.now(timezone.utc) - timedelta(hours=200)
    ablation = {"schema": "x", "generated_at_utc": _iso(old)}
    (art / "general_prophecy_holdout_evolution_ablation_latest.json").write_text(
        json.dumps(ablation), encoding="utf-8"
    )
    now = datetime.now(timezone.utc)
    hit = {"schema": "prophecy_hit_rate_eval_report_v2", "generated_at_utc": _iso(now - timedelta(hours=1)), "metrics": {}}
    (art / "prophecy_hit_rate_eval_latest.json").write_text(json.dumps(hit), encoding="utf-8")

    code, data = _run(root, ["--max-ablation-age-hours", "96"])
    assert code == 1
    assert data.get("overall_ok") is False


def test_allow_missing_ablation(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    (root / "docs/final/artifacts").mkdir(parents=True)
    code, data = _run(root, ["--allow-missing-ablation", "--allow-missing-hit-rate"])
    assert code == 0
    assert data.get("overall_ok") is True


def _write_fresh_evals(root: Path, *, hit_rate: float, gen_offset_hours: int = 0) -> None:
    art = root / "docs/final/artifacts"
    art.mkdir(parents=True)
    now = datetime.now(timezone.utc) - timedelta(hours=gen_offset_hours)
    iso = _iso(now)
    ablation = {"schema": "general_prophecy_holdout_evolution_ablation_v1", "generated_at_utc": iso}
    (art / "general_prophecy_holdout_evolution_ablation_latest.json").write_text(
        json.dumps(ablation), encoding="utf-8"
    )
    hit = {
        "schema": "prophecy_hit_rate_eval_report_v2",
        "generated_at_utc": iso,
        "metrics": {"price_directional_hit_rate": hit_rate},
    }
    (art / "prophecy_hit_rate_eval_latest.json").write_text(json.dumps(hit), encoding="utf-8")


def test_hit_rate_streak_fails(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    rep = root / "reports"
    rep.mkdir(parents=True)
    tail = rep / "prophecy_evolution_watchdog_hit_rate_tail_v1.jsonl"
    rows = [
        {"schema": "prophecy_watchdog_hit_rate_tail_v1", "sampled_from_eval_generated_at": "2026-01-01T00:00:00Z", "hit_rate": 0.35},
        {"schema": "prophecy_watchdog_hit_rate_tail_v1", "sampled_from_eval_generated_at": "2026-01-02T00:00:00Z", "hit_rate": 0.35},
        {"schema": "prophecy_watchdog_hit_rate_tail_v1", "sampled_from_eval_generated_at": "2026-01-03T00:00:00Z", "hit_rate": 0.35},
    ]
    tail.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    _write_fresh_evals(root, hit_rate=0.50)

    code, data = _run(
        root,
        [
            "--max-ablation-age-hours",
            "200",
            "--max-hit-rate-age-hours",
            "200",
            "--hit-rate-streak-count",
            "3",
            "--hit-rate-streak-below",
            "0.4",
            "--no-append-hit-rate-tail",
        ],
    )
    assert code == 1
    assert data.get("overall_ok") is False
    streak = [c for c in data["checks"] if c.get("id") == "btrack_hit_rate_streak_guard"]
    assert streak and streak[0].get("ok") is False


def test_hit_rate_ema_guard_fails(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    rep = root / "reports"
    rep.mkdir(parents=True)
    tail = rep / "prophecy_evolution_watchdog_hit_rate_tail_v1.jsonl"
    rows = [{"hit_rate": 0.2}, {"hit_rate": 0.2}, {"hit_rate": 0.2}, {"hit_rate": 0.2}]
    tail.write_text(
        "\n".join(json.dumps({"schema": "t", **r}) for r in rows) + "\n",
        encoding="utf-8",
    )
    _write_fresh_evals(root, hit_rate=0.9)

    code, data = _run(
        root,
        [
            "--max-ablation-age-hours",
            "200",
            "--max-hit-rate-age-hours",
            "200",
            "--hit-rate-ema-min",
            "0.55",
            "--hit-rate-ema-alpha",
            "0.25",
            "--hit-rate-ema-max-lines",
            "12",
            "--no-append-hit-rate-tail",
        ],
    )
    assert code == 1
    ema_chk = [c for c in data["checks"] if c.get("id") == "btrack_hit_rate_ema_guard"]
    assert ema_chk and ema_chk[0].get("ok") is False
