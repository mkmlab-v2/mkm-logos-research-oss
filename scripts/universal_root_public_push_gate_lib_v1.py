#!/usr/bin/env python3
"""UR public push/post gate — substance + repro before GitHub/GTM [HYPO · HOLD]."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BENCH_SSOT = ROOT / "docs/final/artifacts/universal_root_named_public_bench_v1.json"
HOLDOUT_DEFAULT = ROOT / "tests/fixtures/universal_root_b0_miss_holdout_bench_v1.json"
BENCH_REPORT = ROOT / "reports/universal_root_b0_miss_holdout_bench_v1_latest.json"

LIVE_GTM_ACTIONS = frozenset(
    {
        "maintainer_bump",
        "discussions_live_post",
        "x_live_post",
        "reddit_live_post",
        "community_gtm_live",
    }
)
SUBSTANCE_PUSH_ACTIONS = frozenset(
    {
        "github_public_push",
        "export_materialize",
        "export_push_mirror",
        "readme_hero_update",
    }
)


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def evaluate_named_public_bench() -> dict[str, Any]:
    ssot = _read_json(BENCH_SSOT)
    min_pairs = int(ssot.get("min_holdout_pairs") or 10)
    holdout_path = ROOT / str(ssot.get("holdout_fixture") or HOLDOUT_DEFAULT.relative_to(ROOT).as_posix())
    report_path = ROOT / str(ssot.get("report_artifact") or BENCH_REPORT.relative_to(ROOT).as_posix())

    violations: list[str] = []
    holdout = _read_json(holdout_path)
    report = _read_json(report_path)

    if holdout.get("schema") != "universal_root_b0_miss_holdout_bench_v1":
        violations.append("holdout_fixture_missing_or_schema_mismatch")
    pair_count = int(holdout.get("pair_count") or 0)
    if pair_count < min_pairs:
        violations.append(f"holdout_pair_count_below_min:{pair_count}<{min_pairs}")
    if not report.get("pair_count"):
        violations.append("bench_report_missing")

    b0_miss_rate = holdout.get("b0_miss_rate")
    b0_hit_rate = holdout.get("b0_hit_rate")
    if b0_hit_rate is None and pair_count > 0:
        violations.append("b0_hit_rate_missing")

    ok = not violations
    return {
        "named_public_bench_ok": ok,
        "bench_name": ssot.get("name") or "UR-B0-MISS-HOLDOUT-v1",
        "holdout_fixture": str(holdout_path.relative_to(ROOT)).replace("\\", "/") if holdout_path.is_file() else None,
        "pair_count": pair_count,
        "min_holdout_pairs": min_pairs,
        "b0_miss_rate": b0_miss_rate,
        "b0_hit_rate": b0_hit_rate,
        "violations": violations,
        "bench_ssot": str(BENCH_SSOT.relative_to(ROOT)).replace("\\", "/"),
    }


def evaluate_public_push_gate(
    *,
    action: str = "github_public_push",
    commander_override: bool = False,
    skip_integrity: bool = False,
) -> dict[str, Any]:
    from scripts.universal_root_gtm_freeze_lib_v1 import evaluate_gtm_freeze, external_repro_count  # noqa: WPS433

    freeze_ev = evaluate_gtm_freeze(
        action=action if action in LIVE_GTM_ACTIONS else "read_only",
        commander_override=commander_override,
        skip_integrity=skip_integrity,
    )
    bench_ev = evaluate_named_public_bench()
    ext = int(freeze_ev.get("external_repro_count") or external_repro_count())
    integrity_ok = bool(freeze_ev.get("integrity_ok"))
    named_ok = bool(bench_ev.get("named_public_bench_ok"))

    violations: list[str] = []
    if commander_override:
        allowed = True
    elif action in LIVE_GTM_ACTIONS:
        if not integrity_ok:
            violations.append("phase1a_integrity_failed")
        if not named_ok:
            violations.append("named_public_bench_missing")
        if ext < 1:
            violations.append("external_repro_below_min")
        allowed = not violations
    elif action in SUBSTANCE_PUSH_ACTIONS:
        if not integrity_ok:
            violations.append("phase1a_integrity_failed")
        if not named_ok:
            violations.append("named_public_bench_missing")
        allowed = not violations
    else:
        allowed = integrity_ok and named_ok

    return {
        "schema": "universal_root_public_push_gate_eval_v1",
        "version": "1.0.0",
        "evaluated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "action": action,
        "commander_override": commander_override,
        "integrity_ok": integrity_ok,
        "named_public_bench_ok": named_ok,
        "named_public_bench": bench_ev,
        "external_repro_count": ext,
        "public_gtm_allowed": bool(freeze_ev.get("public_gtm_allowed")),
        "gtm_freeze_eval": freeze_ev,
        "violations": violations,
        "ok": allowed,
        "allowed": allowed,
        "gate_ssot": "docs/final/artifacts/universal_root_named_public_bench_v1.json",
        "reproduce_substance": "py scripts/check_universal_root_public_push_gate_v1.py --strict-substance",
        "reproduce_launch": "py scripts/check_universal_root_public_push_gate_v1.py --strict-launch",
    }
