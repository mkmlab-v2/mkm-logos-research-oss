"""[HYPO] KO premium CS WTT template overlay + tenant must_keep twin scan (B-track).

research_only · CS_MASK only · no BIZ_MASK headline merge (FAIL-COMP-004).
Primary twin: saving_rate + exact_restore_ok · jaccard_proxy separate axis.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.compression_ko_premium_cs_deep_pack_v1_lib import (
    load_template_catalog,
    measure_template_wire_twin,
    template_by_id,
)
from scripts.extract_zone_ko_premium_cs_template_seeds_v1_lib import (
    extract_seeds_from_row,
    iter_jsonl_rows,
    load_shard,
    shard_keywords,
)
from scripts.normalize_ko_premium_cs_mask_snippet_v1_lib import resolve_ko_cs_catalog_match

ROOT = Path(__file__).resolve().parents[1]

TENANT_OVERLAY_BY_ID: dict[str, str] = {
    "wtt-premium-cs-customer-v1": "docs/final/artifacts/tenant_wtt-premium-cs-customer-v1_must_keep_overlay_v1.json",
    "wtt-premium-cs-compression-v1": "docs/final/artifacts/tenant_wtt-premium-cs-compression-v1_must_keep_overlay_v1.json",
    "wtt-premium-cs-auto-local-v1": "docs/final/artifacts/tenant_wtt-premium-cs-auto-local-v1_must_keep_overlay_v1.json",
}


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_tenant_overlay_doc(tenant_id: str, *, workspace_root: Path = ROOT) -> dict[str, Any] | None:
    rel = TENANT_OVERLAY_BY_ID.get(str(tenant_id or "").strip())
    if not rel:
        return None
    path = workspace_root / rel
    if not path.is_file():
        return None
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    return doc if isinstance(doc, dict) else None


def tenant_overlay_terms(
    shard: dict[str, Any],
    catalog_row: dict[str, Any],
    *,
    tenant_doc: dict[str, Any] | None,
    wire_snippet: str,
) -> list[str]:
    """Per-snippet overlay: catalog must_keep + shard/tenant hard terms present in wire snippet."""
    terms: list[str] = []
    for t in catalog_row.get("must_keep_terms") or []:
        s = str(t).strip()
        if s and s not in terms:
            terms.append(s)
    lower = wire_snippet.lower()
    for t in shard.get("must_keep_hard_terms") or []:
        s = str(t).strip()
        if s and s.lower() in lower and s not in terms:
            terms.append(s)
    if tenant_doc:
        for t in tenant_doc.get("must_keep_hard_terms") or []:
            s = str(t).strip()
            if s and s.lower() in lower and s not in terms:
                terms.append(s)
    if "███" in wire_snippet and "███" not in terms:
        terms.append("███")
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
    min_score: int = 1,
    workspace_root: Path = ROOT,
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
    seen_snippets: set[str] = set()

    for obj in iter_jsonl_rows(path):
        rows_scanned += 1
        row_id = str(obj.get("id") or obj.get("session_id") or "")
        tenant_id = str(obj.get("tenant_id") or "")
        tenant_doc = load_tenant_overlay_doc(tenant_id, workspace_root=workspace_root)
        seeds = extract_seeds_from_row(obj, keywords=keywords, min_score=min_score)
        for seed in seeds:
            snippet = str(seed.get("snippet") or "")
            if not snippet:
                continue
            norm = snippet.strip()
            if norm in seen_snippets:
                continue
            seen_snippets.add(norm)
            snippet_candidates_total += 1
            resolved = resolve_ko_cs_catalog_match(snippet, catalog_rows)
            if not resolved:
                if len(misses) < 8:
                    misses.append(
                        {
                            "row_id": row_id,
                            "tenant_id": tenant_id,
                            "snippet_preview": snippet[:100],
                            "reason": "no_catalog_snippet_match",
                        }
                    )
                continue
            template_id, _ = resolved
            row = template_by_id(catalog_rows, template_id) or {}
            wire_snippet = str(row.get("snippet") or snippet)
            wire_match_count += 1
            twin = measure_template_wire_twin(
                original_snippet=wire_snippet,
                template_id=template_id,
                catalog_sha256=catalog_sha256,
                catalog_rows=catalog_rows,
            )
            overlay_terms = tenant_overlay_terms(
                shard,
                row,
                tenant_doc=tenant_doc,
                wire_snippet=wire_snippet,
            )
            ok_overlay, missing_terms = overlay_terms_present(wire_snippet, overlay_terms)
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
                        "tenant_id": tenant_id,
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


def run_wtt_overlay_scan(
    inputs: list[Path],
    *,
    shard_path: Path,
    catalog_path: Path,
    manifest_path: Path | None = None,
    min_score: int = 1,
    saving_rate_floor: float = 0.0,
    workspace_root: Path = ROOT,
    excluded_paths: list[str] | None = None,
) -> dict[str, Any]:
    shard = load_shard(shard_path)
    catalog_rows = load_template_catalog(catalog_path)
    if manifest_path and manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
        catalog_sha256 = str(manifest.get("catalog_sha256") or "")
        excluded_paths = excluded_paths or list(manifest.get("excluded_paths") or [])
        exclusion_reason = manifest.get("exclusion_reason")
    else:
        import hashlib

        h = hashlib.sha256()
        h.update(catalog_path.read_bytes())
        catalog_sha256 = h.hexdigest()
        exclusion_reason = None

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
                workspace_root=workspace_root,
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
        "schema": "ko_premium_cs_wtt_template_overlay_scan_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "send_gate": "HOLD",
        "track_a_active_untouched": True,
        "vertical_id": "zone_ko_premium_cs_v1",
        "wire_family": "CS_MASK",
        "corpus_axis": "wtt_premium_cs_only",
        "fail_comp_note": "CS_MASK WTT corpora only; BIZ_MASK en-business excluded; ICP operator axis excluded.",
        "icp_synthetic_operator_excluded": True,
        "excluded_paths": list(excluded_paths or []),
        "exclusion_reason": exclusion_reason,
        "tenant_must_keep_overlay": {
            "tenant_overlay_map": TENANT_OVERLAY_BY_ID,
            "merge_rule": "catalog must_keep + shard hard + tenant hard intersecting wire snippet; ███ when masked",
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
        "reproduce": "py scripts/run_ko_premium_cs_wtt_template_overlay_scan_v1.py",
    }


def write_overlay_report(report: dict[str, Any], *, report_path: Path, artifact_path: Path) -> None:
    payload = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(payload, encoding="utf-8")
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(payload, encoding="utf-8")
