#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Job prologue symbolic energy + lemma hub slice [HYPO][NON_GATING] — high-dim shadow lane."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RESOLVER = ROOT / "scripts/resolve_logos_verse_reference_v1.py"
ANCHOR_INDEX = ROOT / "reports/logos_bidirectional_anchor_index_v1_latest.json"
DEFAULT_SCHEMA = ROOT / "docs/final/schemas/job_prologue_symbolic_energy_v1.schema.json"
DEFAULT_OUT_ART = ROOT / "docs/final/artifacts/job_prologue_symbolic_energy_v1_latest.json"
DEFAULT_OUT_PUBLIC = (
    ROOT
    / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp"
    / "job_prologue_symbolic_energy_v1.json"
)

SCHEMA_VERSION = "job_prologue_symbolic_energy_v1"
GENERATOR = "build_job_prologue_symbolic_energy_slice_v1.py@1.0.0"

NARRATIVE_ORDER: list[dict[str, str]] = [
    {"ref": "Job.1.6", "scene": "heavenly_council", "speaker": "narrator", "act_ko": "하늘 회의 장면"},
    {"ref": "Job.1.8", "scene": "heavenly_council", "speaker": "divine", "act_ko": "무죄 선포"},
    {"ref": "Job.1.12", "scene": "first_permit", "speaker": "divine", "act_ko": "1차 허용(몸 제외)"},
    {"ref": "Job.1.21", "scene": "job_response_1", "speaker": "job", "act_ko": "욥 1차 응답"},
    {"ref": "Job.2.3", "scene": "second_dialogue", "speaker": "divine", "act_ko": "2차 대화·חנם"},
    {"ref": "Job.2.6", "scene": "life_bound", "speaker": "divine", "act_ko": "생명만 지켜라"},
    {"ref": "Job.2.10", "scene": "job_response_2", "speaker": "job", "act_ko": "선악 받되 입술 무죄"},
]

LEMMA_HUBS = ("שטן", "חנם", "יהוה", "תם")

DISCLAIMER = {
    "evidence_tier": "hypo_research_only",
    "gating_status": "NON_GATING",
    "note_ko": (
        "게마트리아·4D·아톰 허브는 corpus-bound 관측입니다. [HYPO] 인과·교리·물리 증명이 아닙니다. "
        "physical_constants_match는 신학 승격 금지."
    ),
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _validate(doc: dict[str, Any], schema_path: Path) -> None:
    jsonschema = __import__("jsonschema")
    jsonschema.Draft7Validator(_load(schema_path)).validate(doc)


def _fetch_row(ref: str) -> dict[str, Any]:
    proc = subprocess.run(
        [sys.executable, str(RESOLVER), "--text", ref, "--fetch-row"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return {"verse_id": ref, "found": False}
    try:
        doc = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"verse_id": ref, "found": False}
    row_wrap = (doc.get("corpus_rows") or [{}])[0]
    if not row_wrap.get("found"):
        return {"verse_id": ref, "found": False}
    row = row_wrap.get("row") or {}
    v4 = row.get("vector_4d") or row.get("unified_4d_vector") or {}
    return {
        "verse_id": ref,
        "found": True,
        "hebrew_value": row.get("hebrew_value"),
        "total_value": row.get("total_value"),
        "normalized_value": row.get("normalized_value"),
        "vector_4d": v4,
        "phase_phi": row.get("phase_phi"),
        "distance_to_centroid": row.get("distance_to_centroid"),
        "text_snippet": (row.get("text") or "")[:160],
        "interpretation": row.get("interpretation"),
        "physical_constants_match_max": max((row.get("physical_constants_match") or {}).values() or [0]),
    }


def _lemma_hubs(index: dict[str, Any]) -> list[dict[str, Any]]:
    a2v = index.get("atom_to_verses") or {}
    hubs: list[dict[str, Any]] = []
    for lemma in LEMMA_HUBS:
        atom_id = f"hebrew::{lemma}"
        vers = a2v.get(atom_id) or []
        job_ids: list[str] = []
        other_ids: list[str] = []
        for v in vers:
            vid = v.get("verse_id") if isinstance(v, dict) else str(v)
            w = float(v.get("weight", 0)) if isinstance(v, dict) else 0.0
            if not vid:
                continue
            if vid.startswith("Job."):
                job_ids.append(vid)
            elif len(other_ids) < 12:
                other_ids.append(vid)
        hubs.append(
            {
                "lemma": lemma,
                "atom_id": atom_id,
                "job_verse_count": len(job_ids),
                "job_verse_sample": sorted(set(job_ids))[:12],
                "cross_corpus_sample": other_ids[:8],
                "hub_role_ko": {
                    "שטן": "법정·고발·시험 lemma hub",
                    "חנם": "무고/헛되이 논쟁 축",
                    "יהוה": "선포층 신명",
                    "תם": "순전 프레임(희소)",
                }.get(lemma, "symbolic hub"),
            }
        )
    return hubs


def _avg_4d(rows: list[dict[str, Any]], key: str) -> float:
    vals = [
        float((r.get("vector_4d") or {}).get(key, 0))
        for r in rows
        if r.get("found")
    ]
    return round(sum(vals) / len(vals), 4) if vals else 0.0


def build(index_path: Path) -> dict[str, Any]:
    index = _load(index_path) if index_path.is_file() else {}
    curve: list[dict[str, Any]] = []
    by_ref: dict[str, dict[str, Any]] = {}
    for item in NARRATIVE_ORDER:
        ref = item["ref"]
        row = _fetch_row(ref)
        by_ref[ref] = row
        curve.append({**item, **row})

    divine_rows = [by_ref[r["ref"]] for r in NARRATIVE_ORDER if r["speaker"] == "divine"]
    job_rows = [by_ref[r["ref"]] for r in NARRATIVE_ORDER if r["speaker"] == "job"]

    speaker_split = {
        "divine": {
            "refs": [r["ref"] for r in NARRATIVE_ORDER if r["speaker"] == "divine"],
            "avg_K": _avg_4d(divine_rows, "K"),
            "avg_M": _avg_4d(divine_rows, "M"),
            "avg_S": _avg_4d(divine_rows, "S"),
            "avg_L": _avg_4d(divine_rows, "L"),
        },
        "job": {
            "refs": [r["ref"] for r in NARRATIVE_ORDER if r["speaker"] == "job"],
            "avg_K": _avg_4d(job_rows, "K"),
            "avg_M": _avg_4d(job_rows, "M"),
            "avg_S": _avg_4d(job_rows, "S"),
            "avg_L": _avg_4d(job_rows, "L"),
        },
        "observation_ko": (
            "화자층 4D 분리: 욥 응답층 K 상대↑·M 상대↓ — [HYPO] 구조 서명이며 인과 단정 아님."
        ),
    }

    hv_23 = float(by_ref.get("Job.2.3", {}).get("hebrew_value") or 0)
    hv_26 = float(by_ref.get("Job.2.6", {}).get("hebrew_value") or 0)
    norm_23 = float(by_ref.get("Job.2.3", {}).get("normalized_value") or 0)

    hubs = _lemma_hubs(index)
    satan_hub = next((h for h in hubs if h["lemma"] == "שטן"), {})

    high_dim: list[dict[str, Any]] = [
        {
            "hypothesis_id": "H_SYM_SATAN_HUB",
            "label_ko": "שטן lemma hub — 욥 서곡 밀집 + Zech/1Chr 교차망",
            "status": "path_only_not_verdict",
            "tier": "symbolic_network",
            "metrics": {
                "job_verse_count": satan_hub.get("job_verse_count"),
                "cross_corpus_sample": satan_hub.get("cross_corpus_sample"),
            },
            "prompt_ko": "법정·incite·시험 역할을 corpus 망으로 분리 검토. 채택은 지휘관.",
        },
        {
            "hypothesis_id": "H_ENERGY_SPIKE_2_3",
            "label_ko": "게마트리아 특이점 Job.2.3 → 허용 상한 급락 Job.2.6",
            "status": "path_only_not_verdict",
            "tier": "gematria_energy",
            "metrics": {
                "Job.2.3_hebrew_value": hv_23,
                "Job.2.3_normalized_value": norm_23,
                "Job.2.6_hebrew_value": hv_26,
                "delta_2_3_to_2_6": round(hv_26 - hv_23, 1),
                "physical_constants_match_max_2_3": by_ref.get("Job.2.3", {}).get(
                    "physical_constants_match_max"
                ),
            },
            "prompt_ko": "에너지 곡선은 구조 관측. 「왜」의 답이 아님.",
        },
        {
            "hypothesis_id": "H_KM_SPEAKER_SPLIT",
            "label_ko": "4D K/M 화자층 분리 (divine vs job)",
            "status": "path_only_not_verdict",
            "tier": "vector_4d_shadow",
            "metrics": {
                "divine_avg_K": speaker_split["divine"]["avg_K"],
                "divine_avg_M": speaker_split["divine"]["avg_M"],
                "job_avg_K": speaker_split["job"]["avg_K"],
                "job_avg_M": speaker_split["job"]["avg_M"],
                "delta_K_job_minus_divine": round(
                    speaker_split["job"]["avg_K"] - speaker_split["divine"]["avg_K"], 4
                ),
                "delta_M_job_minus_divine": round(
                    speaker_split["job"]["avg_M"] - speaker_split["divine"]["avg_M"], 4
                ),
            },
            "prompt_ko": "운영 은유·렌즈 입력용. Track A 승격 금지.",
        },
        {
            "hypothesis_id": "H_CHINAM_LEXICAL",
            "label_ko": "חנם(헛되이) 어휘 축 — 무고 시험 논점",
            "status": "path_only_not_verdict",
            "tier": "lemma_network",
            "metrics": {
                "anchor_ref": "Job.2.3",
                "snippet_contains_chinam": "חנם" in (by_ref.get("Job.2.3", {}).get("text_snippet") or ""),
            },
            "prompt_ko": "어휘 네트워크 경로. 신학 단정 아님.",
        },
    ]

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": _utc_now(),
        "generator": GENERATOR,
        "issue_id": "job_prologue_suffering",
        "query_ko": "욥이 고난을 받은 이유",
        "disclaimer": DISCLAIMER,
        "energy_curve": curve,
        "speaker_4d_split": speaker_split,
        "lemma_hubs": hubs,
        "high_dim_hypotheses": high_dim,
        "reproduce": {
            "command": f"py {RESOLVER.relative_to(ROOT).as_posix()} --text Job.2.3 --fetch-row",
            "anchor_index": str(ANCHOR_INDEX.relative_to(ROOT)).replace("\\", "/"),
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Build Job prologue symbolic energy slice v1.")
    ap.add_argument("--anchor-index", type=Path, default=ANCHOR_INDEX)
    ap.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    ap.add_argument("--out-artifact", type=Path, default=DEFAULT_OUT_ART)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT_PUBLIC)
    ap.add_argument("--skip-validate", action="store_true")
    args = ap.parse_args()

    doc = build(args.anchor_index if args.anchor_index.is_absolute() else ROOT / args.anchor_index)
    out_art = args.out_artifact if args.out_artifact.is_absolute() else ROOT / args.out_artifact
    out_json = args.out_json if args.out_json.is_absolute() else ROOT / args.out_json
    payload = json.dumps(doc, ensure_ascii=False, indent=2)
    out_art.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_art.write_text(payload, encoding="utf-8")
    out_json.write_text(payload, encoding="utf-8")
    if not args.skip_validate:
        schema = args.schema if args.schema.is_absolute() else ROOT / args.schema
        _validate(doc, schema)
    print(json.dumps({"ok": True, "out": str(out_art), "hypotheses": len(doc["high_dim_hypotheses"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
