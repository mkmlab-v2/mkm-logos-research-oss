#!/usr/bin/env python3
"""Extract minimal verse-atom JSONL stub for OSS export (fixture-aligned, Mode B).

Reads the monorepo full corpus and keeps only verse rows needed so
build_universal_root_topology_crosswalk_v1.py reproduces the same topology
hits on the 500-pair fixture as the full JSONL (within gate tolerances).

B-track / research_only — not for Track A promotion.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_universal_root_topology_crosswalk_v1 import (  # noqa: E402
    DEFAULT_FIXTURE,
    DEFAULT_LEXICON_AUDIT,
    DEFAULT_VERSE_JSONL,
    _build_atom_index,
    _topology_hit,
    _topology_tokens,
    build_crosswalk,
)

DEFAULT_OUT = ROOT / "tests/fixtures/logos_verse_4d_topology_stub_v1.jsonl"
DEFAULT_META = ROOT / "reports/logos_verse_4d_topology_stub_extract_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _pick_verse_for_topology_sample(
    sample: dict[str, Any],
    audit_row: dict[str, Any],
    token_to_atoms: dict[str, set[str]],
    atom_verse_count: dict[str, int],
    atom_first_verse: dict[str, str],
) -> str | None:
    """One verse row that preserves topology_hit for this sample on the full corpus."""
    tokens = _topology_tokens(sample, audit_row)
    for tok in tokens:
        t = str(tok or "").strip()
        if not t:
            continue
        atoms = token_to_atoms.get(t) or token_to_atoms.get(t.lower()) or set()
        for atom in atoms:
            if atom_verse_count.get(atom, 0) <= 0:
                continue
            vid = atom_first_verse.get(atom)
            if vid:
                return vid
    return None


def _negative_control_leaks(
    fixture: dict[str, Any],
    token_to_atoms: dict[str, set[str]],
    atom_verse_count: dict[str, int],
) -> int:
    leaks = 0
    for sample in fixture.get("samples") or []:
        if str(sample.get("control") or "") != "negative":
            continue
        probe_tokens = [str(t) for t in (sample.get("probe_tokens") or []) if str(t).strip()]
        if _topology_hit(probe_tokens, token_to_atoms, atom_verse_count):
            leaks += 1
    return leaks


def _build_atom_first_verse(jsonl: Path) -> dict[str, str]:
    atom_first_verse: dict[str, str] = {}
    with jsonl.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            vid = str(row.get("verse_id") or "")
            if not vid:
                continue
            for atom in ((row.get("atom_overlay") or {}).get("top_atoms")) or []:
                aid = str(atom.get("atom_id") or "")
                if aid and aid not in atom_first_verse:
                    atom_first_verse[aid] = vid
    return atom_first_verse


def extract_stub(
    *,
    fixture_path: Path,
    audit_path: Path,
    source_jsonl: Path,
    out_jsonl: Path,
) -> dict[str, Any]:
    fixture = _read(fixture_path)
    audit = _read(audit_path)
    audit_rows = ((audit.get("baseline") or {}).get("rows")) or []
    rows_by_prime = {str(r.get("prime_en") or ""): r for r in audit_rows if r.get("prime_en")}

    atom_first_verse = _build_atom_first_verse(source_jsonl)
    lines_by_verse: dict[str, str] = {}
    with source_jsonl.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            vid = str(row.get("verse_id") or "")
            if vid:
                lines_by_verse[vid] = line

    t2a_full, avc_full, corpus_full = _build_atom_index(source_jsonl)
    verse_ids: set[str] = set()
    for sample in fixture.get("samples") or []:
        if str(sample.get("control") or "") == "negative":
            continue
        prime = str(sample.get("prime_en") or "")
        audit_row = rows_by_prime.get(prime, {})
        if not _topology_hit(_topology_tokens(sample, audit_row), t2a_full, avc_full):
            continue
        vid = _pick_verse_for_topology_sample(sample, audit_row, t2a_full, avc_full, atom_first_verse)
        if vid:
            verse_ids.add(vid)

    full_doc = build_crosswalk(
        fixture=fixture,
        audit=audit,
        token_to_atoms=t2a_full,
        atom_verse_count=avc_full,
        corpus_summary=corpus_full,
    )
    full_rate = float(full_doc["summary"]["verse_reachable_rate"] or 0)

    out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with out_jsonl.open("w", encoding="utf-8") as out:
        for vid in sorted(verse_ids):
            line = lines_by_verse.get(vid)
            if line:
                out.write(line + "\n")
                written += 1

    t2a_stub, avc_stub, corpus_stub = _build_atom_index(out_jsonl)
    stub_doc = build_crosswalk(
        fixture=fixture,
        audit=audit,
        token_to_atoms=t2a_stub,
        atom_verse_count=avc_stub,
        corpus_summary=corpus_stub,
    )
    stub_rate = float(stub_doc["summary"]["verse_reachable_rate"] or 0)
    neg_leaks = _negative_control_leaks(fixture, t2a_stub, avc_stub)

    size_bytes = out_jsonl.stat().st_size if out_jsonl.is_file() else 0
    ok = (
        abs(stub_rate - full_rate) < 1e-6
        and written > 0
        and neg_leaks == 0
        and int(stub_doc["topology_plane"].get("negative_topology_leak_count") or 0) == 0
    )

    meta = {
        "schema": "logos_verse_4d_topology_stub_extract_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "ok": ok,
        "source_jsonl": str(source_jsonl.relative_to(ROOT)).replace("\\", "/"),
        "out_jsonl": str(out_jsonl.relative_to(ROOT)).replace("\\", "/"),
        "verse_rows_written": written,
        "size_bytes": size_bytes,
        "size_kb": round(size_bytes / 1024, 2),
        "negative_topology_leaks_on_stub": neg_leaks,
        "full_corpus_verse_nodes": corpus_full.get("verse_nodes"),
        "stub_corpus_verse_nodes": corpus_stub.get("verse_nodes"),
        "full_verse_reachable_rate": full_rate,
        "stub_verse_reachable_rate": stub_rate,
        "rate_delta_stub_minus_full": round(stub_rate - full_rate, 6),
    }
    return meta


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    ap.add_argument("--audit", type=Path, default=DEFAULT_LEXICON_AUDIT)
    ap.add_argument("--source-jsonl", type=Path, default=DEFAULT_VERSE_JSONL)
    ap.add_argument("--out-jsonl", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--meta-out", type=Path, default=DEFAULT_META)
    args = ap.parse_args()

    if not args.source_jsonl.is_file():
        print(json.dumps({"ok": False, "error": "missing_source_jsonl", "path": str(args.source_jsonl)}))
        return 2

    meta = extract_stub(
        fixture_path=args.fixture,
        audit_path=args.audit,
        source_jsonl=args.source_jsonl,
        out_jsonl=args.out_jsonl,
    )
    args.meta_out.parent.mkdir(parents=True, exist_ok=True)
    args.meta_out.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False))
    return 0 if meta.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
