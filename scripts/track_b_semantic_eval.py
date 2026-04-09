#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import random
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_OUT = ART / "trackb_semantic_eval_latest.json"
DEFAULT_PAIRS = ART / "trackb_semantic_eval_demo_pairs_latest.jsonl"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _tok(s: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9가-힣]+", s.lower())


def _jaccard(a: str, b: str) -> float:
    sa, sb = set(_tok(a)), set(_tok(b))
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def _cosine_token_counts(a: str, b: str) -> float:
    """Bag-of-tokens cosine (stdlib only). Optional alternative to Jaccard set overlap."""
    ca, cb = Counter(_tok(a)), Counter(_tok(b))
    if not ca and not cb:
        return 1.0
    keys = set(ca) | set(cb)
    dot = sum(ca.get(k, 0) * cb.get(k, 0) for k in keys)
    na = math.sqrt(sum(ca.get(k, 0) ** 2 for k in keys))
    nb = math.sqrt(sum(cb.get(k, 0) ** 2 for k in keys))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def _semantic_fn(name: str) -> Callable[[str, str], float]:
    n = name.strip().lower()
    if n in ("jaccard", "token_jaccard"):
        return _jaccard
    if n in ("cosine_tokens", "cosine", "bow_cosine"):
        return _cosine_token_counts
    raise ValueError(f"unknown --semantic-metric: {name}")


def _oov_rate(src: str, pred: str) -> float:
    s = set(_tok(src))
    p = set(_tok(pred))
    if not p:
        return 1.0
    unseen = [t for t in p if t not in s]
    return len(unseen) / len(p)


def _read_pairs(path: Path) -> list[dict[str, str]]:
    pairs: list[dict[str, str]] = []
    if path.suffix.lower() == ".jsonl":
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            src = str(obj.get("source_text", obj.get("original_text", "")))
            pred = str(obj.get("predicted_text", obj.get("restored_text", "")))
            if src:
                pairs.append({"source_text": src, "predicted_text": pred})
    else:
        arr = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(arr, list):
            raise ValueError("JSON input must be an array")
        for obj in arr:
            src = str(obj.get("source_text", obj.get("original_text", "")))
            pred = str(obj.get("predicted_text", obj.get("restored_text", "")))
            if src:
                pairs.append({"source_text": src, "predicted_text": pred})
    if not pairs:
        raise ValueError(f"no valid pairs found in {path}")
    return pairs


def _build_demo_pairs(n: int = 50) -> list[dict[str, str]]:
    diagnoses = [
        "고혈압", "당뇨병", "고지혈증", "천식", "기관지염",
        "갑상선기능저하증", "만성신질환", "빈혈", "위염", "역류성식도염",
    ]
    actions = [
        "생활습관 교정", "약물 복용 유지", "추적 검사 시행", "식이 조절 권고", "운동 계획 수립"
    ]
    metrics = ["혈압", "공복혈당", "당화혈색소", "LDL 콜레스테롤", "크레아티닌"]

    random.seed(42)
    out: list[dict[str, str]] = []
    for i in range(n):
        d = diagnoses[i % len(diagnoses)]
        a = actions[(i * 3) % len(actions)]
        m = metrics[(i * 5) % len(metrics)]
        src = f"환자 {i+1}의 주진단은 {d}이며 {m} 수치 기반으로 {a}이 필요하다."
        # deterministic mild semantic mutation
        if i % 5 == 0:
            pred = src.replace("필요하다", "요구된다")
        elif i % 5 == 1:
            pred = src.replace("주진단은", "진단은")
        elif i % 5 == 2:
            pred = src.replace("수치 기반으로", "지표를 바탕으로")
        elif i % 5 == 3:
            pred = src
        else:
            pred = src.replace("환자", "대상자")
        out.append({"source_text": src, "predicted_text": pred})
    return out


def evaluate(pairs: list[dict[str, str]], sem: Callable[[str, str], float]) -> dict[str, Any]:
    exact = 0
    sem_scores: list[float] = []
    oov_scores: list[float] = []

    # collision proxy: different source -> same prediction
    pred_to_sources: dict[str, set[str]] = {}
    for row in pairs:
        s = row["source_text"]
        p = row["predicted_text"]
        if s == p:
            exact += 1
        sem_scores.append(sem(s, p))
        oov_scores.append(_oov_rate(s, p))
        pred_to_sources.setdefault(p, set()).add(s)

    collision_cases = sum(1 for srcs in pred_to_sources.values() if len(srcs) > 1)
    collision_rate = collision_cases / len(pred_to_sources) if pred_to_sources else 0.0

    # determinism proxy in static pair file is assumed true.
    return {
        "pair_count": len(pairs),
        "exact_match_rate": round(exact / len(pairs), 8),
        "average_semantic_score": round(sum(sem_scores) / len(sem_scores), 8),
        "collision_rate_proxy": round(collision_rate, 8),
        "oov_rate_avg": round(sum(oov_scores) / len(oov_scores), 8),
        "determinism_check": "dataset_static_pairs",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Track B semantic restoration baseline evaluator")
    ap.add_argument("--pairs", default="", help="JSON/JSONL file with source_text and predicted_text")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--emit-demo-pairs", action="store_true", help="Write generated demo pairs to artifacts")
    ap.add_argument("--demo-pairs-out", default=str(DEFAULT_PAIRS))
    ap.add_argument("--demo-count", type=int, default=50)
    ap.add_argument(
        "--semantic-metric",
        default="jaccard",
        help="jaccard (default, token-set Jaccard) or cosine_tokens (bag-of-tokens cosine, stdlib-only)",
    )
    args = ap.parse_args()
    sem_fn = _semantic_fn(args.semantic_metric)

    if args.pairs:
        pairs_path = (ROOT / args.pairs).resolve() if not Path(args.pairs).is_absolute() else Path(args.pairs)
        pairs = _read_pairs(pairs_path)
        source = str(pairs_path)
    else:
        pairs = _build_demo_pairs(args.demo_count)
        source = "generated_demo_pairs"
        if args.emit_demo_pairs:
            dpath = (ROOT / args.demo_pairs_out).resolve() if not Path(args.demo_pairs_out).is_absolute() else Path(args.demo_pairs_out)
            dpath.parent.mkdir(parents=True, exist_ok=True)
            with dpath.open("w", encoding="utf-8") as f:
                for r in pairs:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")

    metrics = evaluate(pairs, sem_fn)
    note = (
        "semantic_score uses token-set Jaccard (default). "
        "Optional cosine_tokens is bag-of-words cosine without embeddings. "
        "For BERTScore or neural embeddings, use a separate backend and artifact series."
    )
    if args.semantic_metric.strip().lower() not in ("jaccard", "token_jaccard"):
        note = (
            f"semantic_metric={args.semantic_metric}: lexical proxy only; "
            "not BERTScore or contextual embeddings."
        )
    out = {
        "schema": "track_b_semantic_eval_v1",
        "generated_at_utc": _utc_now(),
        "runner": "scripts/track_b_semantic_eval.py",
        "semantic_metric": args.semantic_metric,
        "input_source": source,
        "metrics": metrics,
        "fact_safe_note": note,
    }
    out_path = (ROOT / args.out).resolve() if not Path(args.out).is_absolute() else Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
