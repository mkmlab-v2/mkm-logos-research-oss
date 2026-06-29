#!/usr/bin/env python3
"""Bridge Phase O Psi abstract nodes to 4AI Sasang roles — structure only [HYPO]."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.btrack_sasang_role_router_v1 import build_psi_role_bridge  # noqa: E402

OUT_DEFAULT = ROOT / "reports/btrack_sasang_psi_role_bridge_v1_latest.json"
PSI_DEFAULT = ROOT / "reports/logos_psi_logic_extraction_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--psi", type=Path, default=PSI_DEFAULT)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    if not args.psi.is_file():
        print("psi_missing", file=sys.stderr)
        return 1

    psi_doc = json.loads(args.psi.read_text(encoding="utf-8-sig"))
    doc = build_psi_role_bridge(psi_doc)
    doc["generated_at_utc"] = _utc()
    doc["psi_path"] = str(args.psi.resolve())
    doc["reproduce_cmd"] = "py scripts/build_btrack_sasang_psi_role_bridge_v1.py"

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"ok": doc["bridge_ok"], "nodes": len(doc["bridged_nodes"]), "out": str(args.out)},
            ensure_ascii=False,
        )
    )
    return 0 if doc["bridge_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
