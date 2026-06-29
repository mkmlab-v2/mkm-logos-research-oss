#!/usr/bin/env python3
"""Enforce UR public push/post gate — substance before GitHub, repro before GTM [HYPO · HOLD]."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.universal_root_public_push_gate_lib_v1 import evaluate_public_push_gate  # noqa: E402

OUT = ROOT / "reports/universal_root_public_push_gate_v1_latest.json"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--action",
        default="github_public_push",
        help="github_public_push | export_materialize | discussions_live_post | maintainer_bump | …",
    )
    ap.add_argument(
        "--strict-substance",
        action="store_true",
        help="exit 1 unless integrity_ok AND named_public_bench_ok (GitHub export push tier)",
    )
    ap.add_argument(
        "--strict-launch",
        action="store_true",
        help="exit 1 unless substance + external_repro>=1 (live GTM tier)",
    )
    ap.add_argument("--commander-override-push-gate", action="store_true")
    ap.add_argument("--skip-integrity", action="store_true")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    ev = evaluate_public_push_gate(
        action=args.action,
        commander_override=args.commander_override_push_gate,
        skip_integrity=args.skip_integrity,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(ev, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": ev["ok"],
                "allowed": ev["allowed"],
                "action": ev["action"],
                "integrity_ok": ev["integrity_ok"],
                "named_public_bench_ok": ev["named_public_bench_ok"],
                "external_repro_count": ev["external_repro_count"],
                "violations": ev["violations"],
                "out": str(args.out),
            },
            ensure_ascii=False,
        )
    )

    if args.commander_override_push_gate:
        return 0
    if args.strict_launch:
        if not ev["ok"]:
            return 1
        if int(ev.get("external_repro_count") or 0) < 1:
            return 1
        return 0
    if args.strict_substance:
        if not ev["integrity_ok"] or not ev["named_public_bench_ok"]:
            return 1
        return 0
    return 0 if ev["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
