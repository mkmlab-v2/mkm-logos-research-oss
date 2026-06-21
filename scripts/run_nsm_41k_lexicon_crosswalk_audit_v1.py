#!/usr/bin/env python3
"""NSM semantic prime ↔ 41k lexicon crosswalk audit (100/500-pair distortion report, B-track)."""

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

from scripts.core.master_codebook_lexicon_v1_bridge import (  # noqa: E402
    lexicon_hits_for_text,
    resolve_latest_codebook_path,
)
from scripts.deepnsm_shadow_explication_lib_v1 import (  # noqa: E402
    load_explication_sidecar,
    lookup_tokens_for_resolution,
    sidecar_key_for_sample,
)
from scripts.nsm_41k_crosswalk_catalog_v1 import NSM_CROSSWALK_100  # noqa: E402

DEFAULT_FIXTURE = ROOT / "tests/fixtures/nsm_41k_lexicon_crosswalk_500_v1.json"
DEFAULT_FIXTURE_100 = ROOT / "tests/fixtures/nsm_41k_lexicon_crosswalk_100_v1.json"
DEFAULT_OUT = ROOT / "reports/nsm_41k_lexicon_crosswalk_audit_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    try:
        return p.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return p.resolve().as_posix()


def _token_hit(token: str, lexicon: Path) -> tuple[bool, list[str]]:
    hits, _ = lexicon_hits_for_text(token.strip().lower(), lexicon)
    return bool(hits), sorted(hits)[:4]


def _multi_token_hit(tokens: list[str], lexicon: Path) -> tuple[bool, list[str]]:
    merged: set[str] = set()
    for tok in tokens:
        tok = str(tok or "").strip().lower()
        if not tok:
            continue
        hit, hits = _token_hit(tok, lexicon)
        if hit:
            merged.update(hits)
    return bool(merged), sorted(merged)[:4]


def _classify_sample(
    sample: dict[str, Any],
    lexicon: Path,
    *,
    sidecar_row: dict[str, Any] | None = None,
    orig_probes_only: bool = False,
) -> dict[str, Any]:
    lang = sample.get("lang_probes") if isinstance(sample.get("lang_probes"), dict) else {}
    en_tok = str(lang.get("en") or "").strip().lower()
    greek_tok = str(lang.get("greek") or "").strip().lower()
    hebrew_tok = str(lang.get("hebrew") or "").strip().lower()
    is_negative = str(sample.get("control") or "") == "negative"

    if orig_probes_only and (greek_tok or hebrew_tok):
        en_tok = ""

    en_hit, en_hits = _token_hit(en_tok, lexicon) if en_tok else (False, [])
    greek_tokens = [greek_tok] if greek_tok else []
    hebrew_tokens = [hebrew_tok] if hebrew_tok else []
    resolution_mode = "raw_latin"
    if sidecar_row:
        resolved = sidecar_row.get("resolved_probes") if isinstance(sidecar_row.get("resolved_probes"), dict) else {}
        greek_tokens = lookup_tokens_for_resolution(resolved.get("greek") or {}) or greek_tokens
        hebrew_tokens = lookup_tokens_for_resolution(resolved.get("hebrew") or {}) or hebrew_tokens
        resolution_mode = "deepnsm_shadow"

    greek_hit, greek_hits = _multi_token_hit(greek_tokens, lexicon) if greek_tokens else (False, [])
    hebrew_hit, hebrew_hits = _multi_token_hit(hebrew_tokens, lexicon) if hebrew_tokens else (False, [])
    orig_hit = greek_hit or hebrew_hit
    any_hit = en_hit or orig_hit

    if is_negative:
        status = "negative_control_ok" if not any_hit else "negative_control_leak"
    elif not any_hit:
        status = "gap"
    elif en_hit and not orig_hit and (greek_tok or hebrew_tok):
        status = "english_only_distortion"
    elif orig_hit:
        status = "aligned_original_language"
    elif en_hit:
        status = "english_only_ok"
    else:
        status = "gap"

    row = {
        "prime_en": sample.get("prime_en"),
        "status": status,
        "en_hit": en_hit,
        "greek_hit": greek_hit,
        "hebrew_hit": hebrew_hit,
        "hits_sample": sorted(set(en_hits + greek_hits + hebrew_hits))[:6],
        "control": sample.get("control"),
        "resolution_mode": resolution_mode,
    }
    if sidecar_row:
        row["shadow_resolution"] = {
            "greek": (sidecar_row.get("resolved_probes") or {}).get("greek", {}).get("resolution"),
            "hebrew": (sidecar_row.get("resolved_probes") or {}).get("hebrew", {}).get("resolution"),
        }
    if orig_probes_only:
        row["orig_probes_only"] = True
    return row


def audit_lexicon(
    lexicon: Path,
    samples: list[dict[str, Any]],
    *,
    sidecar: dict[str, dict[str, Any]] | None = None,
    orig_probes_only: bool = False,
) -> dict[str, Any]:
    rows = [
        _classify_sample(
            s,
            lexicon,
            sidecar_row=(sidecar or {}).get(sidecar_key_for_sample(s, i)),
            orig_probes_only=orig_probes_only,
        )
        for i, s in enumerate(samples)
    ]
    non_control = [r for r in rows if r.get("control") != "negative"]
    controls = [r for r in rows if r.get("control") == "negative"]
    aligned = sum(1 for r in non_control if r["status"] in {"aligned_original_language", "english_only_ok"})
    distortion = sum(1 for r in non_control if r["status"] == "english_only_distortion")
    gaps = sum(1 for r in non_control if r["status"] == "gap")
    control_leaks = sum(1 for r in controls if r["status"] == "negative_control_leak")
    n = len(non_control) or 1
    return {
        "lexicon_path": _rel(lexicon),
        "pair_count": len(samples),
        "non_control_pairs": len(non_control),
        "negative_control_pairs": len(controls),
        "prime_hit_rate": round(aligned / n, 4),
        "aligned_original_language_count": sum(
            1 for r in non_control if r["status"] == "aligned_original_language"
        ),
        "english_only_distortion_count": distortion,
        "english_only_distortion_rate": round(distortion / n, 4),
        "gap_count": gaps,
        "gap_rate": round(gaps / n, 4),
        "negative_control_leak_count": control_leaks,
        "rows": rows,
    }


def export_fixture(path: Path) -> None:
    doc = {
        "schema": "nsm_41k_lexicon_crosswalk_100_v1",
        "version": "1.0.0",
        "description": "100-pair NSM prime → Logos lexicon probe catalog (existence-only lookup).",
        "source_note": "DeepNSM-inspired manual crosswalk; distortion audit via run_nsm_41k_lexicon_crosswalk_audit_v1.py",
        "research_only": True,
        "send_gate": "HOLD",
        "pair_count": len(NSM_CROSSWALK_100),
        "samples": NSM_CROSSWALK_100,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _load_fixture(path: Path, *, expected_pairs: int | None = None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    samples = doc.get("samples") or []
    declared = doc.get("pair_count")
    if expected_pairs is not None and len(samples) != expected_pairs:
        raise ValueError(f"expected {expected_pairs} samples in {path}, got {len(samples)}")
    if declared is not None and len(samples) != int(declared):
        raise ValueError(f"fixture pair_count={declared} but samples={len(samples)} in {path}")
    if expected_pairs is None and not samples:
        raise ValueError(f"empty samples in {path}")
    return samples, doc


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--lexicon", type=Path, default=None)
    ap.add_argument("--candidate-lexicon", type=Path, default=None)
    ap.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    ap.add_argument(
        "--fixture-100",
        action="store_true",
        help="Use legacy 100-pair fixture (tests/fixtures/nsm_41k_lexicon_crosswalk_100_v1.json)",
    )
    ap.add_argument("--export-fixture", action="store_true")
    ap.add_argument("--export-500", action="store_true", help="Build 500-pair fixture via builder script")
    ap.add_argument("--expected-pairs", type=int, default=None)
    ap.add_argument("--min-prime-hit-rate", type=float, default=0.5)
    ap.add_argument("--max-distortion-rate", type=float, default=0.35)
    ap.add_argument("--max-negative-leaks", type=int, default=2)
    ap.add_argument(
        "--enforce-gates",
        action="store_true",
        help="Exit 1 when quality gates fail (default: audit-only exit 0)",
    )
    ap.add_argument(
        "--explication-sidecar",
        type=Path,
        default=None,
        help="DeepNSM shadow explication JSONL — remaps greek/hebrew probes via gematria lemma script",
    )
    ap.add_argument(
        "--orig-probes-only",
        action="store_true",
        help="Raw experiment: ignore English probe when greek/hebrew probes exist (distortion without EN shortcut)",
    )
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if args.fixture_100:
        fixture_path = DEFAULT_FIXTURE_100
    else:
        fixture_path = args.fixture if args.fixture.is_absolute() else ROOT / args.fixture

    if args.export_500:
        from scripts.build_nsm_41k_crosswalk_500_fixture_v1 import export_fixture as export_500  # noqa: E402

        export_500(fixture_path, target=args.expected_pairs or 500)
        print(
            json.dumps(
                {"ok": True, "exported": _rel(fixture_path), "pairs": args.expected_pairs or 500},
                ensure_ascii=False,
            )
        )
        return 0

    if args.export_fixture:
        export_fixture(fixture_path)
        print(json.dumps({"ok": True, "exported": _rel(fixture_path), "pairs": 100}, ensure_ascii=False))
        return 0

    if not fixture_path.is_file():
        if fixture_path.name.endswith("_500_v1.json"):
            from scripts.build_nsm_41k_crosswalk_500_fixture_v1 import export_fixture as export_500  # noqa: E402

            export_500(fixture_path, target=args.expected_pairs or 500)
        else:
            export_fixture(fixture_path)

    samples, fixture_doc = _load_fixture(fixture_path, expected_pairs=args.expected_pairs)
    baseline = args.lexicon
    if baseline is None or not baseline.is_file():
        baseline = resolve_latest_codebook_path()
    if baseline is None or not baseline.is_file():
        print("ABORT: baseline lexicon not found")
        return 1

    sidecar_path = None
    sidecar_index: dict[str, dict[str, Any]] | None = None
    if args.explication_sidecar:
        sidecar_path = (
            args.explication_sidecar
            if args.explication_sidecar.is_absolute()
            else ROOT / args.explication_sidecar
        )
        if not sidecar_path.is_file():
            print(f"ABORT: explication sidecar missing: {sidecar_path}")
            return 1
        sidecar_index = load_explication_sidecar(sidecar_path)

    baseline_audit = audit_lexicon(
        baseline,
        samples,
        sidecar=sidecar_index,
        orig_probes_only=args.orig_probes_only,
    )
    candidate_audit = None
    if args.candidate_lexicon:
        cand = args.candidate_lexicon if args.candidate_lexicon.is_absolute() else ROOT / args.candidate_lexicon
        if cand.is_file():
            candidate_audit = audit_lexicon(
                cand,
                samples,
                sidecar=sidecar_index,
                orig_probes_only=args.orig_probes_only,
            )

    gate_ok = (
        baseline_audit["prime_hit_rate"] >= args.min_prime_hit_rate
        and baseline_audit["english_only_distortion_rate"] <= args.max_distortion_rate
        and baseline_audit["negative_control_leak_count"] <= args.max_negative_leaks
    )

    out_doc = {
        "schema": "nsm_41k_lexicon_crosswalk_audit_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "fixture": _rel(fixture_path),
        "fixture_schema": fixture_doc.get("schema"),
        "fixture_pair_count": len(samples),
        "explication_sidecar": _rel(sidecar_path) if sidecar_path else None,
        "explication_sidecar_records": len(sidecar_index or {}),
        "audit_mode": (
            "deepnsm_shadow"
            if sidecar_index
            else ("orig_probes_only" if args.orig_probes_only else "raw_latin")
        ),
        "orig_probes_only": bool(args.orig_probes_only),
        "gates": {
            "min_prime_hit_rate": args.min_prime_hit_rate,
            "max_distortion_rate": args.max_distortion_rate,
            "max_negative_leaks": args.max_negative_leaks,
            "gate_ok": gate_ok,
        },
        "baseline": baseline_audit,
        "candidate": candidate_audit,
        "comparison": None,
        "reproduce": f"py scripts/run_nsm_41k_lexicon_crosswalk_audit_v1.py --fixture {_rel(fixture_path)}",
    }
    if candidate_audit:
        out_doc["comparison"] = {
            "prime_hit_rate_delta": round(
                candidate_audit["prime_hit_rate"] - baseline_audit["prime_hit_rate"], 4
            ),
            "distortion_rate_delta": round(
                candidate_audit["english_only_distortion_rate"]
                - baseline_audit["english_only_distortion_rate"],
                4,
            ),
        }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "gate_ok": gate_ok,
                "out": _rel(args.out),
                "prime_hit_rate": baseline_audit["prime_hit_rate"],
                "distortion_rate": baseline_audit["english_only_distortion_rate"],
                "aligned_original": baseline_audit["aligned_original_language_count"],
                "gaps": baseline_audit["gap_count"],
                "research_verdict": "high_distortion_expected_nsm_vs_corpus_lexicon"
                if baseline_audit["english_only_distortion_rate"] > 0.5
                else "moderate_crosswalk",
            },
            ensure_ascii=False,
        )
    )
    if args.enforce_gates and not gate_ok:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
