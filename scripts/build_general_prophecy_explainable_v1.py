# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.86, L:0.91, K:0.54, M:0.58}
# Balance: 92
# Purpose: Build explainable rationale layer for general prophecy with biblical/myeongri/sasang evidence and fusion decision.
# Keywords: general_prophecy, explainability, biblical, gematria, myeongri, sasang, fusion
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IN = ROOT / "docs" / "final" / "artifacts" / "general_prophecy_latest.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "general_prophecy_explainable_latest.json"

WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9_-]*")

BIBLICAL_RULES: list[dict[str, Any]] = [
    {"ref": "Matthew 24:32", "keywords": ["watch", "sign", "future", "timeline"], "theme": "watchfulness"},
    {"ref": "Daniel 2:21", "keywords": ["kingdom", "change", "season", "policy"], "theme": "regime_shift"},
    {"ref": "Ecclesiastes 3:1", "keywords": ["time", "season", "deadline", "window"], "theme": "timing_window"},
    {"ref": "Proverbs 21:5", "keywords": ["plan", "policy", "criteria", "discipline"], "theme": "disciplined_execution"},
    {"ref": "Isaiah 1:18", "keywords": ["judge", "reason", "evidence", "criteria"], "theme": "evidence_reasoning"},
    {"ref": "Habakkuk 2:2", "keywords": ["write", "vision", "plain", "record"], "theme": "traceable_record"},
    {"ref": "Luke 14:28", "keywords": ["count", "cost", "budget", "risk"], "theme": "cost_accounting"},
    {"ref": "1 Thessalonians 5:21", "keywords": ["test", "prove", "hold", "good"], "theme": "test_then_hold"},
]


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def a1z26_value(word: str) -> int:
    total = 0
    for ch in word.lower():
        if "a" <= ch <= "z":
            total += ord(ch) - ord("a") + 1
    return total


def extract_words(text: str) -> list[str]:
    return [m.group(0).lower() for m in WORD_RE.finditer(text)]


def biblical_evidence(question_text: str, domain_tags: list[str]) -> dict[str, Any]:
    text_l = question_text.lower()
    tags = {str(t).lower() for t in domain_tags}
    matched: list[dict[str, Any]] = []
    for rule in BIBLICAL_RULES:
        hits = [k for k in rule["keywords"] if k in text_l or k in tags]
        if hits:
            matched.append({"ref": rule["ref"], "theme": rule["theme"], "matched_keywords": hits})

    words = extract_words(question_text)
    gem_words = [w for w in words if len(w) >= 4][:8]
    gem_values = [{"word": w, "a1z26": a1z26_value(w)} for w in gem_words]
    resonance = round(sum(x["a1z26"] for x in gem_values) / max(1, len(gem_values)), 3)

    keyword_hits = sum(len(m["matched_keywords"]) for m in matched)
    score = min(1.0, 0.2 + 0.13 * len(matched) + 0.02 * keyword_hits + 0.0008 * resonance)
    coverage = round(min(1.0, keyword_hits / 6.0), 6)
    return {
        "score": round(score, 6),
        "keyword_coverage": coverage,
        "match_count": len(matched),
        "verse_matches": matched,
        "gematria": {"method": "a1z26", "tokens": gem_values, "resonance": resonance},
    }


def month_phase(month: int) -> str:
    if month in (1, 2, 3):
        return "기준선/탐색"
    if month in (4, 5, 6):
        return "압박/방어"
    if month in (7, 8, 9):
        return "재정비/경쟁"
    return "성과 회수/정리"


def myeongri_evidence(resolution_deadline_utc: str, domain_tags: list[str]) -> dict[str, Any]:
    dt = datetime.fromisoformat(resolution_deadline_utc.replace("Z", "+00:00"))
    phase = month_phase(dt.month)
    tags = {str(t).lower() for t in domain_tags}
    cycle_pressure = {"기준선/탐색": 0.46, "압박/방어": 0.72, "재정비/경쟁": 0.58, "성과 회수/정리": 0.44}[phase]
    boundary_risk = 0.18 if "policy" in tags or "macro" in tags else 0.08
    pillar_fit = round(max(0.0, min(1.0, cycle_pressure - boundary_risk + 0.12)), 6)
    cycle_alignment = round(max(0.0, min(1.0, cycle_pressure + 0.1)), 6)
    score = round(max(0.0, min(1.0, 0.25 + 0.45 * pillar_fit + 0.3 * cycle_alignment)), 6)
    return {
        "score": score,
        "phase": phase,
        "pillar_fit": pillar_fit,
        "cycle_alignment": cycle_alignment,
        "boundary_risk": round(boundary_risk, 6),
    }


def sasang_evidence(domain_tags: list[str], probability: float) -> dict[str, Any]:
    tags = {str(t).lower() for t in domain_tags}
    stress = 0.62 if {"macro", "rates", "energy"} & tags else 0.44
    balance = round(1.0 - abs(probability - 0.5) * 1.5, 6)
    response = round(max(0.0, min(1.0, 0.45 * stress + 0.55 * balance)), 6)
    score = round(max(0.0, min(1.0, 0.3 + 0.6 * response)), 6)
    phase_state = "압박완충" if stress >= 0.6 and response < 0.6 else ("탄력회복" if response >= 0.6 else "중립조정")
    return {
        "score": score,
        "stress_response": round(stress, 6),
        "balance_response": balance,
        "state_hint": phase_state,
        "response_strength": response,
    }


def fusion_decision(probability: float, b: dict[str, Any], m: dict[str, Any], s: dict[str, Any]) -> dict[str, Any]:
    weights = {"biblical": 0.38, "myeongri": 0.34, "sasang": 0.28}
    rationale_strength = (
        weights["biblical"] * float(b["score"])
        + weights["myeongri"] * float(m["score"])
        + weights["sasang"] * float(s["score"])
    )
    centered = probability - 0.5
    fused = centered * (0.55 + 0.45 * rationale_strength)
    if fused > 0.08:
        decision = "lean_true"
    elif fused < -0.08:
        decision = "lean_false"
    else:
        decision = "neutral"
    confidence = max(0.05, min(0.99, 0.5 + abs(fused) + (rationale_strength - 0.5) * 0.2))
    return {
        "decision": decision,
        "confidence": round(confidence, 6),
        "weights": weights,
        "rationale_strength": round(rationale_strength, 6),
        "calibration": {
            "probability_input": round(probability, 6),
            "centered": round(centered, 6),
            "fused_signal": round(fused, 6),
        },
    }


def build_question_explanation(q: dict[str, Any]) -> dict[str, Any]:
    qid = str(q.get("question_id", "unknown"))
    qtext = str(q.get("question_text", ""))
    tags = [str(t) for t in (q.get("domain_tags") or [])]
    forecasts = q.get("forecasts") or []
    prob = 0.5
    if forecasts and isinstance(forecasts[0], dict):
        prob = float(forecasts[0].get("probability_0_1", 0.5))

    bib = biblical_evidence(qtext, tags)
    mye = myeongri_evidence(str(q.get("resolution_deadline_utc", utc_now())), tags)
    sas = sasang_evidence(tags, prob)
    fusion = fusion_decision(prob, bib, mye, sas)

    top_evidence = []
    if bib["verse_matches"]:
        vm = bib["verse_matches"][0]
        top_evidence.append(f"biblical:{vm['ref']}:{','.join(vm['matched_keywords'])}")
    top_evidence.append(f"biblical_keyword_coverage:{bib['keyword_coverage']}")
    top_evidence.append(f"gematria_resonance:{bib['gematria']['resonance']}")
    top_evidence.append(
        f"myeongri_phase:{mye['phase']}:pillar_fit={mye['pillar_fit']}:cycle_alignment={mye['cycle_alignment']}"
    )
    top_evidence.append(f"sasang_state:{sas['state_hint']}:response_strength={sas['response_strength']}")

    summary = (
        f"{qid}는 성경(구절·키워드·게마트리아), 명리(시기/경계), 사상(스트레스 반응) "
        f"축을 결합한 결과 {fusion['decision']}로 판정되었다."
    )
    conflict = (
        "성경 점수와 명리 점수가 충돌하면 명리의 boundary_risk를 우선 반영하고, "
        "사상 축은 확신도 보정에만 사용한다."
    )

    return {
        "question_id": qid,
        "fusion_decision": fusion["decision"],
        "fusion_confidence": fusion["confidence"],
        "lane_weights": fusion["weights"],
        "fusion_calibration": fusion["calibration"],
        "explanation": {
            "why_summary": summary,
            "biblical": bib,
            "myeongri": mye,
            "sasang": sas,
            "conflict_resolution": conflict,
            "top_evidence": top_evidence,
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Build explainable rationale artifact for general prophecy registry.")
    ap.add_argument("--input", type=Path, default=DEFAULT_IN)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    in_path = args.input if args.input.is_absolute() else ROOT / args.input
    if not in_path.is_file():
        print(json.dumps({"ok": False, "error": f"missing_input:{in_path}"}, ensure_ascii=False))
        return 2
    doc = load_json(in_path)
    questions = doc.get("questions") or []
    rows = [build_question_explanation(q) for q in questions if isinstance(q, dict)]

    out_doc = {
        "schema": "general_prophecy_explainable_registry_v1",
        "generated_at_utc": utc_now(),
        "source_registry_path": str(in_path),
        "questions": rows,
    }
    out_path = args.output if args.output.is_absolute() else ROOT / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "questions": len(rows)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
