#!/usr/bin/env python3
"""Validate evolution allowlist SSOT and cross-check evolution artifacts for auto_apply=false."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ALLOWLIST = ROOT / "docs" / "final" / "artifacts" / "evolution_auto_apply_allowlist_v1_latest.json"
DEFAULT_OUT = ROOT / "reports" / "evolution_auto_apply_allowlist_check_latest.json"

from evolution_auto_apply_allowlist_v1 import load_allowlist  # noqa: E402


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        o = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None
    return o if isinstance(o, dict) else None


def _check_artifact_auto_apply_false(path: Path, *, label: str) -> dict[str, Any]:
    doc = _read_json(path)
    if not doc:
        return {"id": label, "ok": False, "reason": "missing_or_invalid", "path": str(path)}
    mode = doc.get("mode")
    track_wall = doc.get("track_wall") if isinstance(doc.get("track_wall"), dict) else {}
    auto_apply = track_wall.get("auto_apply")
    ok = mode == "proposal_only_no_auto_apply" or auto_apply is False
    return {
        "id": label,
        "ok": ok,
        "path": str(path),
        "mode": mode,
        "track_wall_auto_apply": auto_apply,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--allowlist", type=Path, default=DEFAULT_ALLOWLIST)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--strict", action="store_true", help="Exit 1 when any check fails")
    args = ap.parse_args()

    checks: list[dict[str, Any]] = []
    try:
        doc = load_allowlist(args.allowlist)
        checks.append({"id": "allowlist_load", "ok": True, "path": str(args.allowlist)})
    except (FileNotFoundError, ValueError) as exc:
        checks.append({"id": "allowlist_load", "ok": False, "error": str(exc)})
        out = {
            "schema": "evolution_auto_apply_allowlist_check_v1",
            "checked_at_utc": _utc_now(),
            "all_pass": False,
            "checks": checks,
        }
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return 1 if args.strict else 0

    rails = doc.get("rails") if isinstance(doc.get("rails"), dict) else {}
    for rail_name in ("commander_hypothesis", "btrack_price", "general_holdout"):
        block = rails.get(rail_name) if isinstance(rails.get(rail_name), dict) else {}
        mode = str(block.get("auto_apply_mode") or "")
        expected_none = rail_name in ("commander_hypothesis", "general_holdout")
        ok = (mode == "none") if expected_none else (mode == "parameter_only")
        checks.append(
            {
                "id": f"rail_mode_{rail_name}",
                "ok": ok,
                "auto_apply_mode": mode,
                "expected": "none" if expected_none else "parameter_only",
            }
        )

    forbidden = doc.get("forbidden_targets")
    checks.append(
        {
            "id": "forbidden_targets_nonempty",
            "ok": isinstance(forbidden, list) and len(forbidden) >= 3,
            "count": len(forbidden) if isinstance(forbidden, list) else 0,
        }
    )

    checks.append(
        _check_artifact_auto_apply_false(
            ROOT / "docs/final/artifacts/general_prophecy_holdout_evolution_candidates_latest.json",
            label="general_holdout_candidates",
        )
    )
    checks.append(
        _check_artifact_auto_apply_false(
            ROOT / "docs/final/artifacts/general_prophecy_holdout_evolution_ablation_latest.json",
            label="general_holdout_ablation",
        )
    )

    draft = _read_json(ROOT / "docs/final/artifacts/autonomous_evolution_loop_draft_v1_latest.json")
    dry_ok = bool(draft.get("dry_run")) if draft else False
    checks.append({"id": "commander_evolution_draft_dry_run", "ok": dry_ok, "dry_run": draft.get("dry_run") if draft else None})

    all_pass = all(bool(c.get("ok")) for c in checks)
    out = {
        "schema": "evolution_auto_apply_allowlist_check_v1",
        "checked_at_utc": _utc_now(),
        "allowlist_path": str(args.allowlist.resolve()),
        "all_pass": all_pass,
        "checks": checks,
        "human_signoff_required_for": doc.get("human_signoff_required_for"),
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"all_pass": all_pass, "out": str(args.out_json.resolve())}, ensure_ascii=False))
    if args.strict and not all_pass:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
