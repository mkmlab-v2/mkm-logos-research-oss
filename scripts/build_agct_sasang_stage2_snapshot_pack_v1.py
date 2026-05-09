#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _fmt_utc(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description="Build dated snapshot pack for AGCT Sasang Stage2 operations.")
    root = Path(__file__).resolve().parents[1]
    ap.add_argument(
        "--output-root",
        type=Path,
        default=root / "reports" / "agct_sasang_stage2_snapshots",
    )
    ns = ap.parse_args()

    ts = _utc_now()
    tag = ts.strftime("%Y%m%d")
    out_dir = ns.output_root / tag
    out_dir.mkdir(parents=True, exist_ok=True)

    source_files = [
        root / "docs" / "final" / "artifacts" / "agct_sasang_stage2_operating_mode_v1.json",
        root / "reports" / "agct_sasang_stage2_fasttrack_gate_v1_latest.json",
        root / "reports" / "agct_sasang_stage2_promotion_gate_v1_latest.json",
        root / "reports" / "agct_sasang_stage2_d7_checkpoint_v1_latest.json",
        root / "reports" / "agct_sasang_global_status_board_v1_latest.json",
        root / "reports" / "mkm_global_coordinator_v1_latest.json",
        root / "reports" / "sasang_rule_based_response_v1_latest.md",
    ]

    copied = []
    for src in source_files:
        if not src.exists():
            continue
        dst = out_dir / src.name
        shutil.copy2(src, dst)
        copied.append(str(dst.resolve()))

    payload = {
        "schema": "agct_sasang_stage2_snapshot_pack_v1",
        "generated_at_utc": _fmt_utc(ts),
        "snapshot_tag": tag,
        "track": "B_TRACK",
        "snapshot_dir": str(out_dir.resolve()),
        "copied_files": copied,
    }
    index_path = out_dir / "snapshot_index.json"
    index_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {index_path.resolve()} files={len(copied)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
