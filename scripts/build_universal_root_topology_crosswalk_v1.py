#!/usr/bin/env python3
"""Build 41k lexicon vs 31k verse-topology crosswalk report (metric plane separation, B-track)."""

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

DEFAULT_FIXTURE = ROOT / "tests/fixtures/nsm_41k_lexicon_crosswalk_500_v1.json"
DEFAULT_SPEC = ROOT / "docs/final/artifacts/UNIVERSAL_ROOT_TOPOLOGY_CROSSWALK_SPEC_V1.json"
DEFAULT_LEXICON_AUDIT = ROOT / "reports/nsm_41k_lexicon_crosswalk_audit_hf_checkpoint_v1_latest.json"
DEFAULT_VERSE_JSONL = ROOT / "tests/fixtures/logos_verse_4d_topology_stub_v1.jsonl"
DEFAULT_OUT = ROOT / "reports/universal_root_topology_crosswalk_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _rel(p: Path) -> str:
    try:
        return p.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return p.resolve().as_posix()


def _build_atom_index(jsonl: Path) -> tuple[dict[str, set[str]], dict[str, int], dict[str, int]]:
    token_to_atoms: dict[str, set[str]] = {}
    atom_verse_count: dict[str, int] = {}
    summary = {"verse_nodes": 0, "atom_nodes": 0}
    if not jsonl.is_file():
        return token_to_atoms, atom_verse_count, summary
    with jsonl.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            vid = str(row.get("verse_id") or "")
            if not vid:
                continue
            summary["verse_nodes"] += 1
            for atom in ((row.get("atom_overlay") or {}).get("top_atoms")) or []:
                aid = str(atom.get("atom_id") or "")
                form = str(atom.get("normalized_form") or "")
                if not aid:
                    continue
                atom_verse_count[aid] = atom_verse_count.get(aid, 0) + 1
                suffix = aid.split("::")[-1] if "::" in aid else aid
                for key in {form, form.lower(), suffix, suffix.lower()}:
                    if key:
                        token_to_atoms.setdefault(key, set()).add(aid)
    summary["atom_nodes"] = len(atom_verse_count)
    return token_to_atoms, atom_verse_count, summary


def _topology_hit(
    tokens: list[str],
    token_to_atoms: dict[str, set[str]],
    atom_verse_count: dict[str, int],
) -> bool:
    for tok in tokens:
        t = str(tok or "").strip()
        if not t:
            continue
        atoms = token_to_atoms.get(t) or token_to_atoms.get(t.lower()) or set()
        if any(atom_verse_count.get(a, 0) > 0 for a in atoms):
            return True
    return False


def _lexicon_hit(audit_row: dict[str, Any]) -> bool:
    status = str(audit_row.get("status") or "")
    if status in {"gap", "negative_control_leak"}:
        return False
    if status == "negative_control_ok":
        return False
    return bool(audit_row.get("en_hit") or audit_row.get("greek_hit") or audit_row.get("hebrew_hit"))


def _topology_tokens(sample: dict[str, Any], audit_row: dict[str, Any]) -> list[str]:
    tokens: list[str] = []
    extra = sample.get("topology_probe_tokens")
    if isinstance(extra, list):
        for tok in extra:
            tok_s = str(tok or "").strip()
            if tok_s:
                tokens.append(tok_s)
    for hit in audit_row.get("hits_sample") or []:
        hit_s = str(hit or "").strip()
        if hit_s:
            tokens.append(hit_s)
    lang = sample.get("lang_probes") if isinstance(sample.get("lang_probes"), dict) else {}
    for key in ("greek", "hebrew"):
        val = str(lang.get(key) or "").strip()
        if val:
            tokens.append(val)
    return tokens


def _lexicon_hit_for_sample(
    sample: dict[str, Any],
    audit_row: dict[str, Any],
    *,
    lexicon_atom_ids: frozenset[str],
) -> bool:
    if str(sample.get("control") or "") == "negative":
        return False
    aid = str(sample.get("atom_id") or "").strip()
    if aid and aid in lexicon_atom_ids:
        return True
    return _lexicon_hit(audit_row)


def _load_lexicon_atom_id_set(lexicon_path: Path | None) -> frozenset[str]:
    if lexicon_path is None or not lexicon_path.is_file():
        return frozenset()
    try:
        doc = json.loads(lexicon_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return frozenset()
    out: set[str] = set()
    for ent in doc.get("entries") or []:
        if isinstance(ent, dict):
            aid = str(ent.get("atom_id") or "").strip()
            if aid:
                out.add(aid)
    return frozenset(out)


def build_crosswalk(
    *,
    fixture: dict[str, Any],
    audit: dict[str, Any],
    token_to_atoms: dict[str, set[str]],
    atom_verse_count: dict[str, int],
    corpus_summary: dict[str, int],
    lexicon_atom_ids: frozenset[str] | None = None,
) -> dict[str, Any]:
    audit_rows = ((audit.get("baseline") or {}).get("rows")) or []
    rows_by_prime = {str(r.get("prime_en") or ""): r for r in audit_rows if r.get("prime_en")}
    samples = fixture.get("samples") or []
    atom_ids = lexicon_atom_ids or frozenset()

    pair_rows: list[dict[str, Any]] = []
    non_control = 0
    lexicon_hits = 0
    topology_hits = 0
    lexicon_only = 0
    topology_only = 0
    both_hit = 0
    neither = 0
    neg_controls = 0
    neg_leaks = 0

    for sample in samples:
        prime = str(sample.get("prime_en") or "")
        is_negative = str(sample.get("control") or "") == "negative"
        audit_row = rows_by_prime.get(prime, {})
        probe_tokens = [str(t) for t in (sample.get("probe_tokens") or []) if str(t).strip()]

        if is_negative:
            neg_controls += 1
            topo = _topology_hit(probe_tokens, token_to_atoms, atom_verse_count)
            if topo:
                neg_leaks += 1
            pair_rows.append(
                {
                    "prime_en": prime,
                    "control": "negative",
                    "topology_reachable": topo,
                    "status": "negative_control_leak" if topo else "negative_control_ok",
                }
            )
            continue

        non_control += 1
        lh = _lexicon_hit_for_sample(sample, audit_row, lexicon_atom_ids=atom_ids)
        th = _topology_hit(_topology_tokens(sample, audit_row), token_to_atoms, atom_verse_count)
        if lh:
            lexicon_hits += 1
        if th:
            topology_hits += 1
        if lh and th:
            both_hit += 1
            wall_status = "aligned_both_planes"
        elif lh and not th:
            lexicon_only += 1
            wall_status = "lexicon_only_without_topology"
        elif th and not lh:
            topology_only += 1
            wall_status = "topology_only_without_lexicon"
        else:
            neither += 1
            wall_status = "gap_both_planes"

        pair_rows.append(
            {
                "prime_en": prime,
                "lexicon_hit": lh,
                "topology_reachable": th,
                "wall_status": wall_status,
                "audit_status": audit_row.get("status"),
            }
        )

    lexicon_base = audit.get("baseline") or {}
    atom_linked = any(
        isinstance(s, dict) and s.get("atom_id") and str(s.get("control") or "") != "negative" for s in samples
    )
    prime_hit_rate = lexicon_base.get("prime_hit_rate")
    if atom_linked and non_control:
        prime_hit_rate = round(lexicon_hits / non_control, 4)
    lexicon_plane = {
        "plane": "lexicon_41k",
        "pair_count": int(fixture.get("pair_count") or len(samples)),
        "non_control_pairs": non_control,
        "negative_control_pairs": neg_controls,
        "prime_hit_rate": prime_hit_rate,
        "prime_hit_rate_source": "crosswalk_atom_linkage" if atom_linked else "lexicon_audit_baseline",
        "english_only_distortion_rate": lexicon_base.get("english_only_distortion_rate"),
        "negative_control_leak_count": lexicon_base.get("negative_control_leak_count"),
        "audit_mode": audit.get("audit_mode"),
        "audit_pointer": None,
    }
    topology_plane = {
        "plane": "topology_31k",
        "pair_count": int(fixture.get("pair_count") or len(samples)),
        "non_control_pairs": non_control,
        "negative_control_pairs": neg_controls,
        "verse_reachable_rate": round(topology_hits / non_control, 4) if non_control else None,
        "negative_topology_leak_count": neg_leaks,
        "corpus_verse_nodes": corpus_summary.get("verse_nodes"),
        "corpus_atom_nodes": corpus_summary.get("atom_nodes"),
    }
    wall_divergence = {
        "both_planes_hit": both_hit,
        "lexicon_only_without_topology": lexicon_only,
        "topology_only_without_lexicon": topology_only,
        "gap_both_planes": neither,
        "lexicon_only_without_topology_rate": round(lexicon_only / non_control, 4) if non_control else None,
        "plane_separation_reported": True,
        "collapsed_combined_score": None,
    }
    delta = {
        "verse_reachable_minus_prime_hit_rate": round(
            float(topology_plane["verse_reachable_rate"] or 0) - float(lexicon_plane["prime_hit_rate"] or 0),
            4,
        )
        if topology_plane["verse_reachable_rate"] is not None and lexicon_plane["prime_hit_rate"] is not None
        else None
    }

    return {
        "schema": "universal_root_topology_crosswalk_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "fixture": _rel(DEFAULT_FIXTURE),
        "lexicon_audit": audit.get("fixture") or _rel(DEFAULT_LEXICON_AUDIT),
        "lexicon_plane": lexicon_plane,
        "topology_plane": topology_plane,
        "wall_divergence": wall_divergence,
        "delta_topology_minus_lexicon": delta,
        "summary": {
            "pair_count": int(fixture.get("pair_count") or len(samples)),
            "non_control_pairs": non_control,
            "verse_reachable_rate": topology_plane["verse_reachable_rate"],
            "prime_hit_rate": lexicon_plane["prime_hit_rate"],
            "lexicon_only_without_topology_rate": wall_divergence["lexicon_only_without_topology_rate"],
        },
        "rows": pair_rows,
        "reproduce": "py scripts/build_universal_root_topology_crosswalk_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    ap.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    ap.add_argument("--lexicon-audit", type=Path, default=DEFAULT_LEXICON_AUDIT)
    ap.add_argument("--verse-jsonl", type=Path, default=DEFAULT_VERSE_JSONL)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    fixture = _read(args.fixture)
    audit = _read(args.lexicon_audit)
    if not fixture.get("samples"):
        print(json.dumps({"ok": False, "error": "missing_fixture_samples"}))
        return 2
    if not audit.get("baseline"):
        print(json.dumps({"ok": False, "error": "missing_lexicon_audit_baseline"}))
        return 2

    token_to_atoms, atom_verse_count, corpus_summary = _build_atom_index(args.verse_jsonl)
    if not corpus_summary.get("verse_nodes"):
        print(json.dumps({"ok": False, "error": "missing_verse_atom_jsonl"}))
        return 2

    lexicon_path = ROOT / "reports/constitution/btrack_pilot/master_codebook_lexicon_v1_41708_rows_latest.json"
    if not lexicon_path.is_file():
        from scripts.core.master_codebook_lexicon_v1_bridge import resolve_latest_codebook_path  # noqa: WPS433

        resolved = resolve_latest_codebook_path()
        lexicon_path = resolved if resolved is not None else lexicon_path
    lexicon_atom_ids = _load_lexicon_atom_id_set(lexicon_path)

    doc = build_crosswalk(
        fixture=fixture,
        audit=audit,
        token_to_atoms=token_to_atoms,
        atom_verse_count=atom_verse_count,
        corpus_summary=corpus_summary,
        lexicon_atom_ids=lexicon_atom_ids,
    )
    doc["lexicon_plane"]["audit_pointer"] = _rel(args.lexicon_audit)
    doc["inputs"] = {
        "fixture": _rel(args.fixture),
        "spec": _rel(args.spec) if args.spec.is_file() else None,
        "verse_jsonl": _rel(args.verse_jsonl),
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ok = bool(doc.get("summary", {}).get("verse_reachable_rate") is not None)
    print(json.dumps({"ok": ok, "summary": doc["summary"], "out": _rel(args.out)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
