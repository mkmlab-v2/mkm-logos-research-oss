#!/usr/bin/env python3
"""Cross-lane gematria audit: canon anchor vs shadow appendix (9-verse pilot) [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
XREF = ROOT / "reports/shadow_canon_gematria_xref_map_v1_latest.json"
BRIDGE = ROOT / "reports/shadow_appendix_id_bridge_v1_latest.json"
OUT_JSON = ROOT / "reports/shadow_cross_lane_gematria_audit_v1_latest.json"
OUT_MD = ROOT / "reports/shadow_cross_lane_gematria_audit_v1_latest.md"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return {}


def build_audit() -> dict[str, Any]:
    xref = _load(XREF)
    bridge = _load(BRIDGE)
    audits: list[dict[str, Any]] = []
    numeric_eligible = 0
    metadata_only = 0
    line_witness_numeric = 0

    for link in xref.get("links") or []:
        vid = str(link.get("canon_verse_id") or "")
        canon_g = link.get("canon_gematria") or {}
        shadows: list[dict[str, Any]] = []
        for sample in link.get("shadow_gematria_samples") or []:
            eligible = bool(sample.get("numeric_comparison_eligible"))
            if eligible:
                numeric_eligible += 1
            else:
                metadata_only += 1
            shadows.append(
                {
                    "shadow_entry_id": sample.get("shadow_entry_id"),
                    "audit_class": sample.get("audit_class"),
                    "resolve_path": sample.get("resolve_path"),
                    "gematria": sample.get("gematria"),
                    "numeric_comparison_eligible": eligible,
                    "hebrew_delta_vs_canon": sample.get("hebrew_delta_vs_canon"),
                }
            )
        line_witnesses: list[dict[str, Any]] = []
        for lw in link.get("line_witness_samples") or []:
            eligible = bool(lw.get("numeric_comparison_eligible"))
            if eligible:
                line_witness_numeric += 1
            line_witnesses.append(
                {
                    "witness_id": lw.get("witness_id"),
                    "entry_id": lw.get("entry_id"),
                    "scroll": lw.get("scroll"),
                    "line": lw.get("line"),
                    "mapping_status": lw.get("mapping_status"),
                    "comparison_type": lw.get("comparison_type"),
                    "gematria": lw.get("gematria"),
                    "numeric_comparison_eligible": eligible,
                    "hebrew_delta_vs_canon": lw.get("hebrew_delta_vs_canon"),
                }
            )
        has_line = any(lw.get("numeric_comparison_eligible") for lw in line_witnesses)
        has_meta = any(s.get("numeric_comparison_eligible") for s in shadows)
        if has_line:
            interpretation = "line_witness_lexical_proximity"
        elif has_meta:
            interpretation = "numeric_contrast"
        else:
            interpretation = "citation_metadata_only"
        audits.append(
            {
                "canon_verse_id": vid,
                "canon_gematria": canon_g,
                "shadow_count": len(shadows),
                "line_witness_count": len(line_witnesses),
                "numeric_eligible_count": sum(1 for s in shadows if s.get("numeric_comparison_eligible")),
                "line_witness_numeric_eligible_count": sum(
                    1 for lw in line_witnesses if lw.get("numeric_comparison_eligible")
                ),
                "shadows": shadows,
                "line_witnesses": line_witnesses,
                "audit_interpretation": interpretation,
            }
        )

    return {
        "schema": "shadow_cross_lane_gematria_audit_v1",
        "version": "1.1.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "audit_only": True,
        "theology_to_sales_forbidden": True,
        "send_gate": "HOLD",
        "track_wall": {
            "logos_core_mutation_forbidden": True,
            "merge_into_canon_31k_41k": False,
            "track_a_bridge": False,
            "ms_headline_merge_forbidden": True,
        },
        "summary": {
            "pilot_verses": len(audits),
            "total_shadow_samples": sum(a["shadow_count"] for a in audits),
            "numeric_comparison_eligible_samples": numeric_eligible,
            "metadata_only_samples": metadata_only,
            "line_witness_numeric_eligible_samples": line_witness_numeric,
            "bridge_rows": (bridge.get("summary") or {}).get("total_bridge_rows"),
        },
        "sku_positioning": {
            "mainline": "canon_original_language_gematria_audit",
            "appendix": "dss_apocrypha_integrity_numeric_audit",
        },
        "audits": audits,
        "reproduce": "py scripts/build_shadow_cross_lane_gematria_audit_v1.py",
    }


def render_md(doc: dict[str, Any]) -> str:
    sm = doc.get("summary") or {}
    lines = [
        "# Shadow Cross-Lane Gematria Audit (Pilot)",
        "",
        f"- Generated: {doc.get('generated_at_utc')}",
        "- Lane: `track_b_hypo` · `research_only` · `audit_only` · **SEND_GATE: HOLD**",
        "",
        "## Executive finding",
        "",
        f"- Pilot verses: **{sm.get('pilot_verses')}**",
        f"- Shadow samples resolved: **{sm.get('total_shadow_samples')}**",
        f"- Numeric-comparison eligible: **{sm.get('numeric_comparison_eligible_samples')}**",
        f"- Metadata-only citations: **{sm.get('metadata_only_samples')}**",
        f"- Line-witness numeric eligible (11Q5): **{sm.get('line_witness_numeric_eligible_samples')}**",
        "",
        "Line witnesses use `lexical_proximity_not_verified_line` unless mapping_status is "
        "`verified_line_witness`. This is audit contrast, not theological harmonization.",
        "",
        "## Per-verse table",
        "",
        "| Canon verse | Canon Hebrew Σ | Shadow samples | Line witnesses | Numeric eligible | Interpretation |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for a in doc.get("audits") or []:
        cg = a.get("canon_gematria") or {}
        lines.append(
            f"| {a.get('canon_verse_id')} | {cg.get('hebrew_value')} | {a.get('shadow_count')} | "
            f"{a.get('line_witness_count')} | {a.get('line_witness_numeric_eligible_count')} | "
            f"{a.get('audit_interpretation')} |"
        )
    lines.extend(
        [
            "",
            "## Sample shadow rows (first 3 per verse)",
            "",
        ]
    )
    for a in doc.get("audits") or []:
        lines.append(f"### {a.get('canon_verse_id')}")
        for s in (a.get("shadows") or [])[:3]:
            g = s.get("gematria") or {}
            lines.append(
                f"- `{s.get('shadow_entry_id')}` · class={s.get('audit_class')} · "
                f"hebrew={g.get('hebrew_value')} · eligible={s.get('numeric_comparison_eligible')}"
            )
        lines.append("")
    lines.append("---")
    lines.append("Reproduce: `py scripts/build_shadow_cross_lane_gematria_audit_v1.py`")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json-out", type=Path, default=OUT_JSON)
    ap.add_argument("--md-out", type=Path, default=OUT_MD)
    args = ap.parse_args()

    doc = build_audit()
    sm = doc["summary"]
    ok = int(sm.get("pilot_verses") or 0) >= 9 and int(sm.get("total_shadow_samples") or 0) >= 9

    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.md_out.write_text(render_md(doc), encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": ok,
                "pilot_verses": sm.get("pilot_verses"),
                "total_shadow_samples": sm.get("total_shadow_samples"),
                "json_out": str(args.json_out.relative_to(ROOT)),
                "md_out": str(args.md_out.relative_to(ROOT)),
            },
            ensure_ascii=False,
        )
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
