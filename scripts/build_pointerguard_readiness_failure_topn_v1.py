#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "docs" / "final" / "artifacts"
READINESS_DEFAULT = ART / "pointerguard_ops_readiness_latest.json"
OUT_DEFAULT = ART / "pointerguard_readiness_failure_topn_latest.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--readiness-json", type=Path, default=READINESS_DEFAULT)
    ap.add_argument("--top-n", type=int, default=3)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    readiness_path = args.readiness_json if args.readiness_json.is_absolute() else ROOT / args.readiness_json
    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    doc = _read_json(readiness_path)
    if str(doc.get("schema")) != "pointerguard_ops_readiness_v1":
        raise SystemExit("readiness schema mismatch")

    checks = doc.get("checks", [])
    if not isinstance(checks, list):
        checks = []
    failed = [c for c in checks if isinstance(c, dict) and not bool(c.get("ok", False))]
    reason_counter = Counter(str(c.get("reason", "unknown")) for c in failed)
    topn = reason_counter.most_common(max(1, int(args.top_n)))

    repair_queue = []
    for i, (reason, count) in enumerate(topn, start=1):
        repair_queue.append(
            {
                "priority": i,
                "reason": reason,
                "count": count,
                "suggested_action": f"Investigate and fix checks failing with reason `{reason}`",
            }
        )

    out_doc = {
        "schema": "pointerguard_readiness_failure_topn_v1",
        "generated_at_utc": _now_utc(),
        "source": {"readiness_json": str(readiness_path)},
        "all_ok": bool(doc.get("all_ok", False)),
        "failed_check_count": len(failed),
        "top_failure_reasons": [{"reason": r, "count": c} for r, c in topn],
        "repair_queue_topn": repair_queue,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "failed_check_count": len(failed)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
