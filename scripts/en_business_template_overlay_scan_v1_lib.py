"""[HYPO] En business template overlay + tenant must_keep twin scan (B-track).

research_only · BIZ_MASK only · no CS WTT headline merge (FAIL-COMP-004).
Primary twin: saving_rate + exact_restore_ok · jaccard_proxy separate axis.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.compression_en_business_deep_pack_v1_lib import (
    load_template_catalog,
    measure_template_wire_twin,
    resolve_template_match,
    template_by_id,
)
from scripts.extract_zone_h_en_business_template_seeds_v1_lib import (
    extract_seeds_from_row,
    iter_jsonl_rows,
    load_shard,
    shard_keywords,
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def tenant_overlay_terms(
    shard: dict[str, Any],
    catalog_row: dict[str, Any],
    *,
    original_snippet: str,
) -> list[str]:
    """Per-snippet overlay: catalog must_keep + shard hard terms present in original."""
    terms: list[str] = []
    for t in catalog_row.get("must_keep_terms") or []:
        s = str(t).strip()
        if s and s not in terms:
            terms.append(s)
    lower = original_snippet.lower()
    for t in shard.get("must_keep_hard_terms") or []:
        s = str(t).strip()
        if s and s.lower() in lower and s not in terms:
            terms.append(s)
    return terms


def overlay_terms_present(text: str, terms: list[str]) -> tuple[bool, list[str]]:
    lower = text.lower()
    missing = [t for t in terms if t.lower() not in lower]
    return len(missing) == 0, missing


def scan_corpus_overlay(
    path: Path,
    *,
    shard: dict[str, Any],
    catalog_rows: list[dict[str, Any]],
    catalog_sha256: str,
    min_score: int = 2,
) -> dict[str, Any]:
    keywords = shard_keywords(shard)
    rows_scanned = 0
    cases: list[dict[str, Any]] = []
    snippet_candidates_total = 0
    wire_match_count = 0
    exact_restore_pass = 0
    overlay_pass = 0
    saving_rates: list[float] = []
    jaccards: list[float] = []
    misses: list[dict[str, Any]] = []

    for obj in iter_jsonl_rows(path):
        rows_scanned += 1
        row_id = str(obj.get("id") or obj.get("case_id") or "")
        seeds = extract_seeds_from_row(obj, keywords=keywords, min_score=min_score)
        for seed in seeds:
            snippet = str(seed.get("snippet") or "")
            if not snippet:
                continue
            snippet_candidates_total += 1
            resolved = resolve_template_match(snippet, catalog_rows)
            if not resolved:
                if len(misses) < 8:
                    misses.append(
                        {
                            "row_id": row_id,
                            "snippet_preview": snippet[:100],
                            "reason": "no_exact_catalog_snippet_match",
                        }
                    )
                continue
            template_id, _ = resolved
            wire_match_count += 1
            twin = measure_template_wire_twin(
                original_snippet=snippet,
                template_id=template_id,
                catalog_sha256=catalog_sha256,
                catalog_rows=catalog_rows,
            )
            row = template_by_id(catalog_rows, template_id) or {}
            overlay_terms = tenant_overlay_terms(shard, row, original_snippet=snippet)
            ok_overlay, missing_terms = overlay_terms_present(snippet, overlay_terms)
            if twin.get("exact_restore_ok"):
                exact_restore_pass += 1
            if ok_overlay:
                overlay_pass += 1
            saving_rates.append(float(twin.get("saving_rate") or 0.0))
            jaccards.append(float(twin.get("jaccard_proxy") or 0.0))
            if len(cases) < 24:
                cases.append(
                    {
                        "row_id": row_id,
                        "template_id": template_id,
                        "exact_restore_ok": twin.get("exact_restore_ok"),
                        "saving_rate": twin.get("saving_rate"),
                        "jaccard_proxy": twin.get("jaccard_proxy"),
                        "tenant_overlay_ok": ok_overlay,
                        "missing_overlay_terms": missing_terms,
                        "overlay_term_count": len(overlay_terms),
                    }
                )

    denom = snippet_candidates_total
    wire_denom = wire_match_count or 1
    return {
        "input_jsonl": path.as_posix(),
        "rows_scanned": rows_scanned,
        "snippet_candidates_total": snippet_candidates_total,
        "wire_match_count": wire_match_count,
        "exact_restore_pass_count": exact_restore_pass,
        "tenant_overlay_pass_count": overlay_pass,
        "wire_match_rate": round(wire_match_count / denom, 6) if denom else 1.0,
        "exact_restore_rate_on_matched": round(exact_restore_pass / wire_denom, 6),
        "tenant_overlay_rate_on_matched": round(overlay_pass / wire_denom, 6),
        "mean_saving_rate_matched": round(sum(saving_rates) / len(saving_rates), 6) if saving_rates else 0.0,
        "min_saving_rate_matched": round(min(saving_rates), 6) if saving_rates else 0.0,
        "mean_jaccard_proxy_matched": round(sum(jaccards) / len(jaccards), 6) if jaccards else 0.0,
        "misses_sample": misses,
        "cases_sample": cases,
    }


def run_overlay_scan(
    inputs: list[Path],
    *,
    shard_path: Path,
    catalog_path: Path,
    manifest_path: Path | None = None,
    min_score: int = 2,
    saving_rate_floor: float = 0.0,
) -> dict[str, Any]:
    shard = load_shard(shard_path)
    catalog_rows = load_template_catalog(catalog_path)
    if manifest_path and manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
        catalog_sha256 = str(manifest.get("catalog_sha256") or "")
    else:
        import hashlib

        h = hashlib.sha256()
        h.update(catalog_path.read_bytes())
        catalog_sha256 = h.hexdigest()

    per_corpus: list[dict[str, Any]] = []
    for path in inputs:
        if not path.is_file():
            per_corpus.append({"input_jsonl": path.as_posix(), "missing": True})
            continue
        per_corpus.append(
            scan_corpus_overlay(
                path,
                shard=shard,
                catalog_rows=catalog_rows,
                catalog_sha256=catalog_sha256,
                min_score=min_score,
            )
        )

    total_candidates = sum(int(c.get("snippet_candidates_total") or 0) for c in per_corpus)
    total_match = sum(int(c.get("wire_match_count") or 0) for c in per_corpus)
    total_exact = sum(int(c.get("exact_restore_pass_count") or 0) for c in per_corpus)
    total_overlay = sum(int(c.get("tenant_overlay_pass_count") or 0) for c in per_corpus)
    all_saving_mins = [
        float(c.get("min_saving_rate_matched") or 0.0)
        for c in per_corpus
        if int(c.get("wire_match_count") or 0) > 0
    ]
    floor_observed = min(all_saving_mins) if all_saving_mins else 0.0
    matched_denom = total_match or 1

    return {
        "schema": "en_business_template_overlay_scan_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "send_gate": "HOLD",
        "track_a_active_untouched": True,
        "vertical_id": "zone_h_en_business_v1",
        "wire_family": "BIZ_MASK",
        "fail_comp_note": "BIZ_MASK en-business corpora only; CS WTT axis excluded from this scan.",
        "tenant_must_keep_overlay": {
            "shard_hard_terms": list(shard.get("must_keep_hard_terms") or []),
            "shard_soft_terms": list(shard.get("must_keep_soft_terms") or []),
            "merge_rule": "catalog row must_keep_terms + shard hard terms intersecting original snippet; soft terms advisory only",
        },
        "catalog_jsonl": catalog_path.as_posix(),
        "catalog_row_count": len(catalog_rows),
        "catalog_sha256": catalog_sha256,
        "saving_rate_floor_hypo": saving_rate_floor,
        "aggregate": {
            "corpus_count": len(inputs),
            "snippet_candidates_total": total_candidates,
            "wire_match_count": total_match,
            "wire_match_rate": round(total_match / total_candidates, 6) if total_candidates else 1.0,
            "exact_restore_pass_count": total_exact,
            "exact_restore_rate_on_matched": round(total_exact / matched_denom, 6),
            "tenant_overlay_pass_count": total_overlay,
            "tenant_overlay_rate_on_matched": round(total_overlay / matched_denom, 6),
            "min_saving_rate_observed": floor_observed,
            "saving_rate_floor_hypo_pass": floor_observed >= saving_rate_floor,
            "full_wire_and_twin_pass": (
                total_candidates > 0
                and total_match == total_candidates
                and total_exact == total_match
                and total_overlay == total_match
            ),
        },
        "per_corpus": per_corpus,
        "reproduce": "py scripts/run_en_business_template_overlay_scan_v1.py",
    }


def write_overlay_report(report: dict[str, Any], *, report_path: Path, artifact_path: Path) -> None:
    payload = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(payload, encoding="utf-8")
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(payload, encoding="utf-8")
