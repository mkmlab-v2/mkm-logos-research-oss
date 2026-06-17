#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "docs" / "final" / "artifacts"
IN_DEFAULT = ART / "a_codeai_fact_lock_public_copy_latest.json"
OUT_DEFAULT = ART / "a_codeai_public_copy_web_payload_latest.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _section_from_copy(copy: dict[str, Any]) -> dict[str, Any]:
    claims = copy.get("claims", [])
    claim_map = {str(c.get("title", "")).lower(): c.get("items", []) for c in claims if isinstance(c, dict)}
    if isinstance(copy.get("claims"), list) and copy["claims"] and not isinstance(copy["claims"][0], dict):
        claim_items = copy.get("claims", [])
        non_claim_items = copy.get("non_claims", [])
    else:
        claim_items = claim_map.get("what we claim", [])
        non_claim_items = claim_map.get("what we do not claim", [])

    return {
        "hero": {
            "title": copy.get("hero"),
            "subtitle": copy.get("subtitle"),
            "status_line": copy.get("status_line"),
        },
        "fact_lock_bullets": copy.get("bullets", []),
        "claims": claim_items,
        "non_claims": non_claim_items,
        "cta": copy.get("cta", {}),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--copy-json", type=Path, default=IN_DEFAULT)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    in_path = args.copy_json if args.copy_json.is_absolute() else ROOT / args.copy_json
    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    src = _read_json(in_path)
    if str(src.get("schema")) != "a_codeai_fact_lock_public_copy_v1":
        raise SystemExit("input schema mismatch")

    copy = src.get("copy", {})
    copy_ko = src.get("copy_ko", {})

    payload = {
        "schema": "a_codeai_public_copy_web_payload_v1",
        "generated_at_utc": _now_utc(),
        "source_copy_json": str(in_path),
        "sections": _section_from_copy(copy),
        "sections_ko": _section_from_copy(copy_ko) if copy_ko else None,
        "meta": {
            "readiness_all_ok": bool(src.get("status", {}).get("readiness_all_ok", False)),
            "executive_read_decision": src.get("status", {}).get("executive_read_decision"),
            "send_gate": src.get("status", {}).get("send_gate", "HOLD"),
            "lane_metrics": src.get("lane_metrics"),
        },
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
