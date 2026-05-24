#!/usr/bin/env python3
"""Validate wire envelope v1 JSON against schema (+ optional live build probe)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SCHEMA = ROOT / "docs/final/schemas/mkm_inter_agent_wire_envelope_v1.schema.json"
EXAMPLE = ROOT / "docs/final/artifacts/fixtures/mkm_inter_agent_wire_envelope_v1.example.json"


def validate_doc(doc: dict[str, Any], schema_path: Path = SCHEMA) -> dict[str, Any]:
    import jsonschema

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(doc)
    return {"ok": True, "schema": schema_path.relative_to(ROOT).as_posix()}


def probe_live_envelope() -> dict[str, Any]:
    from fastapi.testclient import TestClient

    from scripts.compression_token_api_v2_stub import app

    client = TestClient(app)
    r = client.post(
        "/v1/research/mkm_inter_agent_wire/turn",
        json={"text": "logos bible mercy alpha beta", "turn_id": 1},
    )
    if r.status_code != 200:
        return {"ok": False, "error": f"turn_status_{r.status_code}"}
    env = r.json().get("envelope") or {}
    validate_doc(env)
    return {"ok": True, "envelope_utf8_byte_len": r.json().get("envelope_utf8_byte_len")}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", type=Path, help="Envelope JSON file to validate")
    ap.add_argument("--live-probe", action="store_true", help="Also validate API-built envelope")
    args = ap.parse_args()

    results: list[dict[str, Any]] = []
    path = args.json or EXAMPLE
    if path.is_file():
        doc = json.loads(path.read_text(encoding="utf-8"))
        results.append({"source": str(path.relative_to(ROOT)), **validate_doc(doc)})
    else:
        print(json.dumps({"ok": False, "error": f"missing {path}"}))
        return 2

    if args.live_probe:
        results.append({"source": "live_api_turn", **probe_live_envelope()})

    ok = all(r.get("ok") for r in results)
    print(json.dumps({"ok": ok, "validations": results}, ensure_ascii=False))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
