#!/usr/bin/env python3
"""Write alert artifact for Vibe gate failure/success."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
OUT_JSON = ART / "vibe_gate_alert_latest.json"
OUT_MD = ART / "vibe_gate_alert_latest.md"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--status", required=True, choices=["ok", "fail"])
    parser.add_argument("--stage", required=True)
    parser.add_argument("--message", required=True)
    parser.add_argument("--exit-code", type=int, default=0)
    args = parser.parse_args()

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    data = {
        "schema": "vibe_gate_alert_v1",
        "generated_at_utc": now,
        "scope": "research_only",
        "status": args.status,
        "stage": args.stage,
        "message": args.message,
        "exit_code": args.exit_code,
    }
    OUT_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    OUT_MD.write_text(
        "\n".join(
            [
                "# Vibe Gate Alert (Latest)",
                "",
                f"- Generated (UTC): {now}",
                f"- Status: {args.status}",
                f"- Stage: {args.stage}",
                f"- Exit code: {args.exit_code}",
                f"- Message: {args.message}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"written: {OUT_JSON}")
    print(f"written: {OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

