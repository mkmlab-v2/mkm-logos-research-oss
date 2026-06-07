#!/usr/bin/env python3
"""Gate-gated DSS/apocrypha token NDJSON manifest → news_observation_v1 research rows.

Never embeds raw scroll/token text in canonical_text — metadata summaries only.
When authority_readiness is not READY or NDJSON paths are missing, emits WATCH gate rows.

research_only · [HYPO] · NON_GATING · not Track A or live triggers.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AUTH = ROOT / "projects/dss-4d-ingest/outputs/authority_readiness_command_center_followup_20260327_h_ext3.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/news_observation_v1_dss_ndjson_research_context_latest.jsonl"
DEFAULT_MERGE_TARGET = ROOT / "docs/final/artifacts/news_observation_v1_dss_apocrypha_research_context_latest.jsonl"
_WORK_RESONANCE_KEYWORDS: dict[str, str] = {
    "Ben_Sira": "apocrypha pseudepigrapha dead sea scrolls qumran extracanonical",
    "Jubilees": "apocrypha septuagint qumran cave scrolls dead sea",
    "1_Enoch": "pseudepigrapha apocrypha qumran dead sea scrolls cave 1",
    "isaiah": "isaiah scroll dead sea scrolls qumran cave",
    "damascus": "damascus document dead sea scrolls qumran",
}


def _work_label(obj: dict[str, Any]) -> str:
    return str(obj.get("work") or obj.get("work_id") or obj.get("source_work") or "unknown")


def _scroll_label(obj: dict[str, Any]) -> str:
    return str(obj.get("scroll_id") or obj.get("book") or "")


def _canonical_for_chunk(
    *,
    path_stem: str,
    work: str,
    chunk_idx: int,
    chunk_size: int,
    token_start: int,
    token_end: int,
    tiers: Counter[str],
    scripts: Counter[str],
    scroll_id: str,
) -> str:
    kw = _WORK_RESONANCE_KEYWORDS.get(work, "dead sea scrolls qumran apocrypha pseudepigrapha cave 1")
    tier_top = tiers.most_common(2)
    tier_txt = ",".join(f"{k}:{v}" for k, v in tier_top) if tier_top else "unknown"
    script_top = scripts.most_common(2)
    script_txt = ",".join(f"{k}:{v}" for k, v in script_top) if script_top else "unknown"
    scroll_part = f" scroll {scroll_id}" if scroll_id else ""
    return (
        f"DSS apocrypha token surface chunk | {kw} | file {path_stem} | work {work}{scroll_part} | "
        f"chunk {chunk_idx} size {chunk_size} | tokens {token_start}-{token_end} | "
        f"tiers {tier_txt} | scripts {script_txt} | "
        f"isaiah damascus document septuagint extracanonical | research_only"
    )


def _rows_full_surface_chunk(
    path: Path,
    *,
    chunk_size: int,
    max_rows_per_file: int,
    ingested: str,
    partition: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    stem = path.stem
    buffers: dict[tuple[str, str], list[dict[str, Any]]] = {}
    chunk_idx: dict[tuple[str, str], int] = {}

    def _flush(key: tuple[str, str], buf: list[dict[str, Any]]) -> None:
        if not buf:
            return
        work, scroll = key
        idx = chunk_idx.get(key, 0) + 1
        chunk_idx[key] = idx
        tiers: Counter[str] = Counter()
        scripts: Counter[str] = Counter()
        token_indices: list[int] = []
        for rec in buf:
            tiers[str(rec.get("lineage_tier") or rec.get("tier") or "unknown")] += 1
            scripts[str(rec.get("script") or rec.get("lang") or "unknown")] += 1
            try:
                token_indices.append(int(rec.get("token_index") or 0))
            except (TypeError, ValueError):
                pass
        token_start = min(token_indices) if token_indices else 0
        token_end = max(token_indices) if token_indices else 0
        canonical = _canonical_for_chunk(
            path_stem=stem,
            work=work,
            chunk_idx=idx,
            chunk_size=len(buf),
            token_start=token_start,
            token_end=token_end,
            tiers=tiers,
            scripts=scripts,
            scroll_id=scroll,
        )
        day_bucket = (idx + hash(work) % 28) % 28
        as_of = f"2026-05-{1 + day_bucket:02d}T12:00:00Z"
        rows.append(
            _observation_row(
                canonical=canonical,
                as_of=as_of,
                source_id=f"dss_ndjson_surface_{stem}_{work}_{idx}",
                ingested=ingested,
                partition=partition,
            )
        )

    for line in path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw:
            continue
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict):
            continue
        work = _work_label(obj)
        scroll = _scroll_label(obj)
        key = (work, scroll)
        buffers.setdefault(key, []).append(obj)
        if len(buffers[key]) >= chunk_size:
            if len(rows) >= max_rows_per_file:
                continue
            _flush(key, buffers[key])
            buffers[key] = []
    for key, buf in buffers.items():
        if len(rows) >= max_rows_per_file:
            break
        if buf:
            _flush(key, buf)
    return rows[:max_rows_per_file]


def _canonical_for_manifest_summary(summary: dict[str, Any]) -> str:
    work = str(summary.get("top_work") or "unknown")
    kw = _WORK_RESONANCE_KEYWORDS.get(work, "dead sea scrolls qumran apocrypha pseudepigrapha cave 1")
    return (
        f"DSS apocrypha corpus manifest | {kw} | records {summary['record_count']} | "
        f"top_work {work} | work_variants {summary['work_variants']} | "
        f"isaiah damascus document septuagint | research_only"
    )


DEFAULT_NDJSON_CANDIDATES = (
    "projects/dss-4d-ingest/outputs/apocrypha_tokens_pilot_manifest_ext3_hebrew_priority.ndjson",
    "projects/dss-4d-ingest/outputs/apocrypha_tokens_pilot_manifest_ext2_weighted.ndjson",
    "projects/dss-4d-ingest/outputs/dss_tokens_ci_smoke_manifest_tf4.ndjson",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _observation_row(*, canonical: str, as_of: str, source_id: str, ingested: str, partition: str) -> dict[str, Any]:
    text_sha = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return {
        "schema_version": "news_observation_v1",
        "observation_id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"dss_ndjson_research:{text_sha}")),
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


def _canonical_for_work_surface(work: str, stats: dict[str, Any]) -> str:
    kw = _WORK_RESONANCE_KEYWORDS.get(work, "dead sea scrolls qumran apocrypha pseudepigrapha cave 1")
    tier_bits = ", ".join(f"{k}:{v}" for k, v in sorted(stats.get("tier_counts", {}).items()))
    script_bits = ", ".join(f"{k}:{v}" for k, v in sorted(stats.get("script_counts", {}).items()))
    ref_sample = stats.get("ref_sample") or []
    ref_hint = ref_sample[0] if ref_sample else "n/a"
    return (
        f"DSS apocrypha work surface | {kw} | work {work} | tokens {stats['token_count']} | "
        f"unique_refs {stats['unique_ref_count']} | tiers {tier_bits} | scripts {script_bits} | "
        f"ref_sample {ref_hint} | research_only"
    )


def _work_surfaces_from_ndjson(path: Path, *, max_work_rows: int) -> list[dict[str, Any]]:
    buckets: dict[str, dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw:
            continue
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict):
            continue
        work = str(obj.get("work") or obj.get("work_id") or obj.get("source_work") or "unknown")
        bucket = buckets.setdefault(
            work,
            {
                "path": str(path),
                "work": work,
                "token_count": 0,
                "tier_counts": Counter(),
                "script_counts": Counter(),
                "refs": set(),
            },
        )
        bucket["token_count"] += 1
        tier = str(obj.get("lineage_tier") or obj.get("tier") or "unknown")
        bucket["tier_counts"][tier] += 1
        script = str(obj.get("script") or obj.get("lang") or "unknown")
        bucket["script_counts"][script] += 1
        ref = str(obj.get("ref") or obj.get("reference") or "").strip()
        if ref:
            bucket["refs"].add(ref)

    surfaces: list[dict[str, Any]] = []
    for work in sorted(buckets.keys())[:max_work_rows]:
        bucket = buckets[work]
        surfaces.append(
            {
                "path": bucket["path"],
                "work": work,
                "token_count": bucket["token_count"],
                "tier_counts": dict(bucket["tier_counts"]),
                "script_counts": dict(bucket["script_counts"]),
                "unique_ref_count": len(bucket["refs"]),
                "ref_sample": sorted(bucket["refs"])[:3],
            }
        )
    return surfaces


def _summarize_ndjson(path: Path, max_sample: int) -> dict[str, Any]:
    works: Counter[str] = Counter()
    tiers: Counter[str] = Counter()
    scripts: Counter[str] = Counter()
    record_count = 0
    sample_keys: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw:
            continue
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict):
            continue
        record_count += 1
        if len(sample_keys) < max_sample:
            sample_keys.update(k for k in obj.keys() if k not in ("text", "token_text", "surface", "lemma"))
        work = str(obj.get("work") or obj.get("work_id") or obj.get("source_work") or "unknown")
        works[work] += 1
        tier = str(obj.get("lineage_tier") or obj.get("tier") or "unknown")
        tiers[tier] += 1
        script = str(obj.get("script") or obj.get("lang") or "unknown")
        scripts[script] += 1
    top_work = works.most_common(1)[0][0] if works else "none"
    return {
        "path": str(path),
        "record_count": record_count,
        "top_work": top_work,
        "work_variants": len(works),
        "lineage_tier_variants": len(tiers),
        "script_variants": len(scripts),
        "metadata_keys_sample": sorted(sample_keys)[:12],
    }


def _gate_row(
    *,
    mode: str,
    auth_status: str,
    ingested: str,
    partition: str,
    detail: str,
) -> dict[str, Any]:
    canonical = (
        f"DSS NDJSON ingest gate {mode} | authority_readiness {auth_status} | "
        f"{detail} | dead sea scrolls qumran research_only"
    )
    return _observation_row(
        canonical=canonical,
        as_of="2026-06-07T10:00:00Z",
        source_id="dss_ndjson_ingest_gate_v1",
        ingested=ingested,
        partition=partition,
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--authority-json", type=Path, default=DEFAULT_AUTH)
    ap.add_argument("--ndjson-path", action="append", default=[], help="Explicit NDJSON file(s); repeatable.")
    ap.add_argument("--max-manifest-rows", type=int, default=8)
    ap.add_argument(
        "--ingest-mode",
        choices=("manifest_summary", "work_surface", "full_surface_chunk"),
        default="manifest_summary",
        help="manifest_summary=1 row per file; work_surface=1 row per work; full_surface_chunk=metadata chunks.",
    )
    ap.add_argument("--max-work-rows", type=int, default=64, help="Cap work_surface rows per NDJSON file.")
    ap.add_argument("--chunk-size", type=int, default=250, help="Tokens per surface chunk (full_surface_chunk only).")
    ap.add_argument(
        "--max-surface-rows-per-file",
        type=int,
        default=120,
        help="Cap surface rows per NDJSON file (full_surface_chunk only).",
    )
    ap.add_argument("--output-jsonl", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--merge-into", type=Path, default=None, help="Append built rows to this JSONL after write.")
    ap.add_argument("--dataset-partition", default="biblical_history_research_slice")
    args = ap.parse_args()

    ingested = _utc_now()
    rows: list[dict[str, Any]] = []
    warnings: list[str] = []
    ingest_mode = "WATCH"

    auth_status = "MISSING"
    if args.authority_json.is_file():
        auth = _load_json(args.authority_json)
        auth_status = str(auth.get("status") or "UNKNOWN").upper()
    else:
        warnings.append(f"missing authority json: {args.authority_json}")

    ndjson_paths: list[Path] = [Path(p) for p in args.ndjson_path]
    if not ndjson_paths:
        ndjson_paths = [ROOT / rel for rel in DEFAULT_NDJSON_CANDIDATES]
    existing = [p for p in ndjson_paths if p.is_file()]

    if auth_status != "READY":
        rows.append(
            _gate_row(
                mode="BLOCKED",
                auth_status=auth_status,
                ingested=ingested,
                partition=args.dataset_partition,
                detail="raw ndjson text ingest withheld until authority_readiness READY",
            )
        )
    elif not existing:
        rows.append(
            _gate_row(
                mode="WATCH",
                auth_status=auth_status,
                ingested=ingested,
                partition=args.dataset_partition,
                detail="READY but no ndjson manifests on disk; metadata-only gate row",
            )
        )
        warnings.extend(f"missing ndjson: {p}" for p in ndjson_paths if not p.is_file())
    else:
        if args.ingest_mode == "full_surface_chunk":
            ingest_mode = "FULL_SURFACE_CHUNK"
            for path in existing:
                rows.extend(
                    _rows_full_surface_chunk(
                        path,
                        chunk_size=max(1, args.chunk_size),
                        max_rows_per_file=max(1, args.max_surface_rows_per_file),
                        ingested=ingested,
                        partition=args.dataset_partition,
                    )
                )
        elif args.ingest_mode == "work_surface":
            ingest_mode = "WORK_SURFACE"
            for path in existing:
                for surface in _work_surfaces_from_ndjson(path, max_work_rows=args.max_work_rows):
                    canonical = _canonical_for_work_surface(str(surface["work"]), surface)
                    rows.append(
                        _observation_row(
                            canonical=canonical,
                            as_of="2026-06-07T11:00:00Z",
                            source_id=f"dss_ndjson_work_{Path(path).stem}_{surface['work']}",
                            ingested=ingested,
                            partition=args.dataset_partition,
                        )
                    )
        else:
            ingest_mode = "MANIFEST_SUMMARY"
            for summary in [_summarize_ndjson(p, max_sample=8) for p in existing][: args.max_manifest_rows]:
                canonical = _canonical_for_manifest_summary(summary)
                rows.append(
                    _observation_row(
                        canonical=canonical,
                        as_of="2026-06-07T11:00:00Z",
                        source_id=f"dss_ndjson_manifest_{Path(summary['path']).stem}",
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

    if args.merge_into is not None:
        prior = ""
        if args.merge_into.is_file():
            prior = args.merge_into.read_text(encoding="utf-8")
            if prior and not prior.endswith("\n"):
                prior += "\n"
        args.merge_into.parent.mkdir(parents=True, exist_ok=True)
        args.merge_into.write_text(
            prior + "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
            encoding="utf-8",
        )

    print(
        json.dumps(
            {
                "ok": True,
                "output_jsonl": str(args.output_jsonl),
                "row_count": len(rows),
                "ingest_mode": ingest_mode,
                "authority_status": auth_status,
                "ndjson_files_found": len(existing),
                "chunk_size": args.chunk_size if ingest_mode == "FULL_SURFACE_CHUNK" else None,
                "max_surface_rows_per_file": args.max_surface_rows_per_file
                if ingest_mode == "FULL_SURFACE_CHUNK"
                else None,
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
