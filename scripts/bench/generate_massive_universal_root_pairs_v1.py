#!/usr/bin/env python3
"""Generate scaled Universal Root benchmark pairs from lexicon + topology stub [HYPO · HOLD].

Rules (MKM_MASSIVE_GEN_RULES):
- Diversity: OT:NT ≈ 7:3 on non-negative rows.
- Difficulty: ~40% easy (direct lexicon probe), ~60% multihop (co-atom / bridge).
- B0 evaluability: ~12% english-surface rows (verified NSM-style en probes + dual-plane wiring).
- Wall controls: ~10% Strong's-only hard rows (no atom_id / topology_probe_tokens).
- Holdout: deterministic 80/20 train|holdout split by pair key hash.
- IP: no original_script_text; no canonical-500 duplicate probe keys; ASCII-safe export probes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.core.master_codebook_lexicon_v1_bridge import (  # noqa: E402
    lexicon_hits_for_text,
    resolve_latest_codebook_path,
)

CANONICAL_500 = ROOT / "tests/fixtures/nsm_41k_lexicon_crosswalk_500_v1.json"
TOPOLOGY_STUB = ROOT / "tests/fixtures/logos_verse_4d_topology_stub_v1.jsonl"
CHARTER = ROOT / "docs/final/artifacts/mkm_marketing_ip_governance_charter_draft_v1.json"
DEFAULT_OUT = ROOT / "tests/fixtures/nsm_41k_lexicon_crosswalk_5000_v1.json"
DEFAULT_REPORT = ROOT / "reports/massive_universal_root_pairs_gen_v1_latest.json"
IP_GOVERNANCE = ROOT / "scripts/check_mkm_marketing_ip_governance_v1.py"

NT_BOOK_PREFIXES = frozenset(
    {
        "Matt",
        "Mark",
        "Luke",
        "Jhn",
        "John",
        "Acts",
        "Rom",
        "1Cor",
        "2Cor",
        "Gal",
        "Eph",
        "Phil",
        "Col",
        "1Thess",
        "2Thess",
        "1Tim",
        "2Tim",
        "Titus",
        "Phlm",
        "Heb",
        "Jas",
        "1Pet",
        "2Pet",
        "1Jhn",
        "2Jhn",
        "3Jhn",
        "Jude",
        "Rev",
    }
)
NEGATIVE_POOL = [
    "uvicorn",
    "nextjs",
    "pytest",
    "docker",
    "kubernetes",
    "typescript",
    "react",
    "fastapi",
    "cloudflare",
    "terraform",
    "graphql",
    "mongodb",
    "tailwind",
    "eslint",
    "oauth",
    "jwt",
    "sha256",
    "openssl",
    "prometheus",
    "grafana",
]
HEBREW_BLOCK_RE = re.compile(r"[\u0590-\u05FF\u05F0-\u05F4]")
PRIME_RE = re.compile(r"^[a-z][a-z0-9_]{0,56}$")


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _rel(p: Path) -> str:
    try:
        return p.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return p.resolve().as_posix()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _pair_key(row: dict[str, Any]) -> str:
    lang = row.get("lang_probes") if isinstance(row.get("lang_probes"), dict) else {}
    return "|".join(
        [
            str(row.get("prime_en") or ""),
            str(row.get("control") or ""),
            str(lang.get("en") or ""),
            str(lang.get("greek") or ""),
            str(lang.get("hebrew") or ""),
            str(row.get("variant") or ""),
            str(row.get("bridge_token") or ""),
        ]
    )


def _answer_hash(payload: dict[str, Any]) -> str:
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _split_bucket(pair_key: str) -> str:
    digest = hashlib.sha256(pair_key.encode("utf-8")).hexdigest()
    return "holdout" if int(digest[:8], 16) % 5 == 0 else "train"


def _is_nt_verse(verse_id: str) -> bool:
    book = str(verse_id or "").split(".", 1)[0]
    return book in NT_BOOK_PREFIXES


def _load_canonical_keys(path: Path) -> set[str]:
    doc = _read_json(path)
    keys: set[str] = set()
    for row in doc.get("samples") or []:
        if isinstance(row, dict):
            keys.add(_pair_key(row))
    return keys


def _load_blocklist(charter_path: Path) -> list[str]:
    if not charter_path.is_file():
        return []
    doc = _read_json(charter_path)
    return list(doc.get("internal_term_blocklist_public") or [])


def _strongs_probe(ent: dict[str, Any]) -> str | None:
    cands = ent.get("lexicon_strongs_candidates") or []
    if not isinstance(cands, list) or not cands:
        return None
    raw = str(cands[0] or "").strip().lower()
    if re.fullmatch(r"[gh]\d{1,5}", raw):
        return raw
    return None


def _topology_index_keys(
    jsonl_path: Path,
) -> tuple[dict[str, set[str]], dict[str, int]]:
    token_to_atoms: dict[str, set[str]] = {}
    atom_verse_count: dict[str, int] = {}
    if not jsonl_path.is_file():
        return token_to_atoms, atom_verse_count
    with jsonl_path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            for atom in ((rec.get("atom_overlay") or {}).get("top_atoms")) or []:
                aid = str(atom.get("atom_id") or "")
                form = str(atom.get("normalized_form") or "")
                if not aid:
                    continue
                atom_verse_count[aid] = atom_verse_count.get(aid, 0) + 1
                suffix = aid.split("::")[-1] if "::" in aid else aid
                for key in {form, form.lower(), suffix, suffix.lower()}:
                    if key:
                        token_to_atoms.setdefault(key, set()).add(aid)
    return token_to_atoms, atom_verse_count


def _topology_reaches(tokens: list[str], token_to_atoms: dict[str, set[str]], atom_verse_count: dict[str, int]) -> bool:
    for tok in tokens:
        t = str(tok or "").strip()
        if not t:
            continue
        atoms = token_to_atoms.get(t) or token_to_atoms.get(t.lower()) or set()
        if any(atom_verse_count.get(a, 0) > 0 for a in atoms):
            return True
    return False


def _load_dual_plane_pool(
    topology_path: Path,
    lexicon_path: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    doc = _read_json(lexicon_path)
    by_aid: dict[str, dict[str, Any]] = {}
    lexicon_atom_ids: set[str] = set()
    for ent in doc.get("entries") or []:
        if not isinstance(ent, dict):
            continue
        aid = str(ent.get("atom_id") or "").strip()
        if aid:
            by_aid[aid] = ent
            lexicon_atom_ids.add(aid)

    token_to_atoms, atom_verse_count = _topology_index_keys(topology_path)
    atom_pool: list[dict[str, Any]] = []
    verse_pool: list[dict[str, Any]] = []
    seen_aids: set[str] = set()

    if not topology_path.is_file():
        return atom_pool, verse_pool

    with topology_path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            verse_id = str(rec.get("verse_id") or "")
            if not verse_id:
                continue
            verse_atoms: list[dict[str, Any]] = []
            for atom in ((rec.get("atom_overlay") or {}).get("top_atoms")) or []:
                aid = str(atom.get("atom_id") or "")
                nf = str(atom.get("normalized_form") or "").strip()
                if not aid or aid not in lexicon_atom_ids or not nf:
                    continue
                topo_tokens = [nf]
                suffix = aid.split("::")[-1] if "::" in aid else aid
                if suffix and suffix != nf:
                    topo_tokens.append(suffix)
                if not _topology_reaches(topo_tokens, token_to_atoms, atom_verse_count):
                    continue
                ent = by_aid[aid]
                lang = "greek" if aid.startswith("greek::") else "hebrew" if aid.startswith("hebrew::") else "en"
                testament = "nt" if lang == "greek" else "ot"
                strongs = _strongs_probe(ent)
                ascii_probe = nf.lower() if nf.lower().isascii() and nf.lower().replace("_", "").isalnum() else None
                lexicon_probe_en = ascii_probe or strongs or f"atom_{len(atom_pool):05d}"
                row = {
                    "atom_id": aid,
                    "normalized_form": nf,
                    "topology_probe_tokens": topo_tokens,
                    "lexicon_probe_en": lexicon_probe_en,
                    "strongs": strongs,
                    "lang": lang,
                    "testament": testament,
                }
                verse_atoms.append(row)
                if aid not in seen_aids:
                    seen_aids.add(aid)
                    atom_pool.append(row)
            if len(verse_atoms) >= 2:
                verse_pool.append(
                    {
                        "verse_id": verse_id,
                        "testament": "nt" if _is_nt_verse(verse_id) else "ot",
                        "atoms": verse_atoms,
                        "text_sha256": ((rec.get("text_span") or {}).get("text_sha256")),
                    }
                )
    return atom_pool, verse_pool


def _load_hard_strongs_pool(lexicon_path: Path, dual_atom_ids: set[str]) -> list[dict[str, Any]]:
    doc = _read_json(lexicon_path)
    pool: list[dict[str, Any]] = []
    for ent in doc.get("entries") or []:
        if not isinstance(ent, dict):
            continue
        aid = str(ent.get("atom_id") or "").strip()
        if not aid or aid in dual_atom_ids:
            continue
        strongs = _strongs_probe(ent)
        if not strongs:
            continue
        lang = "greek" if aid.startswith("greek::") else "hebrew" if aid.startswith("hebrew::") else "en"
        pool.append(
            {
                "strongs": strongs,
                "lang": lang,
                "testament": "nt" if lang == "greek" else "ot",
            }
        )
    return pool


def _load_verified_english_surface_pool(
    canonical_path: Path,
    lexicon_path: Path,
) -> list[dict[str, Any]]:
    """English tokens that hit lexicon via naive en probe (canonical 500 + NSM catalog)."""
    seen: set[str] = set()
    pool: list[dict[str, Any]] = []

    def _try_add(lang: dict[str, Any]) -> None:
        en = str(lang.get("en") or "").strip().lower()
        if not en or en in seen:
            return
        if not en.replace(" ", "").replace("_", "").isascii():
            return
        hit, _ = lexicon_hits_for_text(en, lexicon_path)
        if not hit:
            return
        seen.add(en)
        spec: dict[str, Any] = {"en": en}
        greek = str(lang.get("greek") or "").strip().lower()
        hebrew = str(lang.get("hebrew") or "").strip().lower()
        if greek:
            spec["greek"] = greek
        if hebrew:
            spec["hebrew"] = hebrew
        pool.append(spec)

    if canonical_path.is_file():
        for row in _read_json(canonical_path).get("samples") or []:
            if not isinstance(row, dict) or row.get("control") == "negative":
                continue
            lang = row.get("lang_probes") if isinstance(row.get("lang_probes"), dict) else {}
            _try_add(lang)

    try:
        from scripts.nsm_41k_crosswalk_catalog_v1 import NSM_CROSSWALK_100  # noqa: WPS433

        for row in NSM_CROSSWALK_100:
            if isinstance(row, dict):
                lang = row.get("lang_probes") if isinstance(row.get("lang_probes"), dict) else {}
                _try_add(lang)
    except ImportError:
        pass

    return pool


def _english_surface_b0_row(en_spec: dict[str, Any], dual_entry: dict[str, Any], idx: int) -> dict[str, Any]:
    en = str(en_spec["en"])
    lang_probes: dict[str, str] = {"en": en}
    if en_spec.get("greek"):
        lang_probes["greek"] = str(en_spec["greek"])
    if en_spec.get("hebrew"):
        lang_probes["hebrew"] = str(en_spec["hebrew"])
    row = {
        "prime_en": f"ur_mass_en_b0_{idx:05d}",
        "probe_tokens": [en],
        "lang_probes": lang_probes,
        "difficulty": "easy",
        "hop_count": 1,
        "testament_bucket": dual_entry["testament"],
        "labels": ["research_only", "universal_root_fixture_v1", "auto_generated"],
        "source_note": "massive_gen_english_surface_b0",
    }
    _attach_dual_plane_fields(row, dual_entry)
    row["answer_hash"] = _answer_hash(
        {"kind": "english_surface_b0", "en": en, "atom_id": dual_entry["atom_id"]}
    )
    row["split"] = _split_bucket(_pair_key(row))
    return row


def _hard_strongs_row(entry: dict[str, Any], idx: int) -> dict[str, Any]:
    probe = str(entry["strongs"])
    row = {
        "prime_en": f"ur_mass_hard_{idx:05d}",
        "probe_tokens": [probe],
        "lang_probes": {"en": probe},
        "difficulty": "multihop",
        "hop_count": 2,
        "testament_bucket": entry["testament"],
        "labels": ["research_only", "universal_root_fixture_v1", "auto_generated"],
        "source_note": "massive_gen_strongs_hard_control",
    }
    row["answer_hash"] = _answer_hash({"kind": "hard_strongs", "strongs": probe})
    row["split"] = _split_bucket(_pair_key(row))
    return row


def _negative_row(token: str, idx: int) -> dict[str, Any]:
    t = token.strip().lower()
    row = {
        "prime_en": f"control_negative_{t.replace('-', '_')}_{idx:04d}",
        "probe_tokens": [t],
        "control": "negative",
        "lang_probes": {"en": t},
        "difficulty": "easy",
        "hop_count": 0,
        "testament_bucket": "na",
        "labels": ["research_only", "universal_root_fixture_v1", "auto_generated"],
        "source_note": "massive_gen_negative_control",
    }
    row["answer_hash"] = _answer_hash({"kind": "negative", "token": t})
    row["split"] = _split_bucket(_pair_key(row))
    return row


def _attach_dual_plane_fields(row: dict[str, Any], entry: dict[str, Any]) -> None:
    row["atom_id"] = entry["atom_id"]
    row["topology_probe_tokens"] = list(entry["topology_probe_tokens"])
    if entry.get("strongs"):
        row["strongs_probe"] = entry["strongs"]


def _easy_row(entry: dict[str, Any], idx: int) -> dict[str, Any]:
    probe_en = str(entry["lexicon_probe_en"])
    lang = str(entry["lang"])
    lang_probes: dict[str, str] = {"en": probe_en}
    if lang == "greek" and probe_en.isascii():
        lang_probes["greek"] = probe_en
    elif lang == "hebrew" and probe_en.isascii():
        lang_probes["hebrew"] = probe_en
    row = {
        "prime_en": f"ur_mass_easy_{idx:05d}",
        "probe_tokens": [probe_en],
        "lang_probes": lang_probes,
        "difficulty": "easy",
        "hop_count": 1,
        "testament_bucket": entry["testament"],
        "labels": ["research_only", "universal_root_fixture_v1", "auto_generated"],
        "source_note": "massive_gen_dual_plane_direct",
    }
    _attach_dual_plane_fields(row, entry)
    row["answer_hash"] = _answer_hash(
        {"kind": "easy", "atom_id": entry["atom_id"], "strongs": entry.get("strongs"), "probe_en": probe_en}
    )
    row["split"] = _split_bucket(_pair_key(row))
    return row


def _multihop_topology_row(topo: dict[str, Any], idx: int) -> dict[str, Any]:
    atoms = topo["atoms"]
    a, b = random.sample(atoms, 2)
    probe_en = str(a["lexicon_probe_en"])
    topo_tokens = list(dict.fromkeys(a["topology_probe_tokens"] + b["topology_probe_tokens"]))
    row = {
        "prime_en": f"ur_mass_mh_topo_{idx:05d}",
        "probe_tokens": [probe_en, str(b["lexicon_probe_en"])],
        "bridge_token": str(b["lexicon_probe_en"]),
        "lang_probes": {"en": probe_en, "bridge": str(b["lexicon_probe_en"])},
        "difficulty": "multihop",
        "hop_count": 3,
        "testament_bucket": topo["testament"],
        "verse_id_hint": topo["verse_id"],
        "labels": ["research_only", "universal_root_fixture_v1", "auto_generated"],
        "source_note": "massive_gen_topology_coatom_multihop",
        "atom_id": a["atom_id"],
        "bridge_atom_id": b["atom_id"],
        "topology_probe_tokens": topo_tokens,
    }
    if a.get("strongs"):
        row["strongs_probe"] = a["strongs"]
    row["answer_hash"] = _answer_hash(
        {
            "kind": "multihop_topology",
            "verse_id": topo["verse_id"],
            "atom_a": a["atom_id"],
            "atom_b": b["atom_id"],
            "text_sha256": topo.get("text_sha256"),
        }
    )
    row["split"] = _split_bucket(_pair_key(row))
    return row


def _multihop_lexicon_row(a: dict[str, Any], b: dict[str, Any], idx: int) -> dict[str, Any]:
    probe_a, probe_b = str(a["lexicon_probe_en"]), str(b["lexicon_probe_en"])
    testament = a["testament"] if a["testament"] == b["testament"] else random.choice([a["testament"], b["testament"]])
    topo_tokens = list(dict.fromkeys(a["topology_probe_tokens"] + b["topology_probe_tokens"]))
    row = {
        "prime_en": f"ur_mass_mh_lex_{idx:05d}",
        "probe_tokens": [probe_a, probe_b],
        "bridge_token": probe_b,
        "lang_probes": {"en": probe_a, "bridge": probe_b},
        "difficulty": "multihop",
        "hop_count": 3,
        "testament_bucket": testament,
        "labels": ["research_only", "universal_root_fixture_v1", "auto_generated"],
        "source_note": "massive_gen_lexicon_bridge_multihop",
        "atom_id": a["atom_id"],
        "bridge_atom_id": b["atom_id"],
        "topology_probe_tokens": topo_tokens,
    }
    if a.get("strongs"):
        row["strongs_probe"] = a["strongs"]
    row["answer_hash"] = _answer_hash(
        {"kind": "multihop_lexicon", "atom_a": a["atom_id"], "atom_b": b["atom_id"]}
    )
    row["split"] = _split_bucket(_pair_key(row))
    return row


def _scan_fixture_ip_leaks(doc: dict[str, Any], blocklist: list[str]) -> list[str]:
    failures: list[str] = []
    blob = json.dumps(doc, ensure_ascii=False)
    for term in blocklist:
        if term and term in blob:
            failures.append(f"blocklist_term:{term}")
    if "original_script_text" in blob:
        failures.append("original_script_text_leak")
    for row in doc.get("samples") or []:
        if not isinstance(row, dict):
            continue
        for field in ("probe_tokens", "lang_probes", "source_note"):
            val = row.get(field)
            text = json.dumps(val, ensure_ascii=False) if not isinstance(val, str) else val
            if HEBREW_BLOCK_RE.search(text):
                failures.append(f"hebrew_script_in_{field}:{row.get('prime_en')}")
    return failures


def _overlap_rate(samples: list[dict[str, Any]], canonical_keys: set[str]) -> float:
    if not samples:
        return 0.0
    overlap = sum(1 for r in samples if _pair_key(r) in canonical_keys)
    return round(overlap / len(samples), 6)


def _testament_mix(samples: list[dict[str, Any]]) -> dict[str, float]:
    non_neg = [r for r in samples if r.get("control") != "negative"]
    if not non_neg:
        return {"ot": 0.0, "nt": 0.0}
    c = Counter(str(r.get("testament_bucket") or "ot") for r in non_neg)
    total = sum(c.values())
    return {k: round(v / total, 4) for k, v in c.items()}


def _difficulty_mix(samples: list[dict[str, Any]]) -> dict[str, float]:
    non_neg = [r for r in samples if r.get("control") != "negative"]
    if not non_neg:
        return {"easy": 0.0, "multihop": 0.0}
    c = Counter(str(r.get("difficulty") or "easy") for r in non_neg)
    total = sum(c.values())
    return {k: round(v / total, 4) for k, v in c.items()}


def generate_massive_pairs(
    *,
    target: int,
    seed: int,
    canonical_path: Path,
    topology_path: Path,
    lexicon_path: Path,
    neg_fraction: float = 0.05,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rng = random.Random(seed)
    random.seed(seed)

    canonical_keys = _load_canonical_keys(canonical_path)
    atom_pool, topo_pool = _load_dual_plane_pool(topology_path, lexicon_path)
    if not atom_pool:
        raise RuntimeError("dual_plane atom pool empty — check topology stub + lexicon path")
    dual_ids = {str(a["atom_id"]) for a in atom_pool}
    hard_pool = _load_hard_strongs_pool(lexicon_path, dual_ids)

    neg_target = max(25, int(target * neg_fraction))
    non_neg_target = target - neg_target
    english_pool = _load_verified_english_surface_pool(canonical_path, lexicon_path)
    english_b0_target = min(max(1, int(non_neg_target * 0.12)), len(english_pool) * 40, non_neg_target - 2)
    hard_target = min(len(hard_pool), max(1, int(non_neg_target * 0.10)))
    dual_non_neg = non_neg_target - hard_target - english_b0_target
    easy_target = int(dual_non_neg * 0.40)
    mh_target = dual_non_neg - easy_target

    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    stats = Counter()

    def try_add(row: dict[str, Any]) -> bool:
        key = _pair_key(row)
        if key in seen or key in canonical_keys:
            return False
        seen.add(key)
        out.append(row)
        return True

    # Negatives first (fixed pool + synthetic suffix if needed)
    neg_i = 0
    while sum(1 for r in out if r.get("control") == "negative") < neg_target:
        tok = NEGATIVE_POOL[neg_i % len(NEGATIVE_POOL)]
        row = _negative_row(tok, neg_i)
        if try_add(row):
            stats["negative"] += 1
        neg_i += 1
        if neg_i > neg_target * 20:
            break

    # Hard Strong's-only controls first (reserved quota — wall divergence)
    hard_candidates = hard_pool[:]
    rng.shuffle(hard_candidates)
    hard_i = 0
    for entry in hard_candidates:
        if stats["hard_strongs"] >= hard_target:
            break
        row = _hard_strongs_row(entry, hard_i)
        if try_add(row):
            stats["hard_strongs"] += 1
            hard_i += 1

    # English-surface B0 evaluable rows (verified en lexicon hit + dual-plane wiring)
    en_i = 0
    dual_for_en = atom_pool[:]
    rng.shuffle(dual_for_en)
    for entry in dual_for_en:
        if stats["english_surface_b0"] >= english_b0_target or not english_pool:
            break
        en_spec = english_pool[en_i % len(english_pool)]
        row = _english_surface_b0_row(en_spec, entry, en_i)
        if try_add(row):
            stats["english_surface_b0"] += 1
            en_i += 1

    # Easy dual-plane rows — quota toward OT:NT ≈ 7:3
    easy_candidates = atom_pool[:]
    rng.shuffle(easy_candidates)
    easy_i = 0
    ot_easy = 0
    nt_easy = 0
    for entry in easy_candidates:
        if stats["easy"] >= easy_target:
            break
        bucket = str(entry["testament"])
        total_e = ot_easy + nt_easy
        if total_e > 20:
            ot_rate = ot_easy / total_e
            if ot_rate < 0.68 and bucket == "nt":
                continue
            if ot_rate > 0.72 and bucket == "ot":
                continue
        row = _easy_row(entry, easy_i)
        if try_add(row):
            stats["easy"] += 1
            easy_i += 1
            if bucket == "nt":
                nt_easy += 1
            else:
                ot_easy += 1

    # Multihop topology first (harder; uses verse co-atoms)
    mh_i = 0
    attempts = 0
    topo_rows = topo_pool[:]
    rng.shuffle(topo_rows)
    topo_idx = 0
    while stats["multihop"] < mh_target and topo_idx < len(topo_rows) * 4:
        topo = topo_rows[topo_idx % len(topo_rows)]
        topo_idx += 1
        row = _multihop_topology_row(topo, mh_i)
        if try_add(row):
            stats["multihop_topology"] += 1
            stats["multihop"] += 1
            mh_i += 1

    # Fill remaining multihop with lexicon bridges
    while stats["multihop"] < mh_target and attempts < mh_target * 100:
        attempts += 1
        a, b = rng.sample(atom_pool, 2)
        row = _multihop_lexicon_row(a, b, mh_i)
        if try_add(row):
            stats["multihop"] += 1
            mh_i += 1

    # Fill any deficit with dual-plane easy variants
    fill_i = 0
    while len(out) < target and fill_i < target * 3:
        entry = rng.choice(atom_pool)
        row = _easy_row(entry, 90000 + fill_i)
        row["variant"] = f"fill_{fill_i}"
        row["prime_en"] = f"ur_mass_fill_{fill_i:05d}"
        if try_add(row):
            stats["easy_fill"] += 1
        fill_i += 1

    if len(out) > target:
        out = out[:target]

    meta = {
        "dual_plane_atom_pool": len(atom_pool),
        "english_surface_pool": len(english_pool),
        "english_surface_b0_target": english_b0_target,
        "hard_strongs_pool": len(hard_pool),
        "hard_strongs_target": hard_target,
        "topology_verse_pool": len(topo_pool),
        "target": target,
        "actual": len(out),
        "seed": seed,
        "stats": dict(stats),
        "easy_pool_size": len(atom_pool),
        "canonical_overlap_rate": _overlap_rate(out, canonical_keys),
    }
    return out, meta


def build_fixture_doc(
    samples: list[dict[str, Any]],
    *,
    target: int,
    seed: int,
    meta: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema": "nsm_41k_lexicon_crosswalk_massive_v1",
        "version": "1.2.0",
        "description": f"Scaled UR bench ({len(samples)} pairs) — dual-plane wiring + english-surface B0 slice; canonical 500 disjoint.",
        "source_note": "scripts/bench/generate_massive_universal_root_pairs_v1.py",
        "research_only": True,
        "send_gate": "HOLD",
        "pair_count": len(samples),
        "generation": {
            "target": target,
            "seed": seed,
            "rules_id": "MKM_MASSIVE_GEN_RULES",
            "train_holdout_ratio": "80:20",
            **meta,
        },
        "samples": samples,
    }


def run_ip_governance_gate() -> tuple[bool, str]:
    if not IP_GOVERNANCE.is_file():
        return True, "skip_missing_governance_script"
    proc = subprocess.run(
        [sys.executable, str(IP_GOVERNANCE)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    tail = (proc.stdout or proc.stderr or "")[-300:]
    return proc.returncode == 0, tail


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--target", type=int, default=5000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--canonical", type=Path, default=CANONICAL_500)
    ap.add_argument("--topology", type=Path, default=TOPOLOGY_STUB)
    ap.add_argument("--lexicon", type=Path, default=None)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    ap.add_argument("--skip-ip-governance", action="store_true")
    args = ap.parse_args()

    lexicon_path = args.lexicon or resolve_latest_codebook_path()
    if lexicon_path is None or not lexicon_path.is_file():
        print(json.dumps({"ok": False, "error": "missing_lexicon"}))
        return 2

    samples, meta = generate_massive_pairs(
        target=args.target,
        seed=args.seed,
        canonical_path=args.canonical,
        topology_path=args.topology,
        lexicon_path=lexicon_path,
    )
    doc = build_fixture_doc(samples, target=args.target, seed=args.seed, meta=meta)

    blocklist = _load_blocklist(CHARTER)
    ip_failures = _scan_fixture_ip_leaks(doc, blocklist)
    overlap = float(meta.get("canonical_overlap_rate") or 0.0)

    gate_ok = True
    gate_failures: list[str] = []
    if len(samples) < args.target:
        gate_ok = False
        gate_failures.append(f"pair_count_below_target:{len(samples)}<{args.target}")
    if len(samples) > args.target:
        gate_ok = False
        gate_failures.append(f"pair_count_above_target:{len(samples)}>{args.target}")
    if overlap > 0.0:
        gate_ok = False
        gate_failures.append(f"canonical_overlap_rate:{overlap}")
    if ip_failures:
        gate_ok = False
        gate_failures.extend(ip_failures)

    ip_gov_ok, ip_gov_tail = (True, "skipped") if args.skip_ip_governance else run_ip_governance_gate()
    if not ip_gov_ok:
        gate_ok = False
        gate_failures.append("marketing_ip_governance_exit_nonzero")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    report = {
        "schema": "massive_universal_root_pairs_gen_report_v1",
        "generated_at_utc": _utc(),
        "ok": gate_ok,
        "pair_count": len(samples),
        "target": args.target,
        "canonical_overlap_rate": overlap,
        "testament_mix": _testament_mix(samples),
        "difficulty_mix": _difficulty_mix(samples),
        "split_counts": dict(Counter(str(r.get("split") or "train") for r in samples)),
        "gate_failures": gate_failures,
        "ip_governance_ok": ip_gov_ok,
        "ip_governance_tail": ip_gov_tail,
        "out_fixture": _rel(args.out),
        "lexicon_path": _rel(lexicon_path),
        "reproducible_command": (
            f"py scripts/bench/generate_massive_universal_root_pairs_v1.py --target {args.target} --seed {args.seed}"
        ),
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": gate_ok,
                "pair_count": len(samples),
                "overlap_rate": overlap,
                "testament_mix": report["testament_mix"],
                "difficulty_mix": report["difficulty_mix"],
                "out": str(args.out),
                "report": str(args.report),
            },
            ensure_ascii=False,
        )
    )
    return 0 if gate_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
