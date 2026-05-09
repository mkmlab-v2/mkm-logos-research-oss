#!/usr/bin/env python3
"""Pro video helpers: LUT path from profile JSON (optional ASS via subtitles/main.ass in S2 folder)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_VIDEO_PROFILE = ROOT / "docs" / "final" / "artifacts" / "athena_pro_video_profile_v1.json"


def load_video_profile(path: Path | None) -> dict[str, Any]:
    p = path if path else DEFAULT_VIDEO_PROFILE
    if not p.is_file():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def video_profile_for_render(profile: dict[str, Any]) -> dict[str, Any]:
    """Subset passed to render_s2_preset_v2 via JSON (lut_cube path string)."""
    out: dict[str, Any] = {}
    lc = profile.get("lut_cube")
    if lc is not None and str(lc).strip():
        out["lut_cube"] = lc
    return out


def write_render_video_snippet(profile: dict[str, Any], out_path: Path) -> None:
    snippet = video_profile_for_render(profile)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(snippet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_print = sub.add_parser("print-default-profile", help="Print bundled default video profile path + JSON")
    args = ap.parse_args()
    if args.cmd == "print-default-profile":
        data = load_video_profile(DEFAULT_VIDEO_PROFILE)
        print(DEFAULT_VIDEO_PROFILE.as_posix())
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
