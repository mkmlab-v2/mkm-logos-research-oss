#!/usr/bin/env python3
"""Curate slot dictionary using failure-case deltas from bridge policy run."""

from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.report_multilens_performance_eval import evaluate_report


INPUT_V2 = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
BASELINE_V2 = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_PERFORMANCE_EVAL_REPORT_V2.json"
DECISION = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_ULTRA_COMPRESSION_DECISION_V1.json"
OUT = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_DOMAIN_SLOT_DICTIONARY_V61.json"

TOKEN_RE = re.compile(r"[A-Za-z0-9_가-힣]+|[א-ת]+|[Α-Ωα-ωϛϟϡ]+")


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _tokens(text: str) -> list[str]:
    return [w.lower() for w in TOKEN_RE.findall(text)]


def _seed_slots() -> dict[str, set[str]]:
    return {
        "S1": {"state", "state_id", "명리", "전이", "regime"},
        "S2": {"policy", "boundary", "trigger", "gate", "caps", "cadence"},
        "S3": {"evidence", "witness", "traceability", "direct", "증거", "원문", "해시"},
        "S4": {"manual", "strict", "review", "검토", "수동", "엄격"},
        "S5": {"체질", "사상의학", "sasang", "소양", "소음", "태양", "태음"},
        "S6": {"성경", "bible", "logos", "시편", "원어"},
        "S7": {"compression", "복원", "token", "fidelity", "jaccard", "saving"},
    }


def _classify_token(tok: str) -> str | None:
    checks = [
        ("S1", ("state", "명리", "전이", "regime")),
        ("S2", ("policy", "boundary", "trigger", "gate", "cadence")),
        ("S3", ("evidence", "witness", "trace", "direct", "증거", "원문", "해시")),
        ("S4", ("manual", "strict", "review", "검토", "수동", "엄격")),
        ("S5", ("체질", "사상의학", "sasang", "소양", "소음", "태양", "태음")),
        ("S6", ("성경", "bible", "logos", "시편", "원어")),
        ("S7", ("compression", "복원", "token", "fidelity", "jaccard", "saving")),
    ]
    for sid, keys in checks:
        if any(k in tok for k in keys):
            return sid
    return None


def main() -> int:
    src = _load(INPUT_V2)
    base = _load(BASELINE_V2)
    dec = _load(DECISION)
    selected = dec.get("selected_candidate") or {}
    baseline_avg_jaccard = float(base.get("compression_metrics", {}).get("avg_reconstruction_fidelity_jaccard", 0.0))
    threshold_pp = float(dec.get("target", {}).get("jaccard_drop_threshold_pp", 2.0))

    common_kwargs = dict(
        source_input="docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json",
        mode="experimental",
        strategy=str(selected.get("strategy", "A")),
        intensity=str(selected.get("intensity", "extreme")),
        must_keep={"사상의학", "체질", "sasang", "myeongri", "bible"},
        jaccard_drop_threshold_pp=threshold_pp,
        baseline_avg_jaccard=baseline_avg_jaccard,
        general_max_saving_rate=(float(selected["general_max_saving_rate"]) if selected.get("general_max_saving_rate") is not None else None),
        sensitive_max_saving_rate=(float(selected["sensitive_max_saving_rate"]) if selected.get("sensitive_max_saving_rate") is not None else None),
        hangul_max_saving_rate=(float(selected["hangul_max_saving_rate"]) if selected.get("hangul_max_saving_rate") is not None else None),
        use_domain_router=True,
    )
    off = evaluate_report(src, include_gematria_metadata=False, include_gematria_4d_bridge=False, **common_kwargs)
    on = evaluate_report(
        src,
        include_gematria_metadata=True,
        include_gematria_4d_bridge=True,
        apply_gematria_4d_bridge_policy=True,
        use_contextual_generator_v2=True,
        use_contextual_generator_v3=True,
        use_contextual_generator_v4=True,
        use_contextual_generator_v5_codec=True,
        **common_kwargs,
    )

    off_cases = {str(r.get("id")): r for r in off.get("compression_metrics", {}).get("cases", [])}
    on_cases = {str(r.get("id")): r for r in on.get("compression_metrics", {}).get("cases", [])}
    source_by_id = {str(c.get("id")): str(c.get("raw_text", "")) for c in src.get("compression_cases", [])}

    failure_ids: list[str] = []
    for cid, o in off_cases.items():
        n = on_cases.get(cid)
        if n is None:
            continue
        off_f = float(o.get("reconstruction_fidelity_jaccard", 0.0))
        on_f = float(n.get("reconstruction_fidelity_jaccard", 0.0))
        if on_f + 1e-12 < off_f:
            failure_ids.append(cid)

    slot_terms = _seed_slots()
    bucket_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for cid in failure_ids:
        for tok in _tokens(source_by_id.get(cid, "")):
            if len(tok) <= 1:
                continue
            sid = _classify_token(tok)
            if sid is None:
                continue
            bucket_counts[sid][tok] += 1

    for sid, ctr in bucket_counts.items():
        for tok, _ in ctr.most_common(12):
            slot_terms[sid].add(tok)

    out = {
        "schema": "multilens_domain_slot_dictionary_v61",
        "source_input": "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json",
        "failure_case_count": len(failure_ids),
        "slots": {sid: sorted(vals)[:32] for sid, vals in slot_terms.items()},
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
