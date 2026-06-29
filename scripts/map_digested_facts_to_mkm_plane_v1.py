#!/usr/bin/env python3
"""Map digested facts to MKM baseline planes (Wiring step, B-track)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_REGISTRY = ROOT / "docs/final/artifacts/mkm_baseline_plane_registry_v1.json"

# Built-in defaults when registry file absent
DEFAULT_PLANES: dict[str, dict[str, str]] = {
    "B0_naive": {
        "artifact_path": "reports/universal_root_phase1a_baseline_compare_v1_latest.json",
        "artifact_field": "methods.B0.raw.english_only_distortion_rate",
    },
    "B3_dual_plane": {
        "artifact_path": "reports/universal_root_phase1a_baseline_compare_v1_latest.json",
        "artifact_field": "methods.B3.primary_value",
    },
    "external_sota": {
        "artifact_path": "",
        "artifact_field": "",
    },
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _posix_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def load_plane_registry(path: Path | None = None) -> dict[str, dict[str, str]]:
    reg_path = (path or DEFAULT_REGISTRY).resolve()
    if reg_path.is_file():
        doc = json.loads(reg_path.read_text(encoding="utf-8"))
        planes = doc.get("planes") or {}
        return {str(k): dict(v) for k, v in planes.items()}
    return dict(DEFAULT_PLANES)


def map_digested_facts_to_mkm_plane(
    doc: dict[str, Any],
    *,
    registry: dict[str, dict[str, str]] | None = None,
) -> dict[str, Any]:
    planes = registry or load_plane_registry()
    manifest: list[dict[str, Any]] = []
    out = dict(doc)
    facts = out.get("facts") or []

    for fact in facts:
        fact_id = str(fact.get("fact_id") or "")
        wiring = fact.get("mkm_wiring")
        if wiring:
            manifest.append(
                {
                    "fact_id": fact_id,
                    "baseline_plane": wiring["baseline_plane"],
                    "wired": True,
                    "artifact_path": wiring["artifact_path"],
                    "artifact_field": wiring["artifact_field"],
                    "assertion": wiring["assertion"],
                    "gate_status": "not_applicable",
                    "detail": "explicit mkm_wiring on fact",
                }
            )
            continue

        plane_key = "external_sota"
        entry = {
            "fact_id": fact_id,
            "baseline_plane": plane_key,
            "wired": False,
            "gate_status": "skipped",
            "detail": "external SOTA only; no MKM assert without explicit wiring",
        }
        manifest.append(entry)

    out["wiring_manifest"] = manifest
    prov = dict(out.get("provenance") or {})
    prov["wiring_at_utc"] = _utc_now()
    out["provenance"] = prov
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Wire digested facts to MKM baseline planes")
    parser.add_argument("--input", type=Path, required=True, help="digested_facts JSON")
    parser.add_argument("--out", type=Path, default=None, help="default: overwrite input")
    parser.add_argument("--registry", type=Path, default=None)
    args = parser.parse_args()

    in_path = args.input.resolve()
    if not in_path.is_file():
        print(json.dumps({"ok": False, "error": f"missing input: {in_path}"}, ensure_ascii=False))
        return 2

    doc = json.loads(in_path.read_text(encoding="utf-8"))
    registry = load_plane_registry(args.registry.resolve() if args.registry else None)
    wired = map_digested_facts_to_mkm_plane(doc, registry=registry)

    out_path = args.out.resolve() if args.out else in_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(wired, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    wired_count = sum(1 for e in wired.get("wiring_manifest", []) if e.get("wired"))
    print(
        json.dumps(
            {
                "ok": True,
                "out_path": _posix_path(out_path),
                "wired_count": wired_count,
                "manifest_rows": len(wired.get("wiring_manifest", [])),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
