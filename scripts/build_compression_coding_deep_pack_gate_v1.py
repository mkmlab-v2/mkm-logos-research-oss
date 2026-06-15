#!/usr/bin/env python3
"""Build zone_f_code template manifest + coding deep pack twin gate artifact.

Twin axis: token saving_rate + exact_restore_ok (Jaccard reported separately).
research_only · SEND_GATE HOLD · no ACTIVE mutation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.compression_coding_deep_pack_v1_lib import (  # noqa: E402
    measure_template_wire_twin,
)

TEMPLATES = ROOT / "codebook/templates/zone_f_code_templates_v1.jsonl"
MANIFEST = ROOT / "codebook/templates/zone_f_code_templates_manifest_v1.json"
DEFAULT_GATE_REPORTS = ROOT / "reports/compression_coding_deep_pack_gate_v1_latest.json"
DEFAULT_GATE_ARTIFACT = ROOT / "docs/final/artifacts/compression_coding_deep_pack_gate_v1_latest.json"

TIER_A_STATUS_NOTE = (
    "Tier A operational pass rate (~86.7%) — Golden-40 and open_structured_long are separate axes; "
    "not a coding deep pack approval metric."
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_templates(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def build_manifest(templates_path: Path, manifest_path: Path) -> dict[str, Any]:
    catalog_hash = _sha256_file(templates_path)
    rows = load_templates(templates_path)
    generated_at = _utc()
    if manifest_path.is_file():
        try:
            prior = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
            if (
                prior.get("catalog_sha256") == catalog_hash
                and int(prior.get("row_count") or -1) == len(rows)
            ):
                generated_at = str(prior.get("generated_at_utc") or generated_at)
        except (json.JSONDecodeError, OSError, TypeError, ValueError):
            pass
    doc = {
        "schema": "zone_f_code_templates_manifest_v1",
        "generated_at_utc": generated_at,
        "catalog_path": templates_path.relative_to(ROOT).as_posix(),
        "row_count": len(rows),
        "catalog_sha256": catalog_hash,
        "template_ids": [r["template_id"] for r in rows],
        "shard_id": "zone_f_code",
        "research_only": True,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return doc


def _run_template_wire_roundtrip(
    text: str,
    *,
    template_id: str,
    catalog_sha256: str,
    catalog_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    return measure_template_wire_twin(
        original_snippet=text,
        template_id=template_id,
        catalog_sha256=catalog_sha256,
        catalog_rows=catalog_rows,
    )


def build_gate(
    *,
    templates_path: Path,
    manifest: dict[str, Any],
    out_reports: Path,
    out_artifact: Path,
) -> dict[str, Any]:
    rows = load_templates(templates_path)
    catalog_sha256 = manifest["catalog_sha256"]
    cases = [
        _run_template_wire_roundtrip(
            str(r["snippet"]),
            template_id=str(r["template_id"]),
            catalog_sha256=catalog_sha256,
            catalog_rows=rows,
        )
        for r in rows
    ]
    ok_cases = [c for c in cases if c.get("ok")]
    doc: dict[str, Any] = {
        "schema": "compression_coding_deep_pack_gate_v1",
        "generated_at_utc": _utc(),
        "track": "B",
        "research_only": True,
        "hypothesis_tier": "B",
        "send_gate": "HOLD",
        "ready_for_external_send": False,
        "track_a_active_untouched": True,
        "vertical": "zone_f_code_coding_deep_pack",
        "policy_shard": "codebook/shards/zone_f_code.json",
        "template_catalog": {
            "jsonl": templates_path.relative_to(ROOT).as_posix(),
            "manifest": MANIFEST.relative_to(ROOT).as_posix(),
            "catalog_sha256": manifest["catalog_sha256"],
            "row_count": manifest["row_count"],
        },
        "roundtrip_path": "template_catalog_wire_v1",
        "twin_metrics_axis": {
            "primary_pair": ["saving_rate", "exact_restore_ok"],
            "secondary_axis": "jaccard_proxy",
            "note": "Template-catalog wire (MASK deep pack). Generic v2 semantic compress is a separate axis. Do not merge Jaccard into exact_restore headline (FAIL-COMP-004).",
        },
        "tier_a_status_note": TIER_A_STATUS_NOTE,
        "adjacent_evidence_not_decision": "docs/final/artifacts/compression_candidate_pool_on_track_a_candidate_v1_latest.json",
        "cases": cases,
        "summary": {
            "case_count": len(cases),
            "cases_ok": len(ok_cases),
            "exact_restore_pass_count": sum(1 for c in ok_cases if c.get("exact_restore_ok")),
            "mean_saving_rate": round(
                sum(float(c.get("saving_rate") or 0.0) for c in ok_cases) / max(1, len(ok_cases)), 6
            ),
            "mean_jaccard_proxy": round(
                sum(float(c.get("jaccard_proxy") or 0.0) for c in ok_cases) / max(1, len(ok_cases)), 6
            ),
        },
        "reproduce": "py scripts/build_compression_coding_deep_pack_gate_v1.py",
    }
    payload = json.dumps(doc, indent=2, ensure_ascii=False) + "\n"
    out_reports.parent.mkdir(parents=True, exist_ok=True)
    out_reports.write_text(payload, encoding="utf-8")
    out_artifact.parent.mkdir(parents=True, exist_ok=True)
    out_artifact.write_text(payload, encoding="utf-8")
    return doc


def main() -> int:
    ap = argparse.ArgumentParser(description="Build coding deep pack manifest + twin gate")
    ap.add_argument("--templates", type=Path, default=TEMPLATES)
    ap.add_argument("--manifest", type=Path, default=MANIFEST)
    ap.add_argument("--out-reports", type=Path, default=DEFAULT_GATE_REPORTS)
    ap.add_argument("--out-artifact", type=Path, default=DEFAULT_GATE_ARTIFACT)
    args = ap.parse_args()
    if not args.templates.is_file():
        print(f"MISSING templates: {args.templates}", file=sys.stderr)
        return 1
    manifest = build_manifest(args.templates, args.manifest)
    gate = build_gate(
        templates_path=args.templates,
        manifest=manifest,
        out_reports=args.out_reports,
        out_artifact=args.out_artifact,
    )
    print(
        json.dumps(
            {
                "ok": True,
                "catalog_sha256": manifest["catalog_sha256"],
                "row_count": manifest["row_count"],
                "exact_restore_pass_count": gate["summary"]["exact_restore_pass_count"],
                "mean_saving_rate": gate["summary"]["mean_saving_rate"],
                "out_reports": str(args.out_reports),
                "out_artifact": str(args.out_artifact),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
