"""
Resolve a single clinical patient to SSOT pointer paths before chat answers.

Machine gate: exit 0 = one patient; 1 = not found; 2 = ambiguous (do not answer).

Usage:
  py scripts/resolve_patient_clinical_ssot_v1.py --display "김아름"
  py scripts/resolve_patient_clinical_ssot_v1.py --slug kim_areum
  py scripts/resolve_patient_clinical_ssot_v1.py --ref-token KIM-AREUM-2026-001
  py scripts/resolve_patient_clinical_ssot_v1.py --risk-keywords "산후,단삼,소염"
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_REL = Path("docs/final/artifacts/patient_encounter_registry_v1_latest.json")
DISAMBIG_REL = Path("docs/final/artifacts/patient_disambiguation_guard_v1_latest.json")
POINTER_SUFFIX = "_intake_ssot_pointer_v1.json"

CLINICAL_KINDS = frozenset({"clinical_patient"})


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _clinical_encounters(registry: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for enc in registry.get("encounters") or []:
        if not isinstance(enc, dict):
            continue
        kind = str(enc.get("person_kind") or "")
        if kind in CLINICAL_KINDS:
            out.append(enc)
    return out


def _norm_label(s: str) -> str:
    return re.sub(r"\s+", "", s.strip())


def _match_display(encounters: list[dict[str, Any]], display: str) -> list[dict[str, Any]]:
    target = _norm_label(display)
    hits = [e for e in encounters if _norm_label(str(e.get("display_label") or "")) == target]
    return hits


def _match_slug(encounters: list[dict[str, Any]], slug: str) -> list[dict[str, Any]]:
    slug = slug.strip()
    return [e for e in encounters if e.get("slug") == slug]


def _match_ref_token(encounters: list[dict[str, Any]], ref_token: str) -> list[dict[str, Any]]:
    token = ref_token.strip().upper()
    return [e for e in encounters if str(e.get("ref_token") or "").upper() == token]


def _load_pointer(root: Path, pointer_rel: str) -> dict[str, Any]:
    path = root / pointer_rel.replace("\\", "/")
    if not path.is_file():
        return {}
    return _load_json(path)


def _track_b_memory_status(root: Path, pointer_doc: dict[str, Any]) -> dict[str, Any]:
    paths = pointer_doc.get("paths") or {}
    mem_rel = paths.get("patient_track_b_memory")
    if not isinstance(mem_rel, str):
        return {}
    mem_path = root / mem_rel.replace("\\", "/")
    if not mem_path.is_file():
        return {}
    doc = _load_json(mem_path)
    notes = doc.get("session_notes") or {}
    return {
        "path": mem_rel.replace("\\", "/"),
        "intake_status": notes.get("intake_status"),
        "saved_complete": str(notes.get("intake_status") or "").startswith("saved_"),
    }


def _risk_keyword_ambiguous(root: Path, keywords: list[str]) -> dict[str, Any] | None:
    guard_path = root / DISAMBIG_REL
    if not guard_path.is_file():
        return None
    guard = _load_json(guard_path)
    kw_join = ",".join(keywords).lower()
    for pair in guard.get("pairs") or []:
        if not isinstance(pair, dict):
            continue
        risk = str(pair.get("confusion_risk_ko") or "").lower()
        if not any(k.lower() in risk or k.lower() in kw_join for k in keywords):
            continue
        patients = pair.get("patients") or []
        if len(patients) >= 2:
            return {
                "pair_id": pair.get("pair_id"),
                "reason_ko": "유사 처방·증상 키워드만으로는 환자 특정 불가",
                "candidates": patients,
                "guard_path": DISAMBIG_REL.as_posix(),
            }
    return None


def _build_result(root: Path, enc: dict[str, Any]) -> dict[str, Any]:
    pointer_rel = str(enc.get("pointer") or "")
    pointer_doc = _load_pointer(root, pointer_rel) if pointer_rel else {}
    paths = pointer_doc.get("paths") if isinstance(pointer_doc.get("paths"), dict) else {}
    disambig = pointer_doc.get("disambiguation") if isinstance(pointer_doc.get("disambiguation"), dict) else {}
    mem = _track_b_memory_status(root, pointer_doc)
    return {
        "schema": "resolve_patient_clinical_ssot_result_v1",
        "resolved": True,
        "answer_gate": "allow",
        "slug": enc.get("slug"),
        "display_label": enc.get("display_label"),
        "ref_token": enc.get("ref_token"),
        "pointer": pointer_rel,
        "paths": paths,
        "disambiguation": disambig,
        "track_b_memory": mem,
        "cohort_tags": enc.get("cohort_tags") or [],
        "reply_header_ko": (
            f"[환자] {enc.get('display_label')} · {enc.get('ref_token')} · slug={enc.get('slug')}"
        ),
    }


def resolve(
    root: Path,
    *,
    display: str | None = None,
    slug: str | None = None,
    ref_token: str | None = None,
    risk_keywords: list[str] | None = None,
) -> tuple[int, dict[str, Any]]:
    registry_path = root / REGISTRY_REL
    if not registry_path.is_file():
        return 1, {
            "schema": "resolve_patient_clinical_ssot_result_v1",
            "resolved": False,
            "answer_gate": "deny_not_found",
            "error": f"missing registry: {REGISTRY_REL.as_posix()}",
        }

    registry = _load_json(registry_path)
    clinical = _clinical_encounters(registry)

    if risk_keywords and not (display or slug or ref_token):
        amb = _risk_keyword_ambiguous(root, risk_keywords)
        if amb:
            return 2, {
                "schema": "resolve_patient_clinical_ssot_result_v1",
                "resolved": False,
                "answer_gate": "deny_ambiguous",
                "error": amb["reason_ko"],
                "ambiguous": amb,
            }

    hits: list[dict[str, Any]] = []
    if slug:
        hits = _match_slug(clinical, slug)
    elif display:
        hits = _match_display(clinical, display)
    elif ref_token:
        hits = _match_ref_token(clinical, ref_token)

    if not hits:
        return 1, {
            "schema": "resolve_patient_clinical_ssot_result_v1",
            "resolved": False,
            "answer_gate": "deny_not_found",
            "error": "clinical patient not found in registry",
            "query": {"display": display, "slug": slug, "ref_token": ref_token},
        }
    if len(hits) > 1:
        return 2, {
            "schema": "resolve_patient_clinical_ssot_result_v1",
            "resolved": False,
            "answer_gate": "deny_ambiguous",
            "error": "multiple registry matches",
            "candidates": [
                {"slug": h.get("slug"), "display_label": h.get("display_label"), "ref_token": h.get("ref_token")}
                for h in hits
            ],
        }

    return 0, _build_result(root, hits[0])


def main() -> int:
    ap = argparse.ArgumentParser(description="Resolve clinical patient SSOT before agent answers.")
    ap.add_argument("--display", help="Patient display name (e.g. 김아름)")
    ap.add_argument("--slug", help="Patient slug (e.g. kim_areum)")
    ap.add_argument("--ref-token", help="Encounter ref token")
    ap.add_argument(
        "--risk-keywords",
        help="Comma-separated symptom/prescription keywords; without slug/display returns ambiguous if guard pair matches",
    )
    ap.add_argument("--compact", action="store_true", help="Minimal JSON stdout")
    args = ap.parse_args()

    if not any([args.display, args.slug, args.ref_token, args.risk_keywords]):
        print("error: provide --display, --slug, --ref-token, or --risk-keywords", file=sys.stderr)
        return 3

    keywords = None
    if args.risk_keywords:
        keywords = [k.strip() for k in args.risk_keywords.split(",") if k.strip()]

    code, result = resolve(
        _ROOT,
        display=args.display,
        slug=args.slug,
        ref_token=args.ref_token,
        risk_keywords=keywords,
    )

    if args.compact and code == 0:
        print(
            json.dumps(
                {
                    "answer_gate": result.get("answer_gate"),
                    "slug": result.get("slug"),
                    "ref_token": result.get("ref_token"),
                    "pointer": result.get("pointer"),
                },
                ensure_ascii=False,
            )
        )
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))

    return code


if __name__ == "__main__":
    raise SystemExit(main())
