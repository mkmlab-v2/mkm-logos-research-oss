# -*- coding: utf-8 -*-
"""Build standardized Myeongri answer draft from template pack + recommendation + deterministic JSON."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEMPLATE_PACK = ROOT / "docs" / "final" / "artifacts" / "myeongri_answer_template_pack_latest.json"
DEFAULT_RECOMMENDATION = ROOT / "docs" / "final" / "artifacts" / "myeongri_external_reference_recommendation_latest.json"
DEFAULT_DETERMINISTIC = ROOT / "docs" / "final" / "artifacts" / "myeongni_independent_lens_from_chain_latest.json"
DEFAULT_JSON_OUT = ROOT / "docs" / "final" / "artifacts" / "myeongri_answer_draft_latest.json"
DEFAULT_MD_OUT = ROOT / "docs" / "final" / "artifacts" / "myeongri_answer_draft_latest.md"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _pick_template(pack: dict[str, Any], profile: str, lang: str) -> str:
    for t in pack.get("templates", []):
        if t.get("profile") == profile and t.get("lang") == lang:
            return str(t.get("template", ""))
    # fallback
    for t in pack.get("templates", []):
        if t.get("profile") == "general" and t.get("lang") == lang:
            return str(t.get("template", ""))
    raise ValueError(f"No template found for profile={profile} lang={lang}")


def _format_summary(det: dict[str, Any]) -> str:
    keys = ["birth_instant_utc", "iana_tz", "as_of_utc", "state_id", "active_daewoon"]
    pairs = []
    for k in keys:
        if k in det:
            pairs.append(f"{k}={det.get(k)}")
    return ", ".join(pairs) if pairs else "not_provided"


def _format_deterministic_fields(det: dict[str, Any]) -> str:
    wanted = [
        "state_id",
        "active_daewoon",
        "vector_4d_rule_school_v1",
        "myeongni_core_vector_v1",
        "myeongni_independent_lens_v1",
    ]
    found = [k for k in wanted if k in det]
    if not found:
        found = list(det.keys())[:5]
    return ", ".join(found) if found else "none"


def _hypothesis_block(profile: str, rec: dict[str, Any]) -> str:
    recs = rec.get("recommendations") or []
    if not recs:
        return f"[HYPO] profile={profile}: external references unavailable, keep deterministic-only narrative."
    top = recs[0]
    return (
        f"[HYPO] profile={profile}: deterministic anchor + external context "
        f"({top.get('title', 'unknown')}) with conservative boundary."
    )


def build_draft_payload(
    *,
    profile: str,
    lang: str,
    template_text: str,
    deterministic: dict[str, Any],
    recommendation: dict[str, Any],
    artifact_paths: list[str],
) -> dict[str, Any]:
    body = template_text.format(
        input_summary=_format_summary(deterministic),
        artifact_paths=", ".join(artifact_paths),
        deterministic_fields=_format_deterministic_fields(deterministic),
        profile=profile,
        hypothesis_block=_hypothesis_block(profile, recommendation),
    )
    return {
        "schema": "myeongri_answer_draft_v1",
        "version": "1.0.0",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "profile": profile,
        "lang": lang,
        "artifact_paths": artifact_paths,
        "rag_sources_used_suggested": recommendation.get("rag_sources_used_suggested", []),
        "draft_text": body,
        "boundary_note": "Draft only. Final response requires human review and envelope validation.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--profile", default="daewoon")
    ap.add_argument("--lang", default="ko", choices=("ko", "en"))
    ap.add_argument("--template-pack", type=Path, default=DEFAULT_TEMPLATE_PACK)
    ap.add_argument("--recommendation", type=Path, default=DEFAULT_RECOMMENDATION)
    ap.add_argument("--deterministic-json", type=Path, default=DEFAULT_DETERMINISTIC)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_JSON_OUT)
    ap.add_argument("--out-md", type=Path, default=DEFAULT_MD_OUT)
    args = ap.parse_args()

    pack = _load_json(args.template_pack)
    rec = _load_json(args.recommendation)
    det = _load_json(args.deterministic_json) if args.deterministic_json.exists() else {"missing_input": True}
    template_text = _pick_template(pack, args.profile, args.lang)

    artifact_paths = [
        str(args.template_pack.as_posix()),
        str(args.recommendation.as_posix()),
        str(args.deterministic_json.as_posix()),
    ]
    payload = build_draft_payload(
        profile=args.profile,
        lang=args.lang,
        template_text=template_text,
        deterministic=det,
        recommendation=rec,
        artifact_paths=artifact_paths,
    )

    args.out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.out_md.write_text(payload["draft_text"] + "\n", encoding="utf-8")
    print(f"draft_json_written={args.out_json}")
    print(f"draft_md_written={args.out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
