#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tag generative slots as imagination_path vs corpus_bound — hallucination reframe rail v1."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCHEMA = ROOT / "docs/final/schemas/logos_imagination_rail_envelope_v1.schema.json"
DEFAULT_OUT_ART = ROOT / "docs/final/artifacts/logos_imagination_rail_envelope_v1_latest.json"
DEFAULT_ROUTER = ROOT / "reports/question_logos_subgraph_router_sidecar_v1_latest.json"
DEFAULT_SYMBOLIC = ROOT / "docs/final/artifacts/job_prologue_symbolic_energy_v1_latest.json"
DEFAULT_SHADOW = ROOT / "docs/final/artifacts/research_shadow_lane_hypothesis_tree_v1_latest.json"

SCHEMA_VERSION = "logos_imagination_rail_envelope_v1"
POLICY_ID = "imagination_rail_v1"
GENERATOR = "build_logos_imagination_rail_envelope_v1.py@1.0.0"

PROLOGUE_REFS = frozenset(
    {"Job.1.6", "Job.1.8", "Job.1.12", "Job.1.21", "Job.2.3", "Job.2.6", "Job.2.10"}
)

DISCLAIMER = {
    "evidence_tier": "hypo_research_only",
    "gating_status": "NON_GATING",
    "note_ko": (
        "환각을 ‘없앤다’고 주장하지 않습니다. 근거 없는 생성은 imagination_path로 격리·표시하며, "
        "corpus_bound·fact_locked와 혼동 금지. 상상력=채택 가능한 [HYPO] 경로이지 사실이 아닙니다."
    ),
}

UTTERANCE_CLASSES = {
    "fact_locked": "verified_anchor·ECC·exit0 artifact만 — 실매매·Track A 별도 게이트",
    "corpus_bound": "verse_id lookup·스니펫·게마트리아/4D가 corpus에 존재",
    "imagination_path": "생성·라우터·은유·[HYPO] 경로 — 인과·단정 금지, HITL 채택",
    "unknown_gap": "DSS/외경·미연결 위성 — literature pointer만",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _validate(doc: dict[str, Any], schema_path: Path) -> None:
    jsonschema = __import__("jsonschema")
    jsonschema.Draft7Validator(_load(schema_path)).validate(doc)


def _extract_refs(text: str) -> list[str]:
    return re.findall(r"\bJob\.\d+\.\d+\b", text)


def _classify_slot(
    *,
    slot_id: str,
    text: str,
    corpus_refs: list[str],
    verified_anchor: bool,
) -> dict[str, Any]:
    refs = list(dict.fromkeys(corpus_refs + _extract_refs(text)))
    prologue_hits = [r for r in refs if r in PROLOGUE_REFS]
    if verified_anchor and prologue_hits:
        uclass = "fact_locked"
        budget = 0.0
    elif prologue_hits or (refs and "corpus" in slot_id.lower()):
        uclass = "corpus_bound"
        budget = max(0.0, 0.35 - 0.05 * len(refs))
    elif refs:
        uclass = "corpus_bound"
        budget = 0.25
    elif "gap" in slot_id.lower() or "dss" in text.lower() or "4Q" in text:
        uclass = "unknown_gap"
        budget = 0.5
    else:
        uclass = "imagination_path"
        budget = 0.85

    return {
        "slot_id": slot_id,
        "utterance_class": uclass,
        "imagination_budget_0_1": round(budget, 2),
        "corpus_refs": refs,
        "prologue_causality_refs": prologue_hits,
        "must_not_present_as_fact": uclass in ("imagination_path", "unknown_gap"),
        "human_adoption_required": uclass != "fact_locked",
        "display_label_ko": {
            "fact_locked": "사실 잠금",
            "corpus_bound": "본문 결박",
            "imagination_path": "상상력 경로 [HYPO]",
            "unknown_gap": "구조적 무지·갭",
        }[uclass],
        "text_preview": (text or "")[:240],
    }


def build(
    *,
    router: dict[str, Any],
    symbolic: dict[str, Any],
    shadow: dict[str, Any],
) -> dict[str, Any]:
    verified = bool((shadow.get("rail_status") or {}).get("verified_anchor_achieved"))
    slots: list[dict[str, Any]] = []

    bp = shadow.get("boundary_proof") or {}
    slots.append(
        _classify_slot(
            slot_id="boundary.router_verdict",
            text=str(bp.get("router_verdict", "")),
            corpus_refs=list(bp.get("router_verse_ids_sample") or []),
            verified_anchor=verified,
        )
    )

    for i, ev in enumerate((router.get("paths") or [])[:6]):
        note = str(ev.get("note_ko") or "")
        steps = " ".join(str(s) for s in (ev.get("steps") or []))
        slots.append(
            _classify_slot(
                slot_id=f"router.path.{i}",
                text=note + " " + steps,
                corpus_refs=[],
                verified_anchor=False,
            )
        )

    for h in symbolic.get("high_dim_hypotheses") or []:
        refs = []
        m = h.get("metrics") or {}
        if m.get("anchor_ref"):
            refs.append(str(m["anchor_ref"]))
        slots.append(
            _classify_slot(
                slot_id=f"symbolic.{h.get('hypothesis_id')}",
                text=str(h.get("label_ko", "")) + " " + str(h.get("prompt_ko", "")),
                corpus_refs=refs,
                verified_anchor=False,
            )
        )

    for pt in symbolic.get("energy_curve") or []:
        if pt.get("found"):
            slots.append(
                _classify_slot(
                    slot_id=f"corpus.{pt.get('ref')}",
                    text=str(pt.get("text_snippet") or ""),
                    corpus_refs=[str(pt.get("ref"))],
                    verified_anchor=False,
                )
            )

    stats: dict[str, int] = {}
    for s in slots:
        c = s["utterance_class"]
        stats[c] = stats.get(c, 0) + 1

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": _utc_now(),
        "generator": GENERATOR,
        "policy_id": POLICY_ID,
        "issue_id": symbolic.get("issue_id") or shadow.get("issue_id"),
        "query_ko": symbolic.get("query_ko") or shadow.get("query_ko"),
        "disclaimer": DISCLAIMER,
        "utterance_classes": UTTERANCE_CLASSES,
        "reframe_contract_ko": (
            "「환각 제거」가 아니라 미결박 생성을 imagination_path로 명명·격리. "
            "사용자는 상상력 경로를 채택·기각·보류할 수 있음."
        ),
        "slots": slots,
        "stats": stats,
        "reproduce": {
            "command": "py scripts/build_logos_imagination_rail_envelope_v1.py",
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Build imagination rail envelope v1.")
    ap.add_argument("--router-json", type=Path, default=DEFAULT_ROUTER)
    ap.add_argument("--symbolic-json", type=Path, default=DEFAULT_SYMBOLIC)
    ap.add_argument("--shadow-json", type=Path, default=DEFAULT_SHADOW)
    ap.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    ap.add_argument("--out-artifact", type=Path, default=DEFAULT_OUT_ART)
    ap.add_argument("--skip-validate", action="store_true")
    args = ap.parse_args()

    def _p(p: Path) -> Path:
        return p if p.is_absolute() else ROOT / p

    doc = build(
        router=_load(_p(args.router_json)),
        symbolic=_load(_p(args.symbolic_json)),
        shadow=_load(_p(args.shadow_json)),
    )
    out = _p(args.out_artifact)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    if not args.skip_validate:
        _validate(doc, _p(args.schema))
    print(json.dumps({"ok": True, "out": str(out), "stats": doc["stats"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
