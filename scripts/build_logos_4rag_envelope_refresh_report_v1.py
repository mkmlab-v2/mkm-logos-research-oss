#!/usr/bin/env python3
"""Report 4RAG envelope layer refresh status after assemble ([HYPO], B-track)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENVELOPE = ROOT / "docs/final/artifacts/three_lens_sphere_envelope_v1_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_4rag_envelope_refresh_report_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_report(envelope_path: Path) -> dict[str, Any]:
    env = json.loads(envelope_path.read_text(encoding="utf-8-sig"))
    resolved = env.get("rag_layers_resolved") or {}
    layers = ("lexical", "semantic", "temporal", "constitutional")
    layer_rows: dict[str, Any] = {}
    all_ok = True
    for layer in layers:
        entries = resolved.get(layer) if isinstance(resolved.get(layer), list) else []
        present_n = sum(1 for e in entries if isinstance(e, dict) and e.get("present"))
        ok = bool(entries) and present_n == len(entries)
        all_ok = all_ok and ok
        layer_rows[layer] = {
            "passed": ok,
            "entry_count": len(entries),
            "present_count": present_n,
            "tags": [e.get("tag") for e in entries if isinstance(e, dict)],
        }
    manifest = env.get("inputs_manifest") if isinstance(env.get("inputs_manifest"), list) else []
    manifest_present = sum(1 for m in manifest if isinstance(m, dict) and m.get("present"))
    return {
        "schema": "logos_4rag_envelope_refresh_report_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "envelope_path": envelope_path.relative_to(ROOT).as_posix()
        if envelope_path.is_relative_to(ROOT)
        else str(envelope_path),
        "envelope_ts_utc": env.get("ts_utc"),
        "final_action": env.get("final_action"),
        "rag_4e_all_present": all_ok,
        "layers": layer_rows,
        "inputs_manifest_count": len(manifest),
        "inputs_manifest_present": manifest_present,
        "bridge_registry_in_manifest": any(
            isinstance(m, dict)
            and "logos_concept_bridge_registry" in str(m.get("path", ""))
            and m.get("present")
            for m in manifest
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--envelope-json", type=Path, default=DEFAULT_ENVELOPE)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    if not args.envelope_json.is_file():
        raise SystemExit(f"Missing envelope: {args.envelope_json}")
    doc = build_report(args.envelope_json)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["rag_4e_all_present"], "out": str(args.out_json)}, ensure_ascii=False))
    return 0 if doc["rag_4e_all_present"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
