"""[HYPO] Shadow-only corpus_tag → zone_h_en_business_v1 router bind (B-track).

Does NOT patch scripts/core/domain_router.py production route().
research_only · BIZ_MASK wire family · FAIL-COMP-004 axis separation.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.core.domain_router import DomainSpecificRouter, ShardRoute
from scripts.extract_zone_h_en_business_template_seeds_v1_lib import (
    iter_jsonl_rows,
    row_text_blobs,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BIND_SPEC = ROOT / "docs/final/artifacts/compression_en_business_shadow_router_bind_v1.json"
DEFAULT_SHARDS = ROOT / "codebook/shards"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_shadow_bind_spec(path: Path | None = None) -> dict[str, Any]:
    spec_path = path or DEFAULT_BIND_SPEC
    if not spec_path.is_file():
        return {}
    doc = json.loads(spec_path.read_text(encoding="utf-8"))
    return doc if isinstance(doc, dict) else {}


def shadow_corpus_tags(spec: dict[str, Any]) -> set[str]:
    tags: set[str] = set()
    primary = str(spec.get("corpus_tag_primary") or "").strip()
    if primary:
        tags.add(primary)
    for t in spec.get("corpus_tag_aliases") or []:
        s = str(t).strip()
        if s:
            tags.add(s)
    return tags


def corpus_tag_triggers_shadow(corpus_tag: str | None, spec: dict[str, Any]) -> bool:
    tag = str(corpus_tag or "").strip()
    if not tag:
        return False
    return tag in shadow_corpus_tags(spec)


def resolve_shadow_shard_id(corpus_tag: str | None, spec: dict[str, Any]) -> str | None:
    if not corpus_tag_triggers_shadow(corpus_tag, spec):
        return None
    sid = str(spec.get("shadow_shard_id") or "").strip()
    return sid or None


def shard_route_to_dict(route: ShardRoute) -> dict[str, Any]:
    return {
        "shard_id": route.shard_id,
        "domain": route.domain,
        "hangul_principle": route.hangul_principle,
    }


def shadow_bind_integrity_flags(
    *,
    text: str,
    corpus_tag: str | None,
    baseline_route: ShardRoute,
    router: DomainSpecificRouter,
    spec: dict[str, Any] | None = None,
    spec_path: Path | None = None,
) -> dict[str, Any]:
    """Metadata-only shadow bind flags for v2 stub (does not mutate production route)."""
    doc = spec if spec is not None else load_shadow_bind_spec(spec_path)
    tag = str(corpus_tag or "").strip()
    if not corpus_tag_triggers_shadow(tag, doc):
        return {}
    cmp = compare_baseline_vs_shadow(text, corpus_tag=tag, router=router, spec=doc)
    bind_path = (spec_path or DEFAULT_BIND_SPEC)
    try:
        bind_rel = bind_path.relative_to(ROOT).as_posix()
    except ValueError:
        bind_rel = bind_path.as_posix()
    return {
        "shadow_bind_eval_only": True,
        "shadow_only": True,
        "shadow_bind_spec": bind_rel,
        "shadow_corpus_tag": tag,
        "shadow_bind_applied": bool(cmp["shadow_applied"]),
        "baseline_shard_id": cmp["baseline_route"]["shard_id"],
        "shadow_shard_id_recommended": cmp["shadow_route"]["shard_id"] if cmp["shadow_applied"] else None,
        "shadow_bind_diverges_from_baseline": bool(cmp["diverges_from_baseline"]),
        "wire_family": str(doc.get("wire_family") or "BIZ_MASK"),
        "production_router_unchanged": True,
        "baseline_route_shard_used_for_compress": baseline_route.shard_id,
        "send_gate": "HOLD",
        "research_only": True,
    }


def compare_baseline_vs_shadow(
    text: str,
    *,
    corpus_tag: str | None,
    router: DomainSpecificRouter,
    spec: dict[str, Any],
) -> dict[str, Any]:
    baseline = router.route(text)
    shadow_sid = resolve_shadow_shard_id(corpus_tag, spec)
    if shadow_sid:
        shadow = router.route_from_shard_id(shadow_sid)
        shadow_applied = True
    else:
        shadow = baseline
        shadow_applied = False
    diverges = baseline.shard_id != shadow.shard_id
    return {
        "corpus_tag": str(corpus_tag or ""),
        "shadow_applied": shadow_applied,
        "shadow_shard_id": shadow.shard_id if shadow_applied else None,
        "baseline_route": shard_route_to_dict(baseline),
        "shadow_route": shard_route_to_dict(shadow),
        "diverges_from_baseline": diverges,
        "text_preview": text[:120],
    }


def infer_corpus_tag_from_row(obj: dict[str, Any], spec: dict[str, Any]) -> str | None:
    explicit = str(obj.get("corpus_tag") or "").strip()
    if explicit and corpus_tag_triggers_shadow(explicit, spec):
        return explicit
    domain = str(obj.get("domain_tag") or "").strip()
    if domain in shadow_corpus_tags(spec):
        return domain
    if domain.startswith("en-business") or domain == "en_business_formal":
        return str(spec.get("corpus_tag_primary") or "en_biz_v1")
    return None


def scan_corpus_shadow_bind(
    path: Path,
    *,
    router: DomainSpecificRouter,
    spec: dict[str, Any],
) -> dict[str, Any]:
    rows_scanned = 0
    en_biz_rows = 0
    cs_skipped = 0
    shadow_applied_count = 0
    divergence_count = 0
    divergences_sample: list[dict[str, Any]] = []
    cases_sample: list[dict[str, Any]] = []

    for obj in iter_jsonl_rows(path):
        rows_scanned += 1
        row_id = str(obj.get("id") or obj.get("case_id") or "")
        domain = str(obj.get("domain_tag") or "")
        if "customer-support" in domain or domain == "customer-support-chat":
            cs_skipped += 1
            continue
        corpus_tag = infer_corpus_tag_from_row(obj, spec)
        if not corpus_tag:
            continue
        en_biz_rows += 1
        for blob in row_text_blobs(obj):
            if not blob.strip():
                continue
            cmp = compare_baseline_vs_shadow(blob, corpus_tag=corpus_tag, router=router, spec=spec)
            if cmp["shadow_applied"]:
                shadow_applied_count += 1
            if cmp["diverges_from_baseline"]:
                divergence_count += 1
                if len(divergences_sample) < 8:
                    divergences_sample.append(
                        {
                            "row_id": row_id,
                            "corpus_tag": corpus_tag,
                            "baseline_shard_id": cmp["baseline_route"]["shard_id"],
                            "shadow_shard_id": cmp["shadow_route"]["shard_id"],
                            "text_preview": cmp["text_preview"],
                        }
                    )
            if len(cases_sample) < 16:
                cases_sample.append({"row_id": row_id, **cmp})

    denom = shadow_applied_count or 1
    expected_sid = str(spec.get("shadow_shard_id") or "")
    all_shadow_correct = all(
        c.get("shadow_route", {}).get("shard_id") == expected_sid
        for c in cases_sample
        if c.get("shadow_applied")
    )
    return {
        "input_jsonl": path.as_posix(),
        "rows_scanned": rows_scanned,
        "en_business_rows": en_biz_rows,
        "cs_rows_skipped": cs_skipped,
        "shadow_applied_count": shadow_applied_count,
        "divergence_count": divergence_count,
        "divergence_rate": round(divergence_count / denom, 6),
        "all_shadow_routes_match_expected_shard": all_shadow_correct,
        "divergences_sample": divergences_sample,
        "cases_sample": cases_sample,
    }


def run_shadow_bind_eval(
    inputs: list[Path],
    *,
    spec_path: Path | None = None,
    shards_root: Path | None = None,
) -> dict[str, Any]:
    spec = load_shadow_bind_spec(spec_path)
    router = DomainSpecificRouter(shards_root or DEFAULT_SHARDS)
    expected_sid = str(spec.get("shadow_shard_id") or "zone_h_en_business_v1")

    per_corpus: list[dict[str, Any]] = []
    for path in inputs:
        if not path.is_file():
            per_corpus.append({"input_jsonl": path.as_posix(), "missing": True})
            continue
        per_corpus.append(scan_corpus_shadow_bind(path, router=router, spec=spec))

    total_shadow = sum(int(c.get("shadow_applied_count") or 0) for c in per_corpus)
    total_diverge = sum(int(c.get("divergence_count") or 0) for c in per_corpus)
    total_en = sum(int(c.get("en_business_rows") or 0) for c in per_corpus)
    all_correct = all(c.get("all_shadow_routes_match_expected_shard", False) for c in per_corpus if not c.get("missing"))
    denom = total_shadow or 1

    return {
        "schema": "en_business_shadow_router_bind_eval_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "shadow_only": True,
        "send_gate": "HOLD",
        "track_a_active_untouched": True,
        "production_router_unchanged": True,
        "bind_spec": (spec_path or DEFAULT_BIND_SPEC).as_posix(),
        "corpus_tag_primary": spec.get("corpus_tag_primary"),
        "shadow_shard_id": expected_sid,
        "wire_family": spec.get("wire_family") or "BIZ_MASK",
        "fail_comp_note": "Shadow bind eval only; CS WTT corpus_tags excluded; hybrid router bindings unchanged.",
        "aggregate": {
            "corpus_count": len(inputs),
            "en_business_rows_total": total_en,
            "shadow_applied_count": total_shadow,
            "divergence_count": total_diverge,
            "divergence_rate": round(total_diverge / denom, 6),
            "all_shadow_routes_expected_shard": all_correct and total_shadow > 0,
            "full_shadow_bind_pass": all_correct and total_shadow > 0 and total_en > 0,
        },
        "per_corpus": per_corpus,
        "reproduce": "py scripts/run_en_business_shadow_router_bind_v1.py",
    }


def write_shadow_bind_report(report: dict[str, Any], *, report_path: Path, artifact_path: Path) -> None:
    payload = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(payload, encoding="utf-8")
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(payload, encoding="utf-8")
