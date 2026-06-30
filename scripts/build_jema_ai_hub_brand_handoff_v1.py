#!/usr/bin/env python3
"""Build jema-ai.com /hub JEMA OS brand handoff JSON (CTA surfaces, B-track)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "projects/no1kmedi/public/data/jema_ai_hub_brand_handoff_v1.json"
PUBLIC_COPY = ROOT / "projects/no1kmedi/marketing-site/public-copy.json"
SCHEMA = "jema_ai_hub_brand_handoff_v1"

HUB_CTA_KEYS = (
    "showroom_jemaai",
    "premium_mkmlife",
    "research_logos",
    "jema_os_enterprise",
    "b2b_acodeai",
    "research_mkmlab",
    "clinician_support",
)


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def build_handoff(*, root: Path = ROOT) -> dict[str, Any]:
    brand = _read_json(root / "docs/final/artifacts/jema_os_brand_pointer_v1_latest.json") or {}
    freeze = _read_json(
        root / "docs/final/artifacts/logos_corpus_knowledge_freeze_manifest_v1_latest.json"
    ) or {}
    hybrid = _read_json(root / "reports/logos_hybrid_middleware_chain_v1_latest.json") or {}
    envelope_skim = _read_json(
        root / "projects/no1kmedi/public/data/jema_os_coordinate_envelope_skim_v1.json"
    ) or {}
    copy = _read_json(PUBLIC_COPY if PUBLIC_COPY.is_file() else root / PUBLIC_COPY) or {}

    public_brand = brand.get("public_brand") if isinstance(brand.get("public_brand"), dict) else {}
    internal = brand.get("internal_kernel") if isinstance(brand.get("internal_kernel"), dict) else {}
    hub_meta = copy.get("_meta") if isinstance(copy.get("_meta"), dict) else {}

    send_gate = hybrid.get("send_gate") or brand.get("send_gate") or "HOLD"
    pipeline_ok = bool(hybrid.get("ok")) if hybrid else False

    freeze_ok = False
    sidecar_count: int | None = None
    lemma_lines: int | None = None
    assets = freeze.get("assets") if isinstance(freeze.get("assets"), dict) else {}
    sidecar_asset = assets.get("sidecar_v2_corpus_full") or {}
    lemma_asset = assets.get("lemma_verse_edges_jsonl") or {}
    coverage = freeze.get("coverage_report") if isinstance(freeze.get("coverage_report"), dict) else {}
    if sidecar_asset.get("verse_count") is not None:
        sidecar_count = int(sidecar_asset["verse_count"])
    elif coverage.get("corpus_verse_count") is not None:
        sidecar_count = int(coverage["corpus_verse_count"])
    if lemma_asset.get("line_count") is not None:
        lemma_lines = int(lemma_asset["line_count"])
    if freeze.get("schema") and sidecar_count and lemma_lines:
        freeze_ok = sidecar_count >= 30_000 and lemma_lines >= 290_000

    hub_links = copy.get("hub_links") if isinstance(copy.get("hub_links"), dict) else {}
    cta_links: list[dict[str, str]] = []
    for key in HUB_CTA_KEYS:
        row = hub_links.get(key)
        if not isinstance(row, dict):
            continue
        href = str(row.get("href") or "").strip()
        label = str(row.get("label") or "").strip()
        sublabel = str(row.get("sublabel") or "").strip()
        if href and label:
            cta_links.append({"key": key, "href": href, "label": label, "sublabel": sublabel})

    return {
        "schema": SCHEMA,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "surface": {
            "domain": str(hub_meta.get("public_domain") or "jema-ai.com"),
            "path": "/hub",
            "mode": "hub_brand_entry_l0",
            "hub_llm_enabled": False,
            "metering_enabled": False,
            "track_a_promotion_allowed": False,
        },
        "brand": {
            "hub_display": str(hub_meta.get("brand") or "JEMA AI"),
            "public_os_display": str(public_brand.get("display") or "JEMA OS v2"),
            "public_os_name": str(public_brand.get("name") or "JEMA OS"),
            "internal_kernel": str(internal.get("name") or "MKM"),
            "rename_policy": "pointer_only_no_global_rename",
        },
        "governance": {
            "send_gate": send_gate,
            "research_only": bool(hybrid.get("research_only", True)),
            "disclaimer_ko": (
                "허브는 도메인 분기·관측 안내만 제공합니다. "
                "의료·진단·투자·실거래 지시가 아닙니다."
            ),
            "disclaimer_en": (
                "Hub routes to observation surfaces only. "
                "Not medical, diagnostic, investment, or live-trading guidance."
            ),
        },
        "cta_links": cta_links,
        "pipeline_snapshot": {
            "hybrid_chain_ok": pipeline_ok,
            "freeze_manifest_ok": freeze_ok,
            "sidecar_verse_count": sidecar_count,
            "lemma_edge_line_count": lemma_lines,
            "cloud_llm_called": bool(hybrid.get("cloud_llm_called", False)),
        },
        "pointers": {
            "brand_pointer": "docs/final/artifacts/jema_os_brand_pointer_v1_latest.json",
            "domain_portfolio": "docs/final/MKM_DOMAIN_PORTFOLIO_POINTER_V1.md",
            "public_copy": "projects/no1kmedi/marketing-site/public-copy.json",
            "mkmlife_oracle_handoff": "https://mkmlife.com/data/mkmlife_oracle_sphere_jema_os_handoff_v1.json",
            "coordinate_envelope_skim": (
                "projects/no1kmedi/public/data/jema_os_coordinate_envelope_skim_v1.json"
            ),
            "coordinate_envelope_deep": (
                "projects/no1kmedi/public/data/jema_os_coordinate_envelope_deep_v1.json"
            ),
            "coordinate_envelope_read_depth": envelope_skim.get("read_depth") or "skim",
        },
        "reproduce": "py scripts/build_jema_ai_hub_brand_handoff_v1.py",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    payload = build_handoff(root=args.root)
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"

    if args.dry_run:
        print(text, end="")
        return 0

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
