#!/usr/bin/env python3
"""Collect aux compression parity probe from share into main reports."""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHARE_DEFAULT = Path("Z:/external_validation_d6_aux")
PROBE_NAME = "compression_cross_host_parity_aux_probe_v1_latest.json"
OUT = ROOT / "reports/compression_cross_host_parity_aux_probe_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--share-root", type=Path, default=SHARE_DEFAULT)
    args = ap.parse_args()
    src = args.share_root / PROBE_NAME
    if not src.exists():
        raise SystemExit(f"missing aux probe on share: {src}")
    shutil.copy2(src, OUT)
    doc = json.loads(OUT.read_text(encoding="utf-8"))
    meta = {
        "schema": "compression_cross_host_parity_aux_collect_v1",
        "generated_at_utc": _utc(),
        "ok": doc.get("status") == "ok",
        "share_root": str(args.share_root).replace("\\", "/"),
        "aux_probe": str(OUT.relative_to(ROOT)),
        "hostname": doc.get("hostname"),
    }
    meta_path = ROOT / "reports/compression_cross_host_parity_aux_collect_v1_latest.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": meta["ok"], "out": str(OUT.relative_to(ROOT))}))
    return 0 if meta["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
