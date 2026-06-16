#!/usr/bin/env python3
"""[HYPO-4] Run MASK HYPO passive cross-audit chain (registry + 3 HYPO runners)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.compression_mask_hypo_passive_cross_audit_v1_lib import (  # noqa: E402
    run_passive_cross_audit,
    write_cross_audit_report,
)

DEFAULT_REPORT = ROOT / "reports/compression_mask_hypo_passive_cross_audit_v1_latest.json"
DEFAULT_ARTIFACT = ROOT / "docs/final/artifacts/compression_mask_hypo_passive_cross_audit_v1_latest.json"


def main() -> int:
    ap = argparse.ArgumentParser(description="[HYPO-4] MASK HYPO passive cross-audit")
    ap.add_argument("--workspace-root", type=Path, default=ROOT)
    ap.add_argument("--report-out", type=Path, default=DEFAULT_REPORT)
    ap.add_argument("--artifact-out", type=Path, default=DEFAULT_ARTIFACT)
    ap.add_argument("--skip-coord-sibling", action="store_true")
    args = ap.parse_args()

    report = run_passive_cross_audit(
        workspace_root=args.workspace_root,
        include_coord_sibling=not args.skip_coord_sibling,
    )
    write_cross_audit_report(report, report_path=args.report_out, artifact_path=args.artifact_out)
    agg = report["aggregate"]
    print(
        json.dumps(
            {
                "ok": agg["all_steps_pass"],
                "pass_count": agg["pass_count"],
                "step_count": agg["step_count"],
                "failed_step_ids": agg["failed_step_ids"],
                "report_out": str(args.report_out),
            },
            ensure_ascii=False,
        )
    )
    return 0 if agg["all_steps_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
