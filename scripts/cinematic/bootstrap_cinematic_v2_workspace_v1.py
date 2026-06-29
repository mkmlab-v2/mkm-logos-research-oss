#!/usr/bin/env python3
"""Create cinematic v2 workspace dirs and bootstrap manifest."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_WORKSPACE = ART / "cinematic_v2_workspace"
DEFAULT_SHOT_PLAN = ART / "director_agent_v2_shot_plan_latest.json"
DEFAULT_OUT_JSON = ART / "cinematic_v2_workspace_bootstrap_latest.json"

REF_README = """# Cinematic v2 reference images (commander manual step)

Drop these files here before Flow i2v:

- master_character.png — Nano Banana Pro, front portrait, neutral expression, soft dawn light
- master_location.png — Korean home bedroom/living, same lighting palette as shot 01

Do not commit personal photos without approval.
send_gate: HOLD — internal teaser only.
"""


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workspace-root", type=Path, default=DEFAULT_WORKSPACE)
    ap.add_argument("--shot-plan-json", type=Path, default=DEFAULT_SHOT_PLAN)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    args = ap.parse_args()

    workspace = args.workspace_root if args.workspace_root.is_absolute() else (ROOT / args.workspace_root)
    shot_plan_path = args.shot_plan_json if args.shot_plan_json.is_absolute() else (ROOT / args.shot_plan_json)
    if not shot_plan_path.is_file():
        raise SystemExit(f"shot plan not found: {shot_plan_path}")

    shot_plan = json.loads(shot_plan_path.read_text(encoding="utf-8"))
    shots = shot_plan.get("shots") or []

    refs_dir = workspace / "references"
    refs_dir.mkdir(parents=True, exist_ok=True)
    readme = refs_dir / "README_REF_IMAGES.txt"
    readme.write_text(REF_README, encoding="utf-8")

    shot_dirs: list[str] = []
    for shot in shots:
        shot_dir = Path(shot["workspace_targets"]["shot_dir"])
        if not shot_dir.is_absolute():
            shot_dir = ROOT / shot_dir
        shot_dir.mkdir(parents=True, exist_ok=True)
        shot_dirs.append(shot_dir.as_posix())

    master_char = refs_dir / "master_character.png"
    master_loc = refs_dir / "master_location.png"

    payload = {
        "schema": "cinematic_v2_workspace_bootstrap_v1",
        "generated_at_utc": now_utc(),
        "workspace_root": workspace.as_posix(),
        "shot_plan_json": str(shot_plan_path.resolve()),
        "shot_count": len(shots),
        "shot_dirs": shot_dirs,
        "references": {
            "master_character_png": master_char.as_posix(),
            "master_character_exists": master_char.is_file(),
            "master_location_png": master_loc.as_posix(),
            "master_location_exists": master_loc.is_file(),
            "readme": readme.as_posix(),
        },
        "ready_for_flow_i2v": master_char.is_file() and master_loc.is_file(),
        "send_gate": "HOLD",
    }

    out_json = args.out_json if args.out_json.is_absolute() else (ROOT / args.out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({"ok": True, "bootstrap_json": str(out_json), **payload}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
