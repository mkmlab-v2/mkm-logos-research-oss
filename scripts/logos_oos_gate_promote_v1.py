#!/usr/bin/env python3
"""Promote best go=true Logos OOS gate snapshot to prophecy_logos_revalidation_oos_gate_latest.json."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
LATEST = ART / "prophecy_logos_revalidation_oos_gate_latest.json"
GOLDEN_252D = ART / "prophecy_logos_revalidation_oos_gate_golden_252d_v1.json"
WINDOW_DAYS = (252, 120, 60)


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    return raw if isinstance(raw, dict) else {}


def promote_best_logos_oos_gate(art: Path | None = None) -> dict[str, Any]:
    base = (art or ART).resolve()
    latest_path = base / "prophecy_logos_revalidation_oos_gate_latest.json"
    best_path: Path | None = None
    best_hit = -1.0
    candidates: list[dict[str, Any]] = []

    for days in WINDOW_DAYS:
        path = base / f"prophecy_logos_revalidation_oos_gate_{days}d_latest.json"
        doc = _read(path)
        gate = doc.get("gate") if isinstance(doc.get("gate"), dict) else {}
        metrics = doc.get("oos_metrics") if isinstance(doc.get("oos_metrics"), dict) else {}
        hit = metrics.get("directional_hit_rate_active")
        try:
            h = float(hit)
        except (TypeError, ValueError):
            h = None
        row = {
            "path": str(path),
            "window_days": days,
            "go": bool(gate.get("go")),
            "hit": h,
            "status": gate.get("status"),
        }
        candidates.append(row)
        if gate.get("go") and h is not None and h > best_hit:
            best_hit = h
            best_path = path

    promoted = False
    source_note = None
    if best_path is not None:
        shutil.copy2(best_path, latest_path)
        promoted = True
        source_note = "window_snapshots"
    elif GOLDEN_252D.is_file():
        golden = _read(GOLDEN_252D)
        g_gate = golden.get("gate") if isinstance(golden.get("gate"), dict) else {}
        if g_gate.get("go"):
            shutil.copy2(GOLDEN_252D, latest_path)
            promoted = True
            best_path = GOLDEN_252D
            g_metrics = golden.get("oos_metrics") if isinstance(golden.get("oos_metrics"), dict) else {}
            try:
                best_hit = float(g_metrics.get("directional_hit_rate_active"))
            except (TypeError, ValueError):
                best_hit = None
            source_note = "golden_252d_fallback"

    return {
        "schema": "logos_oos_gate_promote_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "research_only": True,
        "promoted": promoted,
        "source": str(best_path.resolve()) if best_path else None,
        "source_note": source_note,
        "latest": str(latest_path.resolve()),
        "best_hit": best_hit if best_hit >= 0 else None,
        "candidates": candidates,
        "golden_252d_path": str(GOLDEN_252D.resolve()) if GOLDEN_252D.is_file() else None,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--artifacts-dir", type=Path, default=ART)
    ap.add_argument("--out-json", type=Path, default=ROOT / "reports" / "logos_oos_gate_promote_latest.json")
    args = ap.parse_args()
    doc = promote_best_logos_oos_gate(args.artifacts_dir)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(doc, ensure_ascii=False))
    return 0 if doc.get("promoted") else 1


if __name__ == "__main__":
    raise SystemExit(main())
