#!/usr/bin/env python3
"""Project mkm_video_rig_stub_v1 with Option B hard clamp (B-track [HYPO])."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.video_rig_dual_plane_v1_lib import project_video_rig  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Hard-project video rig stub JSON (Option B).")
    ap.add_argument("--rig-json", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    rig = json.loads(args.rig_json.read_text(encoding="utf-8"))
    try:
        projected = project_video_rig(rig)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(projected, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    stage = dict(projected.get("projection_stage") or {})
    print(
        json.dumps(
            {
                "ok": True,
                "out": str(args.out.resolve().as_posix()),
                "clip_count": len(stage.get("clip_notes") or []),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
