#!/usr/bin/env python3
"""Write logos_narrative_path_eval_v1_latest.json from bridge narrative samples."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.core.logos_narrative_path_eval_v1 import build_narrative_path_eval_report

OUT = ROOT / "docs/final/artifacts/logos_narrative_path_eval_v1_latest.json"
BRIDGE = ROOT / "docs/final/artifacts/logos_cosmic_anchor_graph_bridge_v1_latest.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bridge-json", type=Path, default=BRIDGE)
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--skip-router", action="store_true")
    args = parser.parse_args()

    if not args.bridge_json.is_file():
        print(f"FAIL: missing {args.bridge_json}", file=sys.stderr)
        return 1

    bridge = json.loads(args.bridge_json.read_text(encoding="utf-8"))
    report = build_narrative_path_eval_report(bridge, run_router=not args.skip_router)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    s = report["summary"]
    print(f"WROTE: {args.out}")
    print(
        f"  samples={report['narrative_sample_count']} "
        f"path_ok_rate={s['path_ok_rate']} flow_pass_rate={s['flow_pass_rate']} "
        f"sample_pass_rate={s['sample_pass_rate']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
