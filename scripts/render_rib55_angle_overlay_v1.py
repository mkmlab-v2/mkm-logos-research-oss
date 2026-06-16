# -*- coding: utf-8 -*-
"""[HYPO] CLI: render rib55 manifest overlay pilot PNG (deterministic geometry layer).

Usage:
  py scripts/render_rib55_angle_overlay_v1.py --fetch-base --update-manifest
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.rib55_angle_overlay_v1_lib import (  # noqa: E402
    DEFAULT_MANIFEST,
    DEFAULT_OUT_DIR,
    render_from_manifest,
)


def main() -> int:
    ap = argparse.ArgumentParser(description="[HYPO] Render rib55 angle overlay from manifest")
    ap.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--entry-id", default=None, help="defaults to first manifest entry")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--fetch-base", action="store_true", help="download Commons base image if missing")
    ap.add_argument("--update-manifest", action="store_true", help="write base_image + verification back")
    ap.add_argument("--report-out", type=Path, default=ROOT / "reports/rib55_angle_overlay_render_v1_latest.json")
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
        print(f"rib55 overlay render failed: {exc}", file=sys.stderr)
        return 1

    report["generated_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    args.report_out.parent.mkdir(parents=True, exist_ok=True)
    args.report_out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({"ok": True, "output": report["output"], "report": str(args.report_out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
