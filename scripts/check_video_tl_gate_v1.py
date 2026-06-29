#!/usr/bin/env python3
"""NeuS-V-inspired temporal-logic gate stub for video rig events (B-track [HYPO]).

Evaluates raw rig vs Option-B projected rig separately. Never merges raw/post into one score.
Reference: NeuS-V (CVPR 2025) — evaluation gate only, not a generator.
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

from scripts.video_rig_dual_plane_v1_lib import evaluate_dual_plane_tl_gate  # noqa: E402

DEFAULT_OUT = ROOT / "reports/video_tl_gate_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main() -> int:
    ap = argparse.ArgumentParser(description="Video TL gate — raw vs post-project dual report.")
    ap.add_argument("--rig-json", type=Path, required=True, help="Raw/draft mkm_video_rig_stub_v1 JSON.")
    ap.add_argument("--tl-spec", type=Path, required=True, help="video_tl_spec_stub_v1 JSON.")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--export-projected-rig", type=Path, default=None)
    args = ap.parse_args()

    rig = json.loads(args.rig_json.read_text(encoding="utf-8"))
    tl_spec = json.loads(args.tl_spec.read_text(encoding="utf-8"))
    if tl_spec.get("schema") != "video_tl_spec_stub_v1":
        print("error: expected schema video_tl_spec_stub_v1", file=sys.stderr)
        return 2

    try:
        report = evaluate_dual_plane_tl_gate(raw_rig=rig, tl_spec=tl_spec)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    projected = report.pop("projected_rig")
    report["generated_at_utc"] = _utc()
    report["inputs"] = {
        "rig_json": str(args.rig_json.resolve().as_posix()),
        "tl_spec": str(args.tl_spec.resolve().as_posix()),
    }
    report["reproduce"] = (
        "py scripts/check_video_tl_gate_v1.py "
        f"--rig-json {args.rig_json.as_posix()} --tl-spec {args.tl_spec.as_posix()}"
    )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    if args.export_projected_rig is not None:
        args.export_projected_rig.parent.mkdir(parents=True, exist_ok=True)
        args.export_projected_rig.write_text(
            json.dumps(projected, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    raw_rate = report["raw"]["violation_rate"]
    post_rate = report["post_project"]["violation_rate"]
    ok = post_rate == 0.0
    print(
        json.dumps(
            {
                "ok": ok,
                "raw_violation_rate": raw_rate,
                "post_project_violation_rate": post_rate,
                "delta": report["delta_post_minus_raw_violation_rate"],
                "out": str(args.out.resolve().as_posix()),
            },
            ensure_ascii=False,
        )
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
