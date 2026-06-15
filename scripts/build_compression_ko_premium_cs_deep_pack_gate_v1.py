#!/usr/bin/env python3
"""Build zone_ko_premium_cs template manifest + twin gate artifact."""

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

from scripts.compression_ko_premium_cs_deep_pack_v1_lib import (  # noqa: E402
    measure_template_wire_twin,
    resolve_template_match,
)

TEMPLATES = ROOT / "codebook/templates/zone_ko_premium_cs_templates_v1.jsonl"
MANIFEST = ROOT / "codebook/templates/zone_ko_premium_cs_templates_manifest_v1.json"
DEFAULT_GATE_REPORTS = ROOT / "reports/compression_ko_premium_cs_deep_pack_gate_v1_latest.json"
DEFAULT_GATE_ARTIFACT = ROOT / "docs/final/artifacts/compression_ko_premium_cs_deep_pack_gate_v1_latest.json"
SPEC_ARTIFACT = ROOT / "docs/final/artifacts/compression_ko_premium_cs_deep_pack_spec_v1_latest.json"


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
        if line:
            rows.append(json.loads(line))
    return rows


def build_manifest(templates_path: Path, manifest_path: Path) -> dict[str, Any]:
    catalog_hash = _sha256_file(templates_path)
    rows = load_templates(templates_path)
    doc = {
        "schema": "zone_ko_premium_cs_templates_manifest_v1",
        "generated_at_utc": _utc(),
        "catalog_path": templates_path.relative_to(ROOT).as_posix(),
        "row_count": len(rows),
        "catalog_sha256": catalog_hash,
        "template_ids": [r["template_id"] for r in rows],
        "shard_id": "zone_ko_premium_cs_v1",
        "wire_family": "CS_MASK",
        "research_only": True,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return doc


def build_gate(
    *,
    templates_path: Path,
    manifest: dict[str, Any],
    out_reports: Path,
    out_artifact: Path,
) -> dict[str, Any]:
    rows = load_templates(templates_path)
    catalog_sha256 = manifest["catalog_sha256"]
    cases: list[dict[str, Any]] = []
    for r in rows:
        snippet = str(r["snippet"])
        resolved = resolve_template_match(snippet, rows)
        if not resolved:
            cases.append({"template_id": str(r["template_id"]), "ok": False, "error": "no_template_match"})
            continue
        template_id, _ = resolved
        cases.append(
            measure_template_wire_twin(
                original_snippet=snippet,
                template_id=template_id,
                catalog_sha256=catalog_sha256,
                catalog_rows=rows,
            )
        )
    ok_cases = [c for c in cases if c.get("ok")]
    doc: dict[str, Any] = {
        "schema": "compression_ko_premium_cs_deep_pack_gate_v1",
        "generated_at_utc": _utc(),
        "track": "B",
        "research_only": True,
        "hypothesis_tier": "B",
        "send_gate": "HOLD",
        "ready_for_external_send": False,
        "track_a_active_untouched": True,
        "vertical": "ko_premium_cs_turn",
        "vertical_id": "zone_ko_premium_cs_v1",
        "policy_shard": "codebook/shards/zone_ko_premium_cs_v1.json",
        "wire_family": "CS_MASK",
        "vertical_spec": SPEC_ARTIFACT.relative_to(ROOT).as_posix(),
        "separate_from_en_business": "docs/final/artifacts/compression_en_business_deep_pack_gate_v1_latest.json",
        "separate_from_wtt_shortcap": "corpus_tag wtt-premium-cs-customer-v1 hybrid shortcap only",
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
            "note": "CS_MASK masked Korean CS wire. Mask tokens (███) must exact-restore. Not BIZ_MASK / ZF_MASK (FAIL-COMP-004).",
        },
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
        "reproduce": "py scripts/build_compression_ko_premium_cs_deep_pack_gate_v1.py",
    }
    payload = json.dumps(doc, indent=2, ensure_ascii=False) + "\n"
    out_reports.parent.mkdir(parents=True, exist_ok=True)
    out_reports.write_text(payload, encoding="utf-8")
    out_artifact.parent.mkdir(parents=True, exist_ok=True)
    out_artifact.write_text(payload, encoding="utf-8")
    return doc


def main() -> int:
    ap = argparse.ArgumentParser(description="Build ko premium cs deep pack manifest + twin gate")
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
    from scripts.build_compression_ko_premium_cs_deep_pack_spec_v1 import build_spec  # noqa: WPS433

    spec_doc = build_spec()
    SPEC_ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    SPEC_ARTIFACT.write_text(json.dumps(spec_doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    from scripts.build_compression_ko_premium_cs_deep_pack_fallback_spec_v1 import build_fallback_spec  # noqa: WPS433

    fallback_path = ROOT / "docs/final/artifacts/compression_ko_premium_cs_deep_pack_fallback_spec_v1_latest.json"
    fallback_doc = build_fallback_spec(gate_path=args.out_artifact)
    fallback_path.write_text(json.dumps(fallback_doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    from scripts.build_compression_ko_premium_cs_deep_pack_signoff_envelope_v1 import build_envelope  # noqa: WPS433

    signoff_path = ROOT / "docs/final/artifacts/compression_ko_premium_cs_deep_pack_promotion_signoff_envelope_v1_latest.json"
    signoff_doc = build_envelope(gate_path=args.out_artifact)
    signoff_path.write_text(json.dumps(signoff_doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    from scripts.compression_deep_pack_tri_vertical_human_signoff_v1_lib import (  # noqa: WPS433
        reconcile_from_tri_signoff_record,
    )

    reconcile_from_tri_signoff_record()
    from scripts.build_compression_ko_premium_cs_deep_pack_signoff_checklist_v1 import build_checklist  # noqa: WPS433

    checklist_path = ROOT / "docs/final/artifacts/compression_ko_premium_cs_deep_pack_signoff_checklist_v1_latest.json"
    checklist_doc = build_checklist(
        gate_path=args.out_artifact,
        envelope_path=signoff_path,
        fallback_path=fallback_path,
        spec_path=SPEC_ARTIFACT,
    )
    checklist_path.write_text(json.dumps(checklist_doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "manifest": str(args.manifest),
                "gate_artifact": str(args.out_artifact),
                "exact_restore": gate["summary"]["exact_restore_pass_count"],
                "case_count": gate["summary"]["case_count"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
