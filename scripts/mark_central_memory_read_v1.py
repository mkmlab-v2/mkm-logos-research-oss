#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main() -> int:
    ap = argparse.ArgumentParser(description="Write central-memory read acknowledgement artifact.")
    ap.add_argument("--workspace-root", default="C:/workspace")
    ap.add_argument("--reason", default="trigger_phrase")
    args = ap.parse_args()

    root = Path(args.workspace_root).resolve()
    out = root / "reports" / "central_memory_read_ack_latest.json"
    out.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "schema": "central_memory_read_ack_v1",
        "acknowledged_at_utc": _now_utc(),
        "reason": str(args.reason),
        "sources": [
            "docs/final/CENTRAL_AGENT_MEMORY_V1.md",
            "AGENTS.md",
            "docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md",
        ],
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"WROTE: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
