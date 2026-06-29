#!/usr/bin/env python3
"""P3 Root Generator v0 — merge baseline 41k anchor + extension overlays (B-track, extension profile)."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.core.master_codebook_lexicon_v1_bridge import resolve_latest_codebook_path  # noqa: E402

PILOT = ROOT / "reports/constitution/btrack_pilot"
CONTRACT = ROOT / "docs/final/artifacts/P3_ROOT_GENERATOR_BENCH_CONTRACT_V1.json"
DEFAULT_REPORT = ROOT / "reports/p3_root_candidate_lexicon_build_v1_latest.json"
ATOM_ID_RE = re.compile(r"^[a-z][a-z0-9_]*::.+$", re.I)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    try:
        return p.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return p.resolve().as_posix()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_lexicon(path: Path) -> dict[str, Any]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    if doc.get("schema") != "master_codebook_lexicon_v1":
        raise ValueError(f"expected master_codebook_lexicon_v1, got {doc.get('schema')!r}")
    return doc


def _entry_key(entry: dict[str, Any]) -> tuple[str, str]:
    lang = str(entry.get("lang") or "").strip().lower()
    form = str(entry.get("normalized_form") or "").strip().lower()
    return lang, form


def _blank_entry(
    *,
    atom_id: str,
    lang: str,
    normalized_form: str,
    source_lane: str,
    curated_tier: str = "p3_extension_v0",
    external_ref: str | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "atom_id": atom_id,
        "lang": lang,
        "normalized_form": normalized_form,
        "occurrences": 0,
        "lexicon_strongs_candidates": [],
        "lexicon_match_method": source_lane,
        "morphhb_match_method": "skipped_lang",
        "morphhb_strongs_hints": [],
        "morphhb_chosen": None,
        "morphhb_disambiguation": None,
        "curated_tier": curated_tier,
    }
    if external_ref:
        row["p3_external_ref"] = external_ref
    return row


def _normalize_extension_row(row: dict[str, Any], *, default_lane: str) -> dict[str, Any] | None:
    form = str(row.get("normalized_form") or row.get("term") or "").strip()
    if not form:
        return None
    lang = str(row.get("lang") or "other").strip().lower()
    lane = str(row.get("source_lane") or default_lane).strip()
    atom_id = str(row.get("atom_id") or f"{lane}::{form}").strip()
    if not ATOM_ID_RE.match(atom_id):
        atom_id = f"{lane}::{form}"
    return _blank_entry(
        atom_id=atom_id,
        lang=lang,
        normalized_form=form,
        source_lane=lane,
        curated_tier=str(row.get("curated_tier") or "p3_extension_v0"),
        external_ref=str(row.get("external_ref") or "") or None,
    )


def _iter_jsonl(path: Path):
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        if isinstance(obj, dict):
            yield obj


def _extensions_from_alias_table(path: Path) -> list[dict[str, Any]]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    if doc.get("schema") != "herbs_formulas_alias_table_v1":
        raise ValueError(f"unexpected alias table schema: {doc.get('schema')!r}")
    out: list[dict[str, Any]] = []
    seen: set[str] = set()

    def _push(form: str, lang: str, ref: str, tier: str) -> None:
        form = form.strip()
        if not form:
            return
        key = f"{lang}::{form.lower()}"
        if key in seen:
            return
        seen.add(key)
        out.append(
            _blank_entry(
                atom_id=f"herbs_formulas_alias_v1::{ref}::{lang}",
                lang=lang,
                normalized_form=form,
                source_lane="herbs_formulas_alias_v1",
                curated_tier=tier,
                external_ref=ref,
            )
        )

    for herb in doc.get("herbs") or []:
        if not isinstance(herb, dict):
            continue
        ref = str(herb.get("canonical_id") or "")
        for key, lang in (("canonical_name_ko", "ko"), ("canonical_name_hans", "zh"), ("pinyin", "zh")):
            val = herb.get(key)
            if isinstance(val, str):
                _push(val, lang, ref, "tcm_herb_alias")
        for alias in herb.get("aliases") or []:
            if isinstance(alias, str):
                _push(alias, "ko" if any("\uac00" <= c <= "\ud7a3" for c in alias) else "en", ref, "tcm_herb_alias")

    for formula in doc.get("formulas") or []:
        if not isinstance(formula, dict):
            continue
        ref = str(formula.get("formula_id") or "")
        for key, lang in (("canonical_name_ko", "ko"), ("canonical_name_hans", "zh")):
            val = formula.get(key)
            if isinstance(val, str):
                _push(val, lang, ref, "tcm_formula_alias")

    return out


LOGOS_SEED_LANGS = frozenset({"hebrew", "greek"})


def _logos_seed_entries(base_entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for entry in base_entries:
        if not isinstance(entry, dict):
            continue
        lang = str(entry.get("lang") or "").strip().lower()
        aid = str(entry.get("atom_id") or "")
        if lang in LOGOS_SEED_LANGS or aid.startswith(("hebrew::", "greek::")):
            out.append(dict(entry))
    return out


def _merge_extension_entries(
    baseline_entries: list[dict[str, Any]],
    proposed: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    baseline_ids = {str(e.get("atom_id")) for e in baseline_entries if e.get("atom_id")}
    baseline_keys = {_entry_key(e) for e in baseline_entries if e.get("normalized_form")}
    merged = list(baseline_entries)
    audit = {
        "added": [],
        "skipped_existing_atom_id": [],
        "skipped_duplicate_form": [],
        "skipped_invalid": [],
    }

    for raw in proposed:
        if not isinstance(raw, dict):
            audit["skipped_invalid"].append({"reason": "not_object"})
            continue
        entry = raw if raw.get("schema") is None else raw
        if "normalized_form" not in entry and "term" in entry:
            norm = _normalize_extension_row(entry, default_lane="p3_extension_v0")
            if norm is None:
                audit["skipped_invalid"].append({"reason": "empty_form", "raw": raw})
                continue
            entry = norm

        aid = str(entry.get("atom_id") or "")
        if aid in baseline_ids:
            audit["skipped_existing_atom_id"].append(aid)
            continue
        key = _entry_key(entry)
        if key in baseline_keys:
            audit["skipped_duplicate_form"].append({"atom_id": aid, "key": list(key)})
            continue

        merged.append(entry)
        baseline_ids.add(aid)
        baseline_keys.add(key)
        audit["added"].append(aid)

    return merged, audit


def _collect_extensions(
    *,
    overlay_paths: list[Path],
    extension_jsonl_paths: list[Path],
    alias_table_paths: list[Path],
) -> list[dict[str, Any]]:
    proposed: list[dict[str, Any]] = []

    for path in overlay_paths:
        doc = _load_lexicon(path)
        for ent in doc.get("entries") or []:
            if isinstance(ent, dict):
                proposed.append(ent)

    for path in extension_jsonl_paths:
        for row in _iter_jsonl(path):
            norm = _normalize_extension_row(row, default_lane="p3_extension_jsonl_v1")
            if norm:
                proposed.append(norm)

    for path in alias_table_paths:
        proposed.extend(_extensions_from_alias_table(path))

    return proposed


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--baseline-lexicon", type=Path, default=None)
    ap.add_argument("--overlay-lexicon", action="append", default=[], type=Path)
    ap.add_argument("--extension-jsonl", action="append", default=[], type=Path)
    ap.add_argument("--alias-table", action="append", default=[], type=Path)
    ap.add_argument("--profile", choices=("extension", "replacement"), default="extension")
    ap.add_argument(
        "--seed-logos-atoms-from-baseline",
        action="store_true",
        help="Replacement only: seed candidate with baseline hebrew/greek atoms before extensions.",
    )
    ap.add_argument("--slug", default="v0")
    ap.add_argument("--out-json", type=Path, default=None)
    ap.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = ap.parse_args()

    baseline_path = args.baseline_lexicon
    if baseline_path is None and CONTRACT.is_file():
        anchor = str(
            (json.loads(CONTRACT.read_text(encoding="utf-8")).get("philosophy") or {}).get(
                "single_anchor_ssot"
            )
            or ""
        )
        baseline_path = ROOT / anchor if anchor else None
    if baseline_path is None or not baseline_path.is_file():
        baseline_path = resolve_latest_codebook_path()
    if baseline_path is None or not baseline_path.is_file():
        print("ABORT: baseline lexicon not found")
        return 1

    baseline_path = baseline_path.resolve()
    base_doc = _load_lexicon(baseline_path)
    base_entries = list(base_doc.get("entries") or [])
    base_n = len(base_entries)

    overlay_paths = [p.resolve() for p in args.overlay_lexicon if p.is_file()]
    jsonl_paths = [p.resolve() for p in args.extension_jsonl if p.is_file()]
    alias_paths = [p.resolve() for p in args.alias_table if p.is_file()]

    proposed = _collect_extensions(
        overlay_paths=overlay_paths,
        extension_jsonl_paths=jsonl_paths,
        alias_table_paths=alias_paths,
    )

    if args.profile == "replacement":
        seed_entries = _logos_seed_entries(base_entries) if args.seed_logos_atoms_from_baseline else []
        merged_entries, audit = _merge_extension_entries(seed_entries, proposed)
        if args.seed_logos_atoms_from_baseline:
            merge_policy = "replacement_logos_seed_plus_extensions_v1"
        else:
            merge_policy = "replacement_extensions_only_v1"
        base_doc = {
            "schema": "master_codebook_lexicon_v1",
            "inputs": {
                "replacement_seed": {
                    "baseline_reference": _rel(baseline_path),
                    "baseline_row_count": base_n,
                    "logos_seed_enabled": bool(args.seed_logos_atoms_from_baseline),
                    "logos_seed_row_count": len(seed_entries),
                    "logos_seed_langs": sorted(LOGOS_SEED_LANGS),
                    "note": (
                        "Replacement research candidate; baseline retained for A/B bench only."
                    ),
                }
            },
            "rail_coverage_note": (
                "P3 replacement research candidate — not production anchor."
            ),
        }
    else:
        if args.seed_logos_atoms_from_baseline:
            print("ABORT: --seed-logos-atoms-from-baseline requires --profile replacement")
            return 2
        merged_entries, audit = _merge_extension_entries(base_entries, proposed)
        merge_policy = "extension_anchor_preserve"
    out_n = len(merged_entries)

    slug = re.sub(r"[^a-z0-9_]+", "_", args.slug.lower()).strip("_") or "v0"
    out_json = args.out_json
    if out_json is None:
        out_json = PILOT / f"master_codebook_lexicon_v1_{out_n}_p3_root_candidate_{slug}_latest.json"
    out_json = out_json.resolve()
    out_json.parent.mkdir(parents=True, exist_ok=True)

    payload = dict(base_doc)
    payload["generated_at_utc"] = _utc()
    payload["row_count"] = out_n
    payload["entries"] = merged_entries
    payload["p3_root_generator_meta"] = {
        "schema": "p3_root_candidate_lexicon_build_v1",
        "version": "0.1.0",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "send_gate": "HOLD",
        "track_a_blocked": True,
        "profile": args.profile,
        "merge_policy": merge_policy,
        "baseline_lexicon": _rel(baseline_path),
        "baseline_row_count": base_n,
        "candidate_row_count": out_n,
        "rows_added": len(audit["added"]),
        "logos_seed_row_count": len(_logos_seed_entries(base_entries))
        if args.profile == "replacement" and args.seed_logos_atoms_from_baseline
        else 0,
        "inputs": {
            "overlay_lexicons": [_rel(p) for p in overlay_paths],
            "extension_jsonls": [_rel(p) for p in jsonl_paths],
            "alias_tables": [_rel(p) for p in alias_paths],
        },
        "audit": {
            **audit,
            "added_sample": audit["added"][:12],
            "skipped_existing_atom_id_count": len(audit["skipped_existing_atom_id"]),
            "skipped_duplicate_form_count": len(audit["skipped_duplicate_form"]),
        },
        "reproduce_bench": (
            f"py scripts/run_p3_root_generator_bench_v1.py --profile {args.profile} "
            f"--candidate-lexicon {_rel(out_json)}"
        ),
    }

    out_json.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")

    report = {
        "schema": "p3_root_candidate_lexicon_build_report_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "candidate_path": _rel(out_json),
        "candidate_sha256": _sha256_file(out_json),
        "baseline_row_count": base_n,
        "candidate_row_count": out_n,
        "rows_added": len(audit["added"]),
        "meta": payload["p3_root_generator_meta"],
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "wrote": _rel(out_json),
                "report": _rel(args.report),
                "baseline_rows": base_n,
                "candidate_rows": out_n,
                "rows_added": len(audit["added"]),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
