#!/usr/bin/env python3
"""Execute DSS + Apocrypha shadow lane P0–P2 (isolated, non-gating) [HYPO]."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DSS_JSONL = ROOT / "data/logos/manuscripts/dss_parsed_enriched.jsonl"
APO_MANIFEST = ROOT / "docs/final/artifacts/logos_apocrypha_bootstrap_manifest_v1_latest.json"
CANON_JSONL = ROOT / "reports/constitution/btrack_pilot/logos_verse_4d_v1_latest.jsonl"
DSS_OUT = ROOT / "reports/dss_shadow_alignment_v1_latest.json"
APO_OUT = ROOT / "reports/apocrypha_shadow_alignment_v1_latest.json"
LANE_OUT = ROOT / "reports/dss_apocrypha_shadow_lane_v1_latest.json"

VERSE_REF_RE = re.compile(r"\b([A-Za-z][A-Za-z0-9]{0,8})\.(\d+)\.(\d+)\b")


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return {}


def _canon_verse_ids(jsonl: Path) -> set[str]:
    out: set[str] = set()
    if not jsonl.is_file():
        return out
    with jsonl.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            vid = str(row.get("verse_id") or "").strip()
            if vid:
                out.add(vid)
    return out


def _inventory_jsonl(path: Path) -> dict[str, Any]:
    rows = 0
    null_text = 0
    ids: list[str] = []
    if not path.is_file():
        return {"present": False, "row_count": 0}
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows += 1
            row = json.loads(line)
            rid = str(row.get("id") or row.get("verse_id") or "")
            if rid:
                ids.append(rid)
            if not str(row.get("text") or row.get("original_text") or "").strip():
                null_text += 1
    return {
        "present": True,
        "row_count": rows,
        "null_text_rows": null_text,
        "null_text_rate": round(null_text / rows, 4) if rows else 0.0,
        "unique_ids": len(set(ids)),
        "id_contract_ok": rows > 0 and len(set(ids)) >= max(1, rows // 2),
    }


def _dss_verse_hits(path: Path, canon: set[str]) -> dict[str, Any]:
    cited: Counter[str] = Counter()
    rows = 0
    rows_with_hit = 0
    if not path.is_file():
        return {"row_count": 0, "canon_hits": 0}
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows += 1
            row = json.loads(line)
            text = str(row.get("text") or "")
            hits = set()
            for m in VERSE_REF_RE.finditer(text):
                vid = f"{m.group(1)}.{m.group(2)}.{m.group(3)}"
                if vid in canon:
                    hits.add(vid)
                    cited[vid] += 1
            if hits:
                rows_with_hit += 1
    return {
        "row_count": rows,
        "rows_with_canon_ref": rows_with_hit,
        "unique_canon_verse_hits": len(cited),
        "top_cited_verses": cited.most_common(12),
        "canon_overlap_rate": round(rows_with_hit / rows, 4) if rows else 0.0,
    }


def _apocrypha_alignment(path: Path) -> dict[str, Any]:
    inv = _inventory_jsonl(path)
    greek_rows = 0
    apo_ids: set[str] = set()
    if path.is_file():
        with path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                vid = str(row.get("verse_id") or "")
                if vid.startswith("apo:"):
                    apo_ids.add(vid)
                if str(row.get("language") or "").startswith("gr"):
                    greek_rows += 1
    return {
        **inv,
        "apo_prefixed_ids": len(apo_ids),
        "greek_rows": greek_rows,
        "fixture_lane": True,
    }


def _retrieval_probe_dss(path: Path, queries: list[str]) -> dict[str, Any]:
    if not path.is_file():
        return {"hit_rate": 0.0, "queries": 0}
    corpus: list[str] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            corpus.append(str(row.get("text") or "").lower())
    hits = 0
    for q in queries:
        ql = q.lower()
        if any(ql in doc for doc in corpus):
            hits += 1
    return {
        "queries": len(queries),
        "hits": hits,
        "hit_rate": round(hits / len(queries), 4) if queries else 0.0,
        "non_gating": True,
    }


def build() -> dict[str, Any]:
    manifest = _load_json(APO_MANIFEST)
    apo_path = ROOT / str(manifest.get("output_jsonl") or "data/logos/manuscripts/apocrypha_original_only_latest.jsonl")
    canon = _canon_verse_ids(CANON_JSONL)

    dss_p0 = _inventory_jsonl(DSS_JSONL)
    apo_p0 = _apocrypha_alignment(apo_path)
    dss_p1 = _dss_verse_hits(DSS_JSONL, canon)
    probe_queries = ["Ps.4.6", "Ps.5.2", "11Q5", "Qumran", "Psalms scroll"]
    dss_p2 = _retrieval_probe_dss(DSS_JSONL, probe_queries)
    apo_p2 = _retrieval_probe_dss(apo_path, ["Tobit", "Wisdom", "Sirach", "Maccabees"])

    dss_doc = {
        "schema": "dss_shadow_alignment_v1",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "track_wall": {"logos_core_mutation_forbidden": True, "track_a_bridge": False},
        "phase_p0_inventory": dss_p0,
        "phase_p1_canon_overlap": dss_p1,
        "phase_p2_retrieval_probe": dss_p2,
        "ok": dss_p0.get("row_count", 0) >= 10 and dss_p1.get("unique_canon_verse_hits", 0) >= 1,
        "reproduce": "py scripts/run_dss_apocrypha_shadow_lane_v1.py",
    }
    apo_doc = {
        "schema": "apocrypha_shadow_alignment_v1",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "track_wall": {"merge_into_canon_complete_jsonl": False, "track_a_bridge": False},
        "phase_p0_inventory": apo_p0,
        "phase_p2_retrieval_probe": apo_p2,
        "fixture_only": manifest.get("fixture_only", True),
        "ok": apo_p0.get("row_count", 0) >= 4,
        "reproduce": "py scripts/run_dss_apocrypha_shadow_lane_v1.py",
    }
    lane_doc = {
        "schema": "dss_apocrypha_shadow_lane_v1",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "phases_completed": ["P0", "P1", "P2"],
        "dss": {"ok": dss_doc["ok"], "artifact": str(DSS_OUT.relative_to(ROOT)).replace("\\", "/")},
        "apocrypha": {"ok": apo_doc["ok"], "artifact": str(APO_OUT.relative_to(ROOT)).replace("\\", "/")},
        "ok": dss_doc["ok"] and apo_doc["ok"],
        "reproduce": "py scripts/run_dss_apocrypha_shadow_lane_v1.py",
    }
    return {"dss": dss_doc, "apocrypha": apo_doc, "lane": lane_doc}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dss-out", type=Path, default=DSS_OUT)
    ap.add_argument("--apo-out", type=Path, default=APO_OUT)
    ap.add_argument("--lane-out", type=Path, default=LANE_OUT)
    args = ap.parse_args()

    built = build()
    for path, key in ((args.dss_out, "dss"), (args.apo_out, "apocrypha"), (args.lane_out, "lane")):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(built[key], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    ok = built["lane"]["ok"]
    print(
        json.dumps(
            {
                "ok": ok,
                "dss_rows": built["dss"]["phase_p0_inventory"].get("row_count"),
                "apo_rows": built["apocrypha"]["phase_p0_inventory"].get("row_count"),
            },
            ensure_ascii=False,
        )
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
