#!/usr/bin/env python3
"""Gate: Edge Encoder TestClient vs real HTTP determinism [HYPO] B-track."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports/edge_encoder_cross_process_determinism_v1_latest.json"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--entry-id", default="pilot_ninth_rib_55deg_v0")
    ap.add_argument("--base-url", default=None, help="Use existing v2 stub; default spawns ephemeral uvicorn.")
    args = ap.parse_args()

    sys.path.insert(0, str(ROOT))
    from scripts.edge_encoder_http_roundtrip_v1_lib import check_cross_process_determinism
    from scripts.edge_encoder_sdk_v1_lib import encode_from_manifest_entry

    result = encode_from_manifest_entry(args.entry_id, workspace_root=ROOT)
    if result.validation_errors:
        print(json.dumps({"ok": False, "errors": result.validation_errors}, ensure_ascii=False))
        return 1

    errors, summary = check_cross_process_determinism(
        result.wire,
        workspace_root=ROOT,
        base_url=args.base_url,
    )
    doc = {"ok": not errors, "errors": errors, "entry_id": args.entry_id, **summary}
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["ok"], "errors": errors}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
