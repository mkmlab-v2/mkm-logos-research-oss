#!/usr/bin/env python3
"""Build zone_hardware_machine prospect twin gate (exact restore + saving axis)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.compression_hardware_machine_deep_pack_v1_lib import (  # noqa: E402
    load_template_catalog,
    measure_template_wire_twin,
    sha256_catalog,
)

DEFAULT_CATALOG = ROOT / "codebook/templates/zone_hardware_machine_templates_prospect_v1.jsonl"
DEFAULT_MANIFEST = ROOT / "codebook/templates/zone_hardware_machine_templates_manifest_v1.json"
DEFAULT_REPORT = ROOT / "reports/zone_hardware_machine_twin_gate_v1_latest.json"
DEFAULT_ARTIFACT = ROOT / "docs/final/artifacts/zone_hardware_machine_twin_gate_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_twin_gate_report(*, catalog_path: Path, manifest_path: Path) -> dict[str, Any]:
    rows = load_template_catalog(catalog_path)
    catalog_hash = sha256_catalog(catalog_path)
    cases: list[dict[str, Any]] = []
    for row in rows:
        snippet = str(row.get("snippet") or "")
        template_id = str(row.get("template_id") or "")
        twin = measure_template_wire_twin(
            original_snippet=snippet,
            template_id=template_id,
            catalog_sha256=catalog_hash,
            catalog_rows=rows,
        )
        cases.append(twin)

    exact_restore_count = sum(1 for c in cases if c.get("exact_restore_ok"))
    saving_rates = [float(c.get("saving_rate") or 0.0) for c in cases]
    gate_pass = exact_restore_count == len(cases) and len(cases) > 0

    manifest = {
        "schema": "zone_hardware_machine_templates_manifest_v1",
        "generated_at_utc": _utc(),
        "shard_id": "zone_hardware_machine",
        "catalog_path": catalog_path.as_posix(),
        "catalog_sha256": catalog_hash,
        "row_count": len(rows),
        "prospect_only": True,
        "send_gate": "HOLD",
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    return {
        "schema": "zone_hardware_machine_twin_gate_v1",
        "generated_at_utc": _utc(),
        "lane": "b_track_hypo",
        "research_only": True,
        "send_gate": "HOLD",
        "track_a_active_untouched": True,
        "merge_policy": "prospect_only_no_auto_merge",
        "catalog_path": catalog_path.as_posix(),
        "manifest_path": manifest_path.as_posix(),
        "catalog_sha256": catalog_hash,
        "row_count": len(rows),
        "twin_gate_exact_restore_all_pass": gate_pass,
        "exact_restore_count": exact_restore_count,
        "saving_rate_avg": round(sum(saving_rates) / len(saving_rates), 6) if saving_rates else 0.0,
        "saving_rate_min": round(min(saving_rates), 6) if saving_rates else 0.0,
        "saving_rate_max": round(max(saving_rates), 6) if saving_rates else 0.0,
        "cases": cases,
        "gate_status": "pass" if gate_pass else "fail",
        "reproduce": "py scripts/build_zone_hardware_machine_twin_gate_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    ap.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--report-out", type=Path, default=DEFAULT_REPORT)
    ap.add_argument("--artifact-out", type=Path, default=DEFAULT_ARTIFACT)
    args = ap.parse_args()

    if not args.catalog.is_file():
        print(f"error: missing catalog: {args.catalog}", file=sys.stderr)
        return 2

    report = build_twin_gate_report(catalog_path=args.catalog.resolve(), manifest_path=args.manifest.resolve())
    payload = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    args.report_out.parent.mkdir(parents=True, exist_ok=True)
    args.report_out.write_text(payload, encoding="utf-8")
    args.artifact_out.parent.mkdir(parents=True, exist_ok=True)
    args.artifact_out.write_text(payload, encoding="utf-8")
    print(json.dumps({"ok": report["gate_status"] == "pass", "gate_status": report["gate_status"]}, indent=2))
    return 0 if report["gate_status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
