#!/usr/bin/env python3
"""Write sasang routing sidecar × narrative path A/B report."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.core.sasang_routing_sidecar_narrative_ab_v1 import (  # noqa: E402
    DEFAULT_BRIDGE,
    DEFAULT_PANEL,
    DEFAULT_SIDECAR,
    build_ab_report,
)

OUT = ROOT / "reports/sasang_routing_sidecar_narrative_path_ab_v1_latest.json"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--panel-path", type=Path, default=None, help="override panel JSON path")
    ap.add_argument("--sidecar", type=Path, default=DEFAULT_SIDECAR)
    ap.add_argument("--bridge", type=Path, default=DEFAULT_BRIDGE)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--skip-router", action="store_true")
    ap.add_argument("--panel", choices=("fixed", "full"), default="fixed")
    ap.add_argument("--profile", choices=("observe", "tactical", "structural"), default=None)
    ap.add_argument("--tag", type=str, default=None)
    args = ap.parse_args()

    panel_path = args.panel_path or DEFAULT_PANEL
    if args.panel_path is None and args.panel == "full":
        panel_path = ROOT / "docs/final/artifacts/fixtures/sasang_routing_sidecar_narrative_ab_panel_full_v1.json"

    tag = args.tag or (f"{args.panel}_{args.profile or 'default'}")
    out = args.out
    if args.out == OUT and (args.panel != "fixed" or args.profile):
        out = ROOT / f"reports/sasang_routing_sidecar_narrative_path_ab_{tag}_latest.json"

    for label, path in (("panel", panel_path), ("sidecar", args.sidecar), ("bridge", args.bridge)):
        if not path.is_file():
            print(json.dumps({"ok": False, "error": f"missing {label}: {path}"}))
            return 1

    report = build_ab_report(
        panel_path=panel_path,
        sidecar_path=args.sidecar,
        bridge_path=args.bridge,
        run_router=not args.skip_router,
        entropy_profile=args.profile,
        report_tag=tag,
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    d = report["delta"]
    print(
        json.dumps(
            {
                "ok": True,
                "panel_n": report["panel_sample_count"],
                "delta_gate": d["sidecar_gate_pass_rate_minus_sample_pass_rate"],
                "delta_router_paths": d["narrowed_router_paths_minus_baseline"],
                "out": str(out),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
