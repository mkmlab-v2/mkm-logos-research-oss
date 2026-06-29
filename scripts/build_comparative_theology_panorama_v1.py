#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build curated comparative-theology panorama — all school readings imagination_path / unknown_gap."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SEED = ROOT / "docs/final/artifacts/comparative_theology_seeds/job_1_6_satan_v1.json"
DEFAULT_SCHEMA = ROOT / "docs/final/schemas/comparative_theology_panorama_v1.schema.json"
DEFAULT_CROSS_REF = ROOT / "docs/final/artifacts/CROSS_REF_DSS_TO_STATES_DRAFT.json"
DEFAULT_OUT_ART = ROOT / "docs/final/artifacts/comparative_theology_panorama_v1_latest.json"
RESOLVER = ROOT / "scripts/resolve_logos_verse_reference_v1.py"

SCHEMA_VERSION = "comparative_theology_panorama_v1"
POLICY_ID = "comparative_theology_rail_v1"
GENERATOR = "build_comparative_theology_panorama_v1.py@1.0.0"

DISCLAIMER = {
    "evidence_tier": "hypo_research_only",
    "gating_status": "NON_GATING",
    "note_ko": (
        "학파별 해석 파노라마 — 전 레인 [HYPO]/NON_GATING. "
        "본문 스니펫만 corpus_bound; 학파 reading은 imagination_path 또는 unknown_gap. "
        "가중치=정렬용, 진리 점수 아님. Track A·실매매·Integrity Orb verified_anchor와 무관."
    ),
}

ALLOWED_SCHOOL_CLASSES = frozenset({"imagination_path", "unknown_gap"})


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _validate(doc: dict[str, Any], schema_path: Path) -> None:
    jsonschema = __import__("jsonschema")
    jsonschema.Draft7Validator(_load(schema_path)).validate(doc)


def _fetch_corpus_row(ref: str) -> dict[str, Any]:
    proc = subprocess.run(
        [sys.executable, str(RESOLVER), "--text", ref, "--fetch-row"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return {"verse_id": ref, "found": False, "error": proc.stderr.strip()[:200]}
    try:
        doc = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"verse_id": ref, "found": False, "error": "invalid_resolver_json"}
    rows = doc.get("corpus_rows") or []
    if not rows:
        return {"verse_id": ref, "found": False}
    row = rows[0]
    if not row.get("found"):
        return {"verse_id": ref, "found": False}
    inner = row.get("row") or {}
    text = str(inner.get("text") or inner.get("original_text") or "")[:400]
    return {
        "verse_id": ref,
        "found": True,
        "utterance_class": "corpus_bound",
        "source_ref": inner.get("source_ref"),
        "edition": inner.get("edition"),
        "text_snippet": text,
        "decode_status": inner.get("decode_status"),
        "must_not_present_as_fact": False,
    }


def _cross_ref_has_job(cross_ref: dict[str, Any]) -> bool:
    rows = cross_ref.get("rows") or cross_ref.get("entries") or []
    for row in rows:
        blob = json.dumps(row, ensure_ascii=False)
        if "Job" in blob or "욥" in blob:
            return True
    return False


def _comparator_transform(school: dict[str, Any]) -> dict[str, Any]:
    tags = school.get("metaphor_transform_tags") or []
    weight = float(school.get("display_rank_weight") or 0.5)
    transforms = [
        {
            "tag": tag,
            "transform_weight_0_1": round(min(1.0, weight * (0.85 + 0.05 * i)), 3),
            "note_ko": "Metaphor DB 태그 라벨만 — 자동 신학 추론 아님.",
        }
        for i, tag in enumerate(tags)
    ]
    return {
        "school_id": school.get("school_id"),
        "display_rank_weight": weight,
        "transforms": transforms,
        "rank_is_not_truth_score": True,
    }


def _enforce_budget(school_lanes: list[dict[str, Any]]) -> dict[str, Any]:
    imagination = [s for s in school_lanes if s["utterance_class"] == "imagination_path"]
    gaps = [s for s in school_lanes if s["utterance_class"] == "unknown_gap"]
    total_budget = sum(float(s.get("imagination_budget_0_1") or 0) for s in school_lanes)
    top = max(school_lanes, key=lambda s: float(s.get("display_rank_weight") or 0))
    top_w = float(top.get("display_rank_weight") or 0)
    parallel_ok = len(imagination) >= 2
    bias_detected = top_w >= 0.85 and len(imagination) < 2
    enforcement = "ok"
    messages: list[str] = []
    if len(school_lanes) < 2:
        enforcement = "parallel_required"
        messages.append("school_count < 2 — 병렬 학파 배치 필요.")
    elif not parallel_ok:
        enforcement = "parallel_required"
        messages.append("imagination_path 학파 2개 미만 — 병렬 배치 권고.")
    if bias_detected:
        enforcement = "bias_parallel_injected" if parallel_ok else "bias_detected"
        messages.append(
            f"편향 가중치 감지({top.get('school_id')}={top_w}) — 다른 학파 병렬 표시 유지."
        )
    if total_budget > 3.5:
        messages.append("imagination_budget 합계 높음 — 신규 생성 금지, 큐레이션만.")

    return {
        "status": enforcement,
        "school_count": len(school_lanes),
        "imagination_path_count": len(imagination),
        "unknown_gap_count": len(gaps),
        "total_imagination_budget": round(total_budget, 2),
        "parallel_required": not parallel_ok,
        "bias_detected": bias_detected,
        "messages_ko": messages,
        "gate_ko": (
            "현재 답변에 편향된 상상력이 개입되었습니다. 다른 학파 경로를 병렬로 배치합니다."
            if bias_detected and parallel_ok
            else ""
        ),
    }


def build(
    *,
    seed: dict[str, Any],
    cross_ref: dict[str, Any],
) -> dict[str, Any]:
    anchor_ref = str(seed.get("anchor_ref") or "Job.1.6")
    anchor_corpus = _fetch_corpus_row(anchor_ref)
    cross_job = _cross_ref_has_job(cross_ref)

    school_lanes: list[dict[str, Any]] = []
    for raw in seed.get("school_lanes") or []:
        uclass = str(raw.get("utterance_class") or "imagination_path")
        if uclass not in ALLOWED_SCHOOL_CLASSES:
            uclass = "imagination_path"
        if raw.get("school_id") == "dss_qumran_parallels" and not cross_job:
            uclass = "unknown_gap"

        budget = 0.85 if uclass == "imagination_path" else 0.5
        school_lanes.append(
            {
                "school_id": raw.get("school_id"),
                "label_ko": raw.get("label_ko"),
                "label_en": raw.get("label_en"),
                "reading_ko": raw.get("reading_ko"),
                "source_tier": raw.get("source_tier"),
                "utterance_class": uclass,
                "imagination_budget_0_1": budget,
                "display_rank_weight": raw.get("display_rank_weight"),
                "display_label_ko": {
                    "imagination_path": "상상력 경로 [HYPO]",
                    "unknown_gap": "구조적 무지·갭",
                }[uclass],
                "must_not_present_as_fact": True,
                "human_adoption_required": True,
                "literature_pointers": raw.get("literature_pointers") or [],
                "metaphor_transform_tags": raw.get("metaphor_transform_tags") or [],
                "dss_cross_ref_job_in_repo": cross_job,
            }
        )

    comparator = {
        "schema": "comparator_v1",
        "anchor_ref": anchor_ref,
        "school_transforms": [_comparator_transform(s) for s in seed.get("school_lanes") or []],
        "notes_ko": seed.get("comparator_notes_ko"),
    }

    enforcement = _enforce_budget(school_lanes)

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": _utc_now(),
        "generator": GENERATOR,
        "policy_id": POLICY_ID,
        "issue_id": seed.get("issue_id"),
        "query_ko": seed.get("query_ko"),
        "disclaimer": DISCLAIMER,
        "anchor_ref": anchor_ref,
        "secondary_refs": seed.get("secondary_refs") or [],
        "anchor_corpus": anchor_corpus,
        "school_lanes": school_lanes,
        "comparator": comparator,
        "imagination_budget_enforcement": enforcement,
        "fact_lock": {
            "track": "B",
            "send_gate": "HOLD",
            "verified_anchor": False,
            "no_track_a_bridge": True,
            "all_school_readings_non_fact": True,
        },
        "reproduce": {
            "command": "py scripts/build_comparative_theology_panorama_v1.py",
            "seed_path": str(DEFAULT_SEED.relative_to(ROOT)).replace("\\", "/"),
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Build comparative theology panorama v1.")
    ap.add_argument("--seed-json", type=Path, default=DEFAULT_SEED)
    ap.add_argument("--cross-ref-json", type=Path, default=DEFAULT_CROSS_REF)
    ap.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    ap.add_argument("--out-artifact", type=Path, default=DEFAULT_OUT_ART)
    ap.add_argument("--skip-validate", action="store_true")
    args = ap.parse_args()

    def _p(p: Path) -> Path:
        return p if p.is_absolute() else ROOT / p

    seed = _load(_p(args.seed_json))
    cross_ref = _load(_p(args.cross_ref_json)) if _p(args.cross_ref_json).is_file() else {}
    doc = build(seed=seed, cross_ref=cross_ref)
    out = _p(args.out_artifact)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    if not args.skip_validate:
        _validate(doc, _p(args.schema))
    print(
        json.dumps(
            {
                "ok": True,
                "out": str(out),
                "school_count": len(doc["school_lanes"]),
                "enforcement": doc["imagination_budget_enforcement"]["status"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
