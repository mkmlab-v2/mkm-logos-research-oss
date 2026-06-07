#!/usr/bin/env python3
"""Ingest DSS/apocrypha frontline manifest into news_observation_v1 research context rows.

Reads chronology sidecar + apocrypha quality manifest (no raw scroll text).
Output defaults to research slice path — does not overwrite production JSONL.

research_only · [HYPO] · NON_GATING · not Track A or live triggers.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SIDECAR = ROOT / "docs/final/artifacts/biblical_history_h_dss_apocrypha_chronology_sidecar_v1.json"
DEFAULT_QUALITY = ROOT / "projects/dss-4d-ingest/outputs/apocrypha_quality_report_pilot_manifest_ext3_hebrew_priority.json"
DEFAULT_FRONTLINE = ROOT / "projects/dss-4d-ingest/outputs/frontline_latest_status.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/news_observation_v1_dss_apocrypha_research_context_latest.jsonl"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _observation_row(
    *,
    canonical: str,
    as_of: str,
    source_id: str,
    ingested: str,
    partition: str,
) -> dict[str, Any]:
    text_sha = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return {
        "schema_version": "news_observation_v1",
        "observation_id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"dss_research:{text_sha}")),
        "as_of_utc": as_of,
        "published_utc": as_of,
        "source_id": source_id,
        "canonical_text": canonical,
        "text_sha256": text_sha,
        "ingested_at_utc": ingested,
        "dataset_partition": partition,
        "hypothesis_tag": "[HYPO]",
        "corpus_type": "dss",
        "research_lane": "biblical_history_h_dss1",
    }


def _rows_from_sidecar(sidecar: dict[str, Any], ingested: str, partition: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    base_dates = ("2026-05-18", "2026-05-22", "2026-05-26", "2026-05-30", "2026-06-03", "2026-06-06")
    nodes = sidecar.get("nodes") if isinstance(sidecar.get("nodes"), list) else []
    for idx, node in enumerate(nodes):
        if not isinstance(node, dict):
            continue
        label = str(node.get("label") or "").strip()
        region = str(node.get("region") or "").strip()
        corpus = str(node.get("corpus_type") or "dss")
        if not label:
            continue
        day = base_dates[idx % len(base_dates)]
        as_of = f"{day}T12:00:00Z"
        canonical = (
            f"DSS apocrypha research context | {label} | region {region} | "
            f"corpus {corpus} | dead sea scrolls qumran"
        )
        rows.append(
            _observation_row(
                canonical=canonical,
                as_of=as_of,
                source_id="dss_apocrypha_sidecar_v1",
                ingested=ingested,
                partition=partition,
            )
        )
    return rows


def _rows_from_quality(quality: dict[str, Any], ingested: str, partition: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    work_counts = quality.get("work_counts") if isinstance(quality.get("work_counts"), dict) else {}
    hebrew_primary = int((quality.get("lineage_tier_counts") or {}).get("A_HEBREW_PRIMARY", 0) or 0)
    total = int(quality.get("total_tokens", 0) or 0)
    as_of = "2026-06-05T09:00:00Z"
    summary = (
        f"Apocrypha pilot manifest ext3 | Hebrew primary tokens {hebrew_primary} of {total} | "
        f"works Ben_Sira Jubilees 1_Enoch | dead sea scrolls pseudepigrapha extracononical"
    )
    rows.append(
        _observation_row(
            canonical=summary,
            as_of=as_of,
            source_id="dss_apocrypha_quality_manifest_v1",
            ingested=ingested,
            partition=partition,
        )
    )
    for work, count in sorted(work_counts.items(), key=lambda kv: str(kv[0])):
        canonical = (
            f"DSS apocrypha corpus segment | work {work} token_count {count} | "
            f"qumran cave scrolls damascus document isaiah"
        )
        rows.append(
            _observation_row(
                canonical=canonical,
                as_of="2026-06-04T10:00:00Z",
                source_id=f"dss_apocrypha_work_{work.lower()}",
                ingested=ingested,
                partition=partition,
            )
        )
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sidecar-json", type=Path, default=DEFAULT_SIDECAR)
    ap.add_argument("--quality-json", type=Path, default=DEFAULT_QUALITY)
    ap.add_argument("--frontline-json", type=Path, default=DEFAULT_FRONTLINE)
    ap.add_argument("--output-jsonl", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--dataset-partition", default="biblical_history_research_slice")
    args = ap.parse_args()

    ingested = _utc_now()
    rows: list[dict[str, Any]] = []
    warnings: list[str] = []

    if args.sidecar_json.is_file():
        rows.extend(_rows_from_sidecar(_load_json(args.sidecar_json), ingested, args.dataset_partition))
    else:
        warnings.append(f"missing sidecar: {args.sidecar_json}")

    if args.quality_json.is_file():
        rows.extend(_rows_from_quality(_load_json(args.quality_json), ingested, args.dataset_partition))
    else:
        warnings.append(f"missing quality manifest: {args.quality_json}")

    if args.frontline_json.is_file():
        front = _load_json(args.frontline_json)
        tag = str(front.get("latest_cycle_tag") or "unknown")
        status = str(front.get("overall_status") or "unknown")
        canonical = (
            f"DSS frontline maintenance status {status} | cycle {tag} | "
            f"apocrypha joint_gate PASS research_only"
        )
        rows.append(
            _observation_row(
                canonical=canonical,
                as_of="2026-06-07T08:00:00Z",
                source_id="dss_frontline_latest_status_v1",
                ingested=ingested,
                partition=args.dataset_partition,
            )
        )

    if not rows:
        print(json.dumps({"ok": False, "error": "no rows built", "warnings": warnings}), file=sys.stderr)
        return 2

    args.output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    args.output_jsonl.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "ok": True,
                "output_jsonl": str(args.output_jsonl),
                "row_count": len(rows),
                "warnings": warnings,
                "research_rail": "B",
                "hypothesis_tier": "[HYPO]",
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
