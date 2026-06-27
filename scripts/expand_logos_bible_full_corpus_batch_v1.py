#!/usr/bin/env python3
"""W1+ — inject canon verse batch into studio graph_slice + meaning_graph ([HYPO] B-track).

Expands coverage toward bible_full 100% roadmap by book-ordered verse batches.
  py scripts/expand_logos_bible_full_corpus_batch_v1.py --target-canon-pct 10
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.lens_context_mesh_v1 import build_hop_index_from_slice  # noqa: E402
from scripts.logos_verse_ref_canonical_v1 import canonical_verse_ref  # noqa: E402

CANON_MANIFEST = ROOT / "docs/final/artifacts/logos_corpus_manifest_v1_latest.json"
KRV_JSONL = ROOT / "data/logos/krv_verses_v1.jsonl"
DEFAULT_SLICE = ROOT / "docs/final/artifacts/showroom_meaning_topology_graph_slice_v1_latest.json"
STUDIO_SLICE = ROOT / "projects/no1kmedi/public/data/logos_studio/graph_slice_v1.json"
MEANING_NODES = ROOT / "docs/final/artifacts/bible_meaning_graph_nodes_v1.jsonl"
MEANING_EDGES = ROOT / "docs/final/artifacts/bible_meaning_graph_edges_v1.jsonl"
HOP_OUT = ROOT / "docs/final/artifacts/lens_context_mesh_hop_index_logos_v1_latest.json"
STUDIO_HOP = ROOT / "projects/no1kmedi/public/data/logos_studio/context_mesh_hop_index_v1.json"
OUT_REPORT = ROOT / "reports/logos_bible_full_corpus_batch_expand_v1_latest.json"

NODE_PREFIX = "krv_batch"
BOOK_ANCHOR_PREFIX = "canon_book_anchor"
VERSE_REF_RE = re.compile(r"^[A-Za-z0-9]+\.\d+\.\d+$")

# Protestant canon book order (OT → NT, 66 books)
FULL_CANON_BOOK_ORDER = (
    "Gen", "Exod", "Lev", "Num", "Deut", "Josh", "Judg", "Ruth",
    "1Sam", "2Sam", "1Kgs", "2Kgs", "1Chr", "2Chr", "Ezra", "Neh",
    "Esth", "Job", "Ps", "Prov", "Eccl", "Song", "Isa", "Jer", "Lam",
    "Ezek", "Dan", "Hos", "Joel", "Amos", "Obad", "Jonah", "Mic", "Nah",
    "Hab", "Zeph", "Hag", "Zech", "Mal",
    "Matt", "Mark", "Luke", "Jhn", "Acts", "Rom", "1Cor", "2Cor", "Gal",
    "Eph", "Phil", "Col", "1Thess", "2Thess", "1Tim", "2Tim", "Titus", "Phlm",
    "Heb", "Jas", "1Pet", "2Pet", "1John", "2John", "3John", "Jude", "Rev",
)
W1_BOOK_ORDER = FULL_CANON_BOOK_ORDER[:20]


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _canon_rows() -> list[dict[str, Any]]:
    manifest = _load_json(CANON_MANIFEST)
    rel = manifest.get("input_path", "data/logos/verse_4pipeline_full_31102.json")
    path = ROOT / str(rel).replace("/", "\\")
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, list):
        raise ValueError(f"expected list corpus: {path}")
    return [r for r in data if isinstance(r, dict) and r.get("verse_id")]


def _krv_snippets() -> dict[str, str]:
    out: dict[str, str] = {}
    if not KRV_JSONL.is_file():
        return out
    for line in KRV_JSONL.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        ref = canonical_verse_ref(str(row.get("ref") or ""))
        text = str(row.get("text_ko") or "").strip()
        if ref and text:
            out[ref] = text[:220]
    return out


def _book_of(ref: str) -> str:
    return ref.split(".", 1)[0]


def _select_verses(
    rows: list[dict[str, Any]],
    *,
    target_count: int,
    books: tuple[str, ...],
) -> list[dict[str, Any]]:
    by_book: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        ref = canonical_verse_ref(str(row.get("verse_id") or ""))
        if not ref or not VERSE_REF_RE.match(ref):
            continue
        by_book[_book_of(ref)].append({**row, "verse_id": ref})

    selected: list[dict[str, Any]] = []
    book_order = books if books else tuple(by_book.keys())
    for book in book_order:
        for row in sorted(by_book.get(book, []), key=lambda r: r["verse_id"]):
            selected.append(row)
            if len(selected) >= target_count:
                return selected
    return selected


def _node_id(ref: str) -> str:
    return f"{NODE_PREFIX}::{ref}"


def _existing_node_ids(path: Path) -> set[str]:
    if not path.is_file():
        return set()
    doc = _load_json(path)
    return {str(n.get("id")) for n in doc.get("nodes") or [] if n.get("id")}


def _existing_meaning_ids(path: Path) -> set[str]:
    ids: set[str] = set()
    if not path.is_file():
        return ids
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        nid = row.get("node_id")
        if nid:
            ids.add(str(nid))
    return ids


def _inject_slice(
    slice_doc: dict[str, Any],
    verses: list[dict[str, Any]],
    krv: dict[str, str],
) -> tuple[dict[str, Any], int]:
    node_by_id = {str(n["id"]): dict(n) for n in slice_doc.get("nodes") or []}
    edges: list[dict[str, Any]] = list(slice_doc.get("edges") or [])
    seen_edges = {(e["src"], e["dst"], e.get("edge_type") or "link") for e in edges}

    added = 0
    by_chapter: dict[tuple[str, int], list[str]] = defaultdict(list)
    books_touched: set[str] = set()

    for row in verses:
        ref = row["verse_id"]
        nid = _node_id(ref)
        books_touched.add(_book_of(ref))
        chap = int(ref.split(".")[1])
        by_chapter[(_book_of(ref), chap)].append(ref)
        if nid in node_by_id:
            continue
        snippet = krv.get(ref) or str(row.get("text_preview") or row.get("text") or "")[:220]
        node_by_id[nid] = {
            "id": nid,
            "label": ref,
            "ref": ref,
            "kind": "verse",
            "corpus": "krv_batch",
            "text_snippet_ko": snippet,
            "hub_score": 0.12,
            "corpus_batch_v1": True,
            "research_only": True,
            "evidence_tier": "hypo_research_only",
        }
        added += 1

    book_refs: dict[str, list[str]] = defaultdict(list)
    for row in verses:
        book_refs[_book_of(row["verse_id"])].append(row["verse_id"])

    for book in sorted(books_touched):
        anchor_id = f"{BOOK_ANCHOR_PREFIX}::{book}"
        if anchor_id not in node_by_id:
            node_by_id[anchor_id] = {
                "id": anchor_id,
                "label": book,
                "kind": "theme",
                "hub_score": 0.2,
                "book_anchor": True,
                "research_only": True,
            }
        for ref in book_refs.get(book, []):
            nid = _node_id(ref)
            key = (anchor_id, nid, "book_contains")
            if key not in seen_edges:
                seen_edges.add(key)
                edges.append({"src": anchor_id, "dst": nid, "edge_type": "book_contains", "weight": 0.4})

    for (_b, _c), refs in sorted(by_chapter.items()):
        ordered = sorted(refs, key=lambda r: int(r.split(".")[2]))
        for a, b in zip(ordered, ordered[1:]):
            src, dst = _node_id(a), _node_id(b)
            key = (src, dst, "canon_sequence")
            if key in seen_edges:
                continue
            seen_edges.add(key)
            edges.append({"src": src, "dst": dst, "edge_type": "canon_sequence", "weight": 0.55})

    kind_counts: dict[str, int] = defaultdict(int)
    nodes_out = list(node_by_id.values())
    for n in nodes_out:
        kind_counts[str(n.get("kind") or "other")] += 1

    doc = dict(slice_doc)
    doc["nodes"] = nodes_out
    doc["edges"] = edges
    stats = dict(doc.get("stats") or {})
    stats.update(
        {
            "node_count": len(nodes_out),
            "edge_count": len(edges),
            "kinds": dict(kind_counts),
            "corpus_batch_verse_count": sum(1 for n in nodes_out if n.get("corpus_batch_v1")),
        }
    )
    doc["stats"] = stats
    batch_meta = {
        "schema": "logos_bible_full_corpus_batch_v1",
        "expanded_at_utc": _utc(),
        "target_verse_count": len(verses),
        "books": sorted(books_touched),
        "added_nodes": added,
        "research_only": True,
        "send_gate": "HOLD",
    }
    doc["corpus_batch_expand_v1"] = batch_meta
    return doc, added


def _existing_meaning_edge_pairs(path: Path) -> set[tuple[str, str, str]]:
    pairs: set[tuple[str, str, str]] = set()
    if not path.is_file():
        return pairs
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        src = str(row.get("src_node_id") or "")
        dst = str(row.get("dst_node_id") or "")
        et = str(row.get("edge_type") or "link")
        if src and dst:
            pairs.add((src, dst, et))
    return pairs


def _append_meaning_graph(
    verses: list[dict[str, Any]],
    krv: dict[str, str],
    *,
    nodes_path: Path,
    edges_path: Path,
) -> tuple[int, int]:
    existing = _existing_meaning_ids(nodes_path)
    existing_edges = _existing_meaning_edge_pairs(edges_path)
    node_lines: list[str] = []
    edge_lines: list[str] = []
    nodes_added = 0
    edges_added = 0
    by_chapter: dict[tuple[str, int], list[str]] = defaultdict(list)

    for row in verses:
        ref = row["verse_id"]
        by_chapter[(_book_of(ref), int(ref.split(".")[1]))].append(ref)
        nid = _node_id(ref)
        if nid in existing:
            continue
        text = str(row.get("text_preview") or row.get("text") or krv.get(ref) or "")
        node_lines.append(
            json.dumps(
                {
                    "schema": "krv_batch_graph_node_v1",
                    "node_id": nid,
                    "corpus": "krv_batch",
                    "ref": ref,
                    "text_norm": text[:500],
                    "research_only": True,
                    "source_track": "B",
                    "hypothesis_tier": "B",
                },
                ensure_ascii=False,
            )
        )
        existing.add(nid)
        nodes_added += 1

    for (_b, _c), refs in sorted(by_chapter.items()):
        ordered = sorted(refs, key=lambda r: int(r.split(".")[2]))
        for a, b in zip(ordered, ordered[1:]):
            src, dst = _node_id(a), _node_id(b)
            key = (src, dst, "canon_sequence")
            if key in existing_edges:
                continue
            existing_edges.add(key)
            edge_lines.append(
                json.dumps(
                    {
                        "schema": "krv_batch_graph_edge_v1",
                        "src_node_id": _node_id(a),
                        "dst_node_id": _node_id(b),
                        "edge_type": "canon_sequence",
                        "weight": 0.55,
                        "research_only": True,
                        "source_track": "B",
                    },
                    ensure_ascii=False,
                )
            )
            edges_added += 1

    if node_lines:
        with nodes_path.open("a", encoding="utf-8") as fh:
            fh.write("\n".join(node_lines) + "\n")
    if edge_lines:
        with edges_path.open("a", encoding="utf-8") as fh:
            fh.write("\n".join(edge_lines) + "\n")
    return nodes_added, edges_added


def _canon_rows_missing_meaning(canon_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    existing = _existing_meaning_ids(MEANING_NODES)
    missing: list[dict[str, Any]] = []
    for row in canon_rows:
        ref = canonical_verse_ref(str(row.get("verse_id") or ""))
        if not ref or not VERSE_REF_RE.match(ref):
            continue
        if _node_id(ref) not in existing:
            missing.append({**row, "verse_id": ref})
    return missing


def _canon_rows_missing_slice(canon_rows: list[dict[str, Any]], slice_path: Path) -> list[dict[str, Any]]:
    existing_refs = _existing_node_ids(slice_path)
    existing = set()
    for nid in existing_refs:
        if "::" in nid:
            tail = nid.split("::", 1)[1]
            if VERSE_REF_RE.match(tail):
                existing.add(canonical_verse_ref(tail))
    missing: list[dict[str, Any]] = []
    for row in canon_rows:
        ref = canonical_verse_ref(str(row.get("verse_id") or ""))
        if not ref or not VERSE_REF_RE.match(ref):
            continue
        if _node_id(ref) not in existing_refs and ref not in existing:
            missing.append({**row, "verse_id": ref})
    return missing


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--target-canon-pct", type=float, default=10.0)
    ap.add_argument("--target-verse-count", type=int, default=0)
    ap.add_argument("--books", type=str, default=",".join(FULL_CANON_BOOK_ORDER))
    ap.add_argument(
        "--fill-meaning-gaps-only",
        action="store_true",
        help="Append only canon verses absent from bible_meaning_graph_nodes_v1.jsonl",
    )
    ap.add_argument(
        "--fill-slice-gaps-only",
        action="store_true",
        help="Append only canon verses absent from studio graph_slice",
    )
    ap.add_argument("--slice-json", type=Path, default=DEFAULT_SLICE)
    ap.add_argument("--studio-slice-json", type=Path, default=STUDIO_SLICE)
    ap.add_argument("--skip-meaning-graph", action="store_true")
    ap.add_argument("--skip-hop-rebuild", action="store_true")
    args = ap.parse_args()

    canon_rows = _canon_rows()
    canon_denom = len(canon_rows)
    books = tuple(b.strip() for b in args.books.split(",") if b.strip())

    if args.fill_meaning_gaps_only:
        verses = _canon_rows_missing_meaning(canon_rows)
        if books and books != FULL_CANON_BOOK_ORDER:
            book_set = set(books)
            verses = [v for v in verses if _book_of(v["verse_id"]) in book_set]
    elif args.fill_slice_gaps_only:
        verses = _canon_rows_missing_slice(canon_rows, args.slice_json)
        if books and books != FULL_CANON_BOOK_ORDER:
            book_set = set(books)
            verses = [v for v in verses if _book_of(v["verse_id"]) in book_set]
    else:
        target = args.target_verse_count or max(1, int(canon_denom * args.target_canon_pct / 100.0))
        verses = _select_verses(canon_rows, target_count=target, books=books)
    if not verses:
        if args.fill_meaning_gaps_only or args.fill_slice_gaps_only:
            print(
                json.dumps(
                    {
                        "ok": True,
                        "skipped": True,
                        "reason": "no_gaps",
                        "fill_mode": "meaning_gaps_only" if args.fill_meaning_gaps_only else "slice_gaps_only",
                    },
                    ensure_ascii=False,
                )
            )
            return 0
        print(json.dumps({"ok": False, "error": "no_verses_selected"}, ensure_ascii=False))
        return 1

    krv = _krv_snippets()
    if not args.slice_json.is_file():
        print(json.dumps({"ok": False, "error": f"slice missing: {args.slice_json}"}, ensure_ascii=False))
        return 2

    slice_doc = _load_json(args.slice_json)
    patched, added_nodes = _inject_slice(slice_doc, verses, krv)
    text = json.dumps(patched, ensure_ascii=False, indent=2) + "\n"
    args.slice_json.write_text(text, encoding="utf-8")
    args.studio_slice_json.parent.mkdir(parents=True, exist_ok=True)
    args.studio_slice_json.write_text(text, encoding="utf-8")

    mg_nodes = mg_edges = 0
    if not args.skip_meaning_graph:
        mg_nodes, mg_edges = _append_meaning_graph(
            verses, krv, nodes_path=MEANING_NODES, edges_path=MEANING_EDGES
        )

    hop_rebuilt = False
    if not args.skip_hop_rebuild:
        rel_src = str(args.slice_json.relative_to(ROOT)).replace("\\", "/")
        hop_doc = build_hop_index_from_slice(
            patched,
            lens_id="logos",
            pack_id="lens_pack@logos_showroom",
            source_slice_path=rel_src,
        )
        hop_text = json.dumps(hop_doc, ensure_ascii=False, indent=2) + "\n"
        HOP_OUT.parent.mkdir(parents=True, exist_ok=True)
        HOP_OUT.write_text(hop_text, encoding="utf-8")
        STUDIO_HOP.parent.mkdir(parents=True, exist_ok=True)
        STUDIO_HOP.write_text(hop_text, encoding="utf-8")
        hop_rebuilt = True

    refs_added = {v["verse_id"] for v in verses}
    report = {
        "schema": "logos_bible_full_corpus_batch_expand_v1",
        "ok": True,
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "target_verse_count": len(verses) if (args.fill_meaning_gaps_only or args.fill_slice_gaps_only) else target,
        "selected_verse_count": len(verses),
        "fill_mode": (
            "meaning_gaps_only"
            if args.fill_meaning_gaps_only
            else ("slice_gaps_only" if args.fill_slice_gaps_only else "canon_pct")
        ),
        "selected_books": sorted({_book_of(v["verse_id"]) for v in verses}),
        "slice_added_nodes": added_nodes,
        "meaning_graph_nodes_added": mg_nodes,
        "meaning_graph_edges_added": mg_edges,
        "hop_rebuilt": hop_rebuilt,
        "sample_refs": sorted(refs_added)[:8],
        "reproduce": "py scripts/expand_logos_bible_full_corpus_batch_v1.py --target-canon-pct 10",
    }
    OUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    OUT_REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
