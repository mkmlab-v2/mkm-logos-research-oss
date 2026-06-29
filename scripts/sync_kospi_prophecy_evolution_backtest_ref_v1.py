#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sync evolution candidate backtest_ref from multilens blend artifact SSOT."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_EVOLUTION = ROOT / "data/commander/kospi_june2026_prophecy_evolution_v1.json"
DEFAULT_BACKTEST_140 = ROOT / "reports/kospi_multilens_blend_backtest_latest.json"
DEFAULT_BACKTEST_30Y = ROOT / "reports/kospi_multilens_blend_backtest_full30y_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _variant_metrics(backtest: dict[str, Any], variant_id: str) -> dict[str, Any] | None:
    rows = backtest.get("variants") if isinstance(backtest.get("variants"), list) else []
    for row in rows:
        if isinstance(row, dict) and row.get("variant_id") == variant_id:
            m = row.get("metrics") if isinstance(row.get("metrics"), dict) else {}
            return {
                "n_scored": m.get("n_scored"),
                "soft_hit_rate": m.get("soft_hit_rate"),
                "directional_hit_rate": m.get("directional_hit_rate"),
                "hit": m.get("hit"),
                "fail": m.get("fail"),
                "neutral_draw": m.get("neutral_draw"),
            }
    return None


def sync_backtest_refs(
    evolution: dict[str, Any],
    *,
    backtest_140: dict[str, Any],
    backtest_30y: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    candidates = evolution.get("blend_weights_v2_candidates")
    if not isinstance(candidates, dict):
        raise ValueError("blend_weights_v2_candidates missing")

    changes: list[dict[str, Any]] = []
    window_140 = backtest_140.get("window") or "2025-11-01..2026-05-30"
    art_140 = "reports/kospi_multilens_blend_backtest_latest.json"
    art_30y = "reports/kospi_multilens_blend_backtest_full30y_latest.json"

    for cid, row in candidates.items():
        if not isinstance(row, dict):
            continue
        ref = row.get("backtest_ref")
        if not isinstance(ref, dict):
            continue
        artifact_path = str(ref.get("artifact") or "")
        if "full30y" in artifact_path or (backtest_30y and cid.endswith("_4ai_current")):
            src = backtest_30y or backtest_140
            art = art_30y if backtest_30y else art_140
            window = src.get("window") or ref.get("window")
        elif "blend_backtest_latest" in artifact_path or cid == "v2_lens3_heavy":
            src = backtest_140
            art = art_140
            window = window_140
        else:
            continue

        metrics = _variant_metrics(src, cid)
        if not metrics:
            continue

        before = {
            "soft_hit_rate": ref.get("soft_hit_rate"),
            "directional_hit_rate": ref.get("directional_hit_rate"),
            "n_scored": ref.get("n_scored"),
        }
        ref["window"] = window
        ref["artifact"] = art
        ref["n_scored"] = metrics["n_scored"]
        ref["soft_hit_rate"] = metrics["soft_hit_rate"]
        ref["directional_hit_rate"] = metrics["directional_hit_rate"]
        ref["synced_at_utc"] = _utc_now()

        after = {
            "soft_hit_rate": ref.get("soft_hit_rate"),
            "directional_hit_rate": ref.get("directional_hit_rate"),
            "n_scored": ref.get("n_scored"),
        }
        if before != after:
            changes.append({"candidate_id": cid, "before": before, "after": after})

    evolution["backtest_ref_sync"] = {
        "synced_at_utc": _utc_now(),
        "source_140d": art_140,
        "source_30y": art_30y if backtest_30y else None,
        "changes": changes,
    }
    return evolution, changes


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--evolution-json", type=Path, default=DEFAULT_EVOLUTION)
    ap.add_argument("--backtest-140", type=Path, default=DEFAULT_BACKTEST_140)
    ap.add_argument("--backtest-30y", type=Path, default=DEFAULT_BACKTEST_30Y)
    ap.add_argument("--dry-run", action="store_true")
    ns = ap.parse_args()

    evolution = _read(ns.evolution_json)
    backtest_140 = _read(ns.backtest_140)
    backtest_30y = _read(ns.backtest_30y) if ns.backtest_30y.is_file() else None

    updated, changes = sync_backtest_refs(
        evolution,
        backtest_140=backtest_140,
        backtest_30y=backtest_30y,
    )

    if not ns.dry_run:
        ns.evolution_json.write_text(
            json.dumps(updated, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    print(
        json.dumps(
            {
                "ok": True,
                "dry_run": ns.dry_run,
                "evolution": str(ns.evolution_json),
                "n_changes": len(changes),
                "changes": changes,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
