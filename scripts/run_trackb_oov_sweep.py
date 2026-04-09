#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import random
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_jsonl(path: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        rows.append(
            {
                "source_text": str(obj.get("source_text", "")),
                "predicted_text": str(obj.get("predicted_text", "")),
            }
        )
    return rows


def _tok(s: str) -> set[str]:
    import re

    return set(re.findall(r"[A-Za-z0-9가-힣]+", s.lower()))


def _jaccard(a: str, b: str) -> float:
    sa, sb = _tok(a), _tok(b)
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def _oov_rate(src: str, pred: str) -> float:
    s = _tok(src)
    p = _tok(pred)
    if not p:
        return 1.0
    return len([t for t in p if t not in s]) / len(p)


def _normalize_predicted(text: str) -> str:
    """Lightweight text normalize before inject (NFKC + whitespace collapse)."""
    import unicodedata

    s = unicodedata.normalize("NFKC", text)
    return " ".join(s.split())


def _inject_oov(text: str, ratio: float) -> str:
    if ratio <= 0.0:
        return text
    noise_bank = ["xqz", "token999", "novelterm", "외생어", "신규코드", "zzk"]
    words = text.split()
    if not words:
        return text
    k = max(1, int(len(words) * ratio))
    idxs = list(range(len(words)))
    random.shuffle(idxs)
    for i in idxs[:k]:
        words[i] = f"{words[i]} {random.choice(noise_bank)}"
    return " ".join(words)


def _evaluate(
    rows: list[dict[str, str]],
    oov_ratio: float,
    *,
    normalize_predicted: bool,
) -> dict[str, float]:
    random.seed(42)
    sem = []
    oov = []
    for r in rows:
        src = r["source_text"]
        pred_text = r["predicted_text"]
        if normalize_predicted:
            pred_text = _normalize_predicted(pred_text)
        pred = _inject_oov(pred_text, oov_ratio)
        sem.append(_jaccard(src, pred))
        oov.append(_oov_rate(src, pred))
    return {
        "pair_count": len(rows),
        "average_semantic_score": round(sum(sem) / len(sem), 8),
        "oov_rate_avg": round(sum(oov) / len(oov), 8),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Track B OOV stress sweep")
    ap.add_argument(
        "--domains",
        default="medical,finance,policy",
        help="Comma-separated domains with existing pair jsonl files.",
    )
    ap.add_argument(
        "--oov-ratios",
        default="0.0,0.05,0.1,0.15,0.2,0.25,0.3",
        help="Comma-separated synthetic OOV inject ratios (stress sweep).",
    )
    ap.add_argument(
        "--normalize-predicted",
        action="store_true",
        help="Apply NFKC + whitespace collapse to predicted text before inject (mitigation probe).",
    )
    ap.add_argument(
        "--out",
        default="",
        help="Default: trackb_oov_collision_sweep_latest.json; "
        "with --normalize-predicted: trackb_oov_collision_sweep_norm_latest.json",
    )
    args = ap.parse_args()

    out_default = (
        ART / "trackb_oov_collision_sweep_norm_latest.json"
        if args.normalize_predicted
        else ART / "trackb_oov_collision_sweep_latest.json"
    )
    out_arg = args.out.strip() if args.out else str(out_default)

    domains = [d.strip() for d in args.domains.split(",") if d.strip()]
    ratios = [float(x.strip()) for x in args.oov_ratios.split(",") if x.strip()]

    report: dict[str, object] = {
        "schema": "trackb_oov_collision_sweep_v1",
        "generated_at_utc": _utc_now(),
        "options": {
            "normalize_predicted": bool(args.normalize_predicted),
            "predicted_text_normalization": (
                "NFKC+whitespace_collapse" if args.normalize_predicted else "none"
            ),
        },
        "domains": {},
        "oov_ratios": ratios,
        "out_of_scope": "No production promotion, no trading trigger.",
    }

    for domain in domains:
        p = ART / f"trackb_semantic_eval_pairs_{domain}_v1.jsonl"
        rows = _read_jsonl(p)
        domain_rows = []
        for ratio in ratios:
            metrics = _evaluate(rows, ratio, normalize_predicted=args.normalize_predicted)
            domain_rows.append({"oov_ratio": ratio, "metrics": metrics})
        report["domains"][domain] = {
            "pair_file": str(p.as_posix()),
            "sweep": domain_rows,
        }

    out_path = Path(out_arg) if Path(out_arg).is_absolute() else (ROOT / out_arg)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
