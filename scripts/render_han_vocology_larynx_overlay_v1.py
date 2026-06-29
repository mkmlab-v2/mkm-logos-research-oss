#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""CLI for Han Vocology larynx overlay render."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.han_vocology_larynx_overlay_v1_lib import (  # noqa: E402
    DEFAULT_MANIFEST,
    DEFAULT_OUT,
    render_from_manifest,
)


def main() -> int:
    ap = argparse.ArgumentParser(description="Render Han Vocology larynx CV overlay")
    ap.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--entry-id", default="larynx_cv23_pilot_v0")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--fetch-base", action="store_true")
    ap.add_argument("--update-manifest", action="store_true")
    ap.add_argument("--report-out", type=Path, default=ROOT / "reports/han_vocology_larynx_overlay_render_v1_latest.json")
    args = ap.parse_args()

    try:
        report = render_from_manifest(
            args.manifest,
            entry_id=args.entry_id,
            out_path=args.out,
            fetch_base=args.fetch_base,
            update_manifest=args.update_manifest,
            workspace_root=ROOT,
        )
    except Exception as exc:
        print(f"larynx overlay render failed: {exc}", file=sys.stderr)
        return 1

    args.report_out.parent.mkdir(parents=True, exist_ok=True)
    args.report_out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": report["output"], "status": report["status"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
