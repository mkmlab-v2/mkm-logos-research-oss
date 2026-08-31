#!/usr/bin/env python3
"""Map digested facts to MKM baseline planes (Wiring step, B-track · DR2 explicit status)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.mkm_dr2_digest_wiring_v1 import (  # noqa: E402
    consumer_status_for_wiring,
    count_silent_unwired,
    resolve_wiring_for_fact,
    utc_now,
)

DEFAULT_REGISTRY = ROOT / "docs/final/artifacts/mkm_baseline_plane_registry_v1.json"

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


def _is_wired_status(status: str) -> bool:
    return status in {"BOUND", "BINDING_CANDIDATE"}


def map_digested_facts_to_mkm_plane(
    doc: dict[str, Any],
    *,
    registry: dict[str, dict[str, str]] | None = None,
) -> dict[str, Any]:
    planes = registry or load_plane_registry()
    manifest: list[dict[str, Any]] = []
    out = dict(doc)
    facts = out.get("facts") or []
    origin = str(out.get("source_tier0_path") or "")

    updated_facts: list[dict[str, Any]] = []
    for fact in facts:
        fact_copy = dict(fact)
        wiring = resolve_wiring_for_fact(fact_copy, registry=planes, artifact_origin=origin)
        wiring["consumer_status"] = consumer_status_for_wiring(wiring)
        fact_copy["mkm_wiring"] = wiring

        status = str(wiring.get("wiring_status") or "HOLD_NO_TARGET")
        plane_key = str(wiring.get("baseline_plane") or "external_sota")
        wired = _is_wired_status(status)
        entry: dict[str, Any] = {
            "fact_id": str(fact_copy.get("fact_id") or ""),
            "baseline_plane": plane_key,
            "wired": wired,
            "wiring_status": status,
            "artifact_path": wiring.get("artifact_path") or wiring.get("target_artifact_candidate") or "",
            "artifact_field": wiring.get("artifact_field") or wiring.get("target_section_candidate") or "",
            "assertion": wiring.get("assertion") or "",
            "consumer_status": wiring.get("consumer_status"),
            "gate_status": "not_applicable",
            "detail": str(wiring.get("binding_reason") or ""),
        }
        if status == "BOUND":
            entry["gate_status"] = "pass"
        elif status == "BINDING_CANDIDATE":
            entry["gate_status"] = "skipped"
        manifest.append(entry)
        updated_facts.append(fact_copy)

    out["facts"] = updated_facts
    out["wiring_manifest"] = manifest
    prov = dict(out.get("provenance") or {})
    prov["wiring_at_utc"] = utc_now()
    prov["dr2_silent_unwired_count"] = count_silent_unwired(updated_facts)
    out["provenance"] = prov
    out["authoritative_ssot_auto_apply"] = "LOCKED"
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Wire digested facts to MKM baseline planes (DR2)")
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
    silent = count_silent_unwired(wired.get("facts") or [])
    print(
        json.dumps(
            {
                "ok": silent == 0,
                "out_path": _posix_path(out_path),
                "wired_count": wired_count,
                "manifest_rows": len(wired.get("wiring_manifest", [])),
                "silent_unwired_count": silent,
            },
            ensure_ascii=False,
        )
    )
    return 0 if silent == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
