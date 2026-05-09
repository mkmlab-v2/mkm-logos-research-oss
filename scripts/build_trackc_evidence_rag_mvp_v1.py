from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "trackc_evidence_rag_mvp_latest.json"

DEFAULT_CATALOG: list[dict[str, Any]] = [
    {
        "id": "trackc_business_plan",
        "title": "Track C IP Business Plan",
        "path": "docs/final/TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md",
        "tags": ["trackc", "business", "gtm", "ip", "commercialization", "b2b", "kpi"],
    },
    {
        "id": "p0_commercialization_tracker",
        "title": "P0 Commercialization Tracker",
        "path": "docs/final/P0_COMMERCIALIZATION_TRACKER.md",
        "tags": ["p0", "commercialization", "gate", "kpi", "promotion", "fact-lock"],
    },
    {
        "id": "central_agent_memory",
        "title": "Central Agent Memory",
        "path": "docs/final/CENTRAL_AGENT_MEMORY_V1.md",
        "tags": ["memory", "ssot", "long-term", "fact-lock", "governance"],
    },
    {
        "id": "constitution_facts",
        "title": "Constitution Implementation Facts",
        "path": "docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md",
        "tags": ["constitution", "facts", "implementation", "paths", "contracts", "ssot"],
    },
    {
        "id": "evidence_bundle",
        "title": "Fact Lock Evidence Bundle",
        "path": "reports/fact_lock_evidence_bundle_latest.json",
        "tags": ["evidence", "hash", "audit", "fact-lock", "integrity"],
    },
    {
        "id": "amsaeng_weekly_audit",
        "title": "Amsaeng Eosa Weekly Audit Packet",
        "path": "reports/amsaeng_eosa_weekly_audit_packet_latest.json",
        "tags": ["ops", "audit", "security", "task", "monitoring", "status"],
    },
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _tokens(text: str) -> set[str]:
    return {t.lower() for t in re.findall(r"[A-Za-z0-9_가-힣]+", text)}


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return obj if isinstance(obj, dict) else None


def _build_excerpt(path: Path) -> str:
    if not path.exists():
        return "missing"
    if path.suffix.lower() == ".json":
        doc = _read_json(path)
        if not doc:
            return "json_parse_failed_or_not_object"
        keep_keys = (
            "schema",
            "generated_at_utc",
            "status",
            "decision",
            "go_stable",
            "fact_lock_missing_count",
            "security_status",
            "ops_mode",
        )
        summary = {k: doc.get(k) for k in keep_keys if k in doc}
        return json.dumps(summary, ensure_ascii=False)
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return "read_failed"
    non_empty = [ln.strip() for ln in lines if ln.strip()]
    return " | ".join(non_empty[:3])[:500] if non_empty else "empty"


def _score(query_tokens: set[str], row: dict[str, Any]) -> int:
    title = str(row.get("title") or "")
    path = str(row.get("path") or "")
    tags = row.get("tags") if isinstance(row.get("tags"), list) else []
    bag = _tokens(" ".join([title, path] + [str(t) for t in tags]))
    overlap = query_tokens & bag
    # Prefer explicit tag matches slightly.
    tag_tokens = _tokens(" ".join(str(t) for t in tags))
    tag_overlap = query_tokens & tag_tokens
    return len(overlap) + len(tag_overlap)


def _resolve_catalog(root: Path, args: argparse.Namespace) -> list[dict[str, Any]]:
    if args.catalog_json:
        catalog_path = Path(args.catalog_json)
        if not catalog_path.is_absolute():
            catalog_path = root / catalog_path
        raw = _read_json(catalog_path)
        rows = raw.get("catalog") if isinstance(raw, dict) else None
        if isinstance(rows, list):
            out: list[dict[str, Any]] = []
            for r in rows:
                if not isinstance(r, dict):
                    continue
                if "path" not in r:
                    continue
                out.append(r)
            if out:
                return out
    return DEFAULT_CATALOG


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build Track C Evidence RAG MVP packet.")
    p.add_argument("--query", action="append", default=[], help="Query string (repeatable).")
    p.add_argument("--max-evidence", type=int, default=4)
    p.add_argument("--catalog-json", default="", help="Optional catalog override JSON with {catalog:[...]}.")
    p.add_argument("--workspace-root", default=str(ROOT))
    p.add_argument("--output-json", default=str(DEFAULT_OUT))
    return p.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.workspace_root).resolve()
    out_path = Path(args.output_json)
    if not out_path.is_absolute():
        out_path = (root / out_path).resolve()
    queries = [q.strip() for q in args.query if str(q).strip()]
    if not queries:
        queries = [
            "track c commercialization proof",
            "ops integrity and guardrail status",
            "ssot fact lock evidence",
        ]

    catalog = _resolve_catalog(root, args)
    result_queries: list[dict[str, Any]] = []
    for q in queries:
        q_tokens = _tokens(q)
        scored: list[tuple[int, dict[str, Any]]] = []
        for row in catalog:
            s = _score(q_tokens, row)
            if s <= 0:
                continue
            scored.append((s, row))
        scored.sort(key=lambda x: x[0], reverse=True)
        selected: list[dict[str, Any]] = []
        for score, row in scored[: max(1, args.max_evidence)]:
            rel = str(row.get("path"))
            p = Path(rel)
            abs_path = p if p.is_absolute() else (root / rel)
            exists = abs_path.exists()
            selected.append(
                {
                    "id": row.get("id", rel),
                    "title": row.get("title", rel),
                    "path": rel.replace("\\", "/"),
                    "score": score,
                    "exists": exists,
                    "last_modified_utc": datetime.fromtimestamp(abs_path.stat().st_mtime, tz=timezone.utc).isoformat()
                    if exists
                    else "",
                    "excerpt": _build_excerpt(abs_path),
                }
            )
        result_queries.append({"query": q, "results": selected})

    payload = {
        "schema": "trackc_evidence_rag_mvp_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "final_decision_policy": "Artifacts and exit-codes remain authoritative; RAG is advisory.",
        "catalog_size": len(catalog),
        "queries": result_queries,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"trackc_evidence_rag_mvp_written={out_path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
