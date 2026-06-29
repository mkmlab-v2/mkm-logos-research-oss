#!/usr/bin/env python3
"""Export UTF-8 paste bodies for manual LinkedIn fix (mojibake recovery)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--batch",
        type=Path,
        default=Path("reports/marketing/ip_safe_batch_publish_today_v1.json"),
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("reports/marketing/ip_safe_paste_fix"),
    )
    args = parser.parse_args()
    batch = json.loads(args.batch.read_text(encoding="utf-8"))
    args.out_dir.mkdir(parents=True, exist_ok=True)
    for row in batch:
        (args.out_dir / f"{row['id']}_post.txt").write_text(row["post"], encoding="utf-8")
        (args.out_dir / f"{row['id']}_comment.txt").write_text(row["disclaimer"], encoding="utf-8")
    print(json.dumps({"ok": True, "items": len(batch), "out_dir": str(args.out_dir)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
