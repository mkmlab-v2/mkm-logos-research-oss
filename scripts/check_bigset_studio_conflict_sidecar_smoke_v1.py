#!/usr/bin/env python3
"""Offline smoke: BigSet studio conflict sidecar mirror (no1kmedi public JSON).

Reproducible:
  py scripts/check_bigset_studio_conflict_sidecar_smoke_v1.py
  py scripts/check_bigset_studio_conflict_sidecar_smoke_v1.py --require-pending-field
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "docs/final/artifacts/bigset_studio_conflict_sidecar_v1_latest.json"
MIRROR = ROOT / "projects/no1kmedi/public/data/logos_studio/bigset_conflict_sidecar_v1.json"
OUT = ROOT / "reports/bigset_studio_conflict_sidecar_smoke_v1_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def validate_doc(doc: dict, *, require_pending_field: bool) -> list[str]:
    errors: list[str] = []
    if doc.get("schema") != "bigset_studio_conflict_sidecar_v1":
        errors.append("schema_mismatch")
    if doc.get("send_gate") != "HOLD":
        errors.append("send_gate_not_hold")
    groups = doc.get("groups")
    if not isinstance(groups, list) or not groups:
        errors.append("groups_empty")
    else:
        g0 = groups[0]
        if not isinstance(g0.get("schools"), list) or not g0["schools"]:
            errors.append("schools_empty")
    obs = doc.get("observability")
    if require_pending_field:
        if not isinstance(obs, dict) or "human_review_pending_count" not in obs:
            errors.append("observability_pending_missing")
    ui = doc.get("ui_contract")
    if not isinstance(ui, dict) or not ui.get("disclaimer_ko"):
        errors.append("ui_contract_missing")
    return errors


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--require-pending-field", action="store_true")
    args = ap.parse_args()

    fails: list[str] = []
    try:
        art = _load(ARTIFACT)
        mirror = _load(MIRROR)
    except FileNotFoundError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        return 2

    fails.extend(f"artifact:{e}" for e in validate_doc(art, require_pending_field=args.require_pending_field))
    fails.extend(f"mirror:{e}" for e in validate_doc(mirror, require_pending_field=args.require_pending_field))

    if art.get("group_count") != mirror.get("group_count"):
        fails.append("artifact_mirror_group_count_mismatch")

    report = {
        "schema": "bigset_studio_conflict_sidecar_smoke_v1",
        "generated_at_utc": _now(),
        "ok": not fails,
        "artifact": str(ARTIFACT.relative_to(ROOT)).replace("\\", "/"),
        "mirror": str(MIRROR.relative_to(ROOT)).replace("\\", "/"),
        "group_count": art.get("group_count"),
        "human_review_pending_count": (art.get("observability") or {}).get("human_review_pending_count"),
        "fails": fails,
        "reproduce": "py scripts/check_bigset_studio_conflict_sidecar_smoke_v1.py",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": report["ok"], "group_count": report["group_count"], "fails": fails}, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
