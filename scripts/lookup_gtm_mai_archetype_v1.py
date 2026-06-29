"""
Deterministic MAI (GTM wrapper) lookup — consumer lane only.

Input: observation_proxies (+ optional myeongri_bucket). Output: mai_code + public copy stub.
[HYPO] lookup table in gtm_personality_wrapper_draft_v1.json — not validated for marketing accuracy.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

DRAFT_REL = Path("docs/final/artifacts/gtm_personality_wrapper_draft_v1.json")
COPY_REL = Path("docs/final/artifacts/gtm_mai_copy_bundles_v1.json")
PROXY_KEYS = ("cold_heat_lean", "digestion_lean", "activity_lean", "moisture_lean")


def _workspace_root() -> Path:
    return Path(__file__).resolve().parent.parent


def load_draft(root: Path | None = None) -> dict[str, Any]:
    path = (root or _workspace_root()) / DRAFT_REL
    return json.loads(path.read_text(encoding="utf-8"))


def load_copy_bundles(root: Path | None = None) -> dict[str, Any]:
    path = (root or _workspace_root()) / COPY_REL
    return json.loads(path.read_text(encoding="utf-8"))


def _quartile(lean: float) -> int:
    if lean < 0.25:
        return 0
    if lean < 0.5:
        return 1
    if lean < 0.75:
        return 2
    return 3


def survey_bucket_from_proxies(proxies: dict[str, float]) -> str:
    parts = []
    labels = ("H", "D", "A", "M")
    for key, label in zip(PROXY_KEYS, labels):
        parts.append(f"{label}{_quartile(float(proxies.get(key, 0.5)))}")
    return "".join(parts)


def lookup_mai_code(
    draft: dict[str, Any],
    *,
    survey_bucket: str,
    myeongri_bucket: str = "E*",
) -> tuple[str, str]:
    table = draft.get("mai_archetype_lookup_v1") or {}
    mappings = table.get("sample_mappings_hypo") or []
    for row in mappings:
        if not isinstance(row, dict):
            continue
        if row.get("survey_bucket") == survey_bucket and (
            row.get("myeongri_bucket") == myeongri_bucket
            or row.get("myeongri_bucket") == "E*"
        ):
            return str(row["mai_code"]), "sample_mapping"
    archetypes = table.get("archetypes") or []
    if not archetypes:
        return "MAI-00", "fallback_empty"
    idx = hash(survey_bucket) % len(archetypes)
    code = str(archetypes[idx].get("mai_code", "MAI-00"))
    return code, "hash_fallback"


def resolve_archetype(draft: dict[str, Any], mai_code: str) -> dict[str, Any] | None:
    archetypes = (draft.get("mai_archetype_lookup_v1") or {}).get("archetypes") or []
    for a in archetypes:
        if isinstance(a, dict) and a.get("mai_code") == mai_code:
            return a
    return None


def resolve_copy_bundle(copy_doc: dict[str, Any], mai_code: str) -> dict[str, Any] | None:
    bundles = copy_doc.get("bundles") or {}
    row = bundles.get(mai_code)
    return row if isinstance(row, dict) else None


def build_mai_public_card(
    proxies: dict[str, float],
    *,
    myeongri_bucket: str = "E*",
    root: Path | None = None,
) -> dict[str, Any]:
    """Consumer-facing MAI envelope (no sasang / birth / raw survey)."""
    root = root or _workspace_root()
    draft = load_draft(root)
    copy_doc = load_copy_bundles(root)
    bucket = survey_bucket_from_proxies(proxies)
    mai_code, method = lookup_mai_code(
        draft, survey_bucket=bucket, myeongri_bucket=myeongri_bucket
    )
    archetype = resolve_archetype(draft, mai_code) or {}
    bundle = resolve_copy_bundle(copy_doc, mai_code) or {}
    disclaimer = str(
        bundle.get("disclaimer_ko")
        or copy_doc.get("disclaimer_ko")
        or draft.get("marketing_posture", {}).get("trademark", "")
    )
    return {
        "schema": "gtm_mai_public_card_v1",
        "hypothesis_tier": "B",
        "research_only": True,
        "mai_code": mai_code,
        "lookup_method": method,
        "survey_bucket_internal": bucket,
        "title_ko": bundle.get("title_ko") or archetype.get("title_ko"),
        "one_liner_ko": bundle.get("one_liner_ko"),
        "strengths_ko": bundle.get("strengths_ko") or [],
        "stress_pattern_ko": bundle.get("stress_pattern_ko"),
        "share_slug": bundle.get("share_slug") or archetype.get("share_slug"),
        "tone": archetype.get("tone"),
        "disclaimer_ko": disclaimer,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="MAI GTM wrapper lookup v1")
    p.add_argument("--proxies-json", type=str, required=True, help="JSON observation_proxies object")
    p.add_argument("--myeongri-bucket", type=str, default="E*")
    args = p.parse_args(argv)
    proxies = json.loads(args.proxies_json)
    card = build_mai_public_card(
        proxies, myeongri_bucket=args.myeongri_bucket, root=_workspace_root()
    )
    out = {
        "schema": "gtm_mai_lookup_result_v1",
        "hypothesis_tier": "B",
        "research_only": True,
        "myeongri_bucket": args.myeongri_bucket,
        "public_card": card,
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
