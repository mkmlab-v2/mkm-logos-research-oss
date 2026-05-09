#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_LENS = ART / "myeongni_independent_lens_latest.json"
DEFAULT_WEATHER = ART / "general_prophecy_explainability_quality_v1_latest.json"
DEFAULT_OUT = ART / "myeongni_weather_fusion_profile_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _f(v: Any, d: float = 0.0) -> float:
    return float(v) if isinstance(v, (int, float)) else d


def _clip(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _weather_pair(weather: dict[str, Any]) -> tuple[float, float]:
    s = weather.get("summary") if isinstance(weather.get("summary"), dict) else {}
    direct = s.get("direct_match_rate")
    if direct is None:
        direct = s.get("coverage_rate")
    repro = s.get("reproducible_evidence_rate")
    return _f(direct, 0.5), _f(repro, 0.8)


def _core(lens: dict[str, Any]) -> tuple[float, float]:
    scores = lens.get("scores") if isinstance(lens.get("scores"), dict) else {}
    adv = lens.get("advanced") if isinstance(lens.get("advanced"), dict) else {}
    coord = adv.get("coordinator") if isinstance(adv.get("coordinator"), dict) else {}
    math = coord.get("mkm_myeongni_math") if isinstance(coord.get("mkm_myeongni_math"), dict) else {}
    direction = _f(math.get("arbitrated_direction_score"), _f(scores.get("direction_score"), 0.0))
    conf = _f(math.get("arbitrated_confidence"), _f(scores.get("confidence"), 0.5))
    return _clip(direction, -1.0, 1.0), _clip(conf, 0.0, 1.0)


def _score_candidate(
    *,
    conf_core: float,
    direct: float,
    repro: float,
    weight_direct: float,
    weight_repro: float,
    anchor_direct: float,
    anchor_repro: float,
    term_clip: float,
) -> tuple[float, dict[str, float]]:
    term = (weight_direct * (direct - anchor_direct)) + (weight_repro * (repro - anchor_repro))
    term = _clip(term, -term_clip, term_clip)
    conf_adj = _clip(conf_core + term, 0.0, 1.0)
    # Objective: keep confidence in practical band (not too low, not overconfident).
    target = 0.58
    score = abs(conf_adj - target) + (0.3 if conf_adj < 0.35 else 0.0) + (0.2 if conf_adj > 0.82 else 0.0)
    return score, {"weather_term": round(term, 6), "confidence_adjusted": round(conf_adj, 6)}


def main() -> int:
    ap = argparse.ArgumentParser(description="Train weather-fusion profile for myeongni response v2.")
    ap.add_argument("--lens-json", type=Path, default=DEFAULT_LENS)
    ap.add_argument("--weather-quality-json", type=Path, default=DEFAULT_WEATHER)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--allow-apply", action="store_true", help="Set policy.allow_apply=true in output profile")
    ap.add_argument("--human-signoff-ack", action="store_true", help="Set policy.human_signoff_ack=true")
    args = ap.parse_args()

    lens_path = args.lens_json if args.lens_json.is_absolute() else ROOT / args.lens_json
    weather_path = args.weather_quality_json if args.weather_quality_json.is_absolute() else ROOT / args.weather_quality_json
    lens = _read_json(lens_path)
    weather = _read_json(weather_path)
    _, conf_core = _core(lens)
    direct, repro = _weather_pair(weather)

    best: dict[str, Any] | None = None
    candidates: list[dict[str, Any]] = []
    for wd in (0.02, 0.04, 0.06, 0.08, 0.1, 0.12):
        for wr in (0.02, 0.04, 0.06, 0.08, 0.1):
            for ad in (0.45, 0.5, 0.55):
                for ar in (0.75, 0.8, 0.85):
                    for tc in (0.1, 0.15, 0.2):
                        score, obs = _score_candidate(
                            conf_core=conf_core,
                            direct=direct,
                            repro=repro,
                            weight_direct=wd,
                            weight_repro=wr,
                            anchor_direct=ad,
                            anchor_repro=ar,
                            term_clip=tc,
                        )
                        row = {
                            "weight_direct": wd,
                            "weight_repro": wr,
                            "anchor_direct": ad,
                            "anchor_repro": ar,
                            "term_clip": tc,
                            "score": round(score, 6),
                            **obs,
                        }
                        candidates.append(row)
                        if best is None or row["score"] < best["score"]:
                            best = row

    assert best is not None
    out = {
        "schema": "myeongni_weather_fusion_profile_v1",
        "generated_at_utc": _now(),
        "input": {
            "lens_json": str(lens_path),
            "weather_quality_json": str(weather_path),
            "conf_core": round(conf_core, 6),
            "direct_match_rate_or_coverage": round(direct, 6),
            "reproducible_evidence_rate": round(repro, 6),
        },
        "recommended": best,
        "top_candidates": sorted(candidates, key=lambda x: x["score"])[:10],
        "policy": {
            "allow_apply": bool(args.allow_apply),
            "human_signoff_ack": bool(args.human_signoff_ack),
            "research_only": True,
            "note": "Profile training is heuristic; enforce human signoff before runtime apply.",
        },
    }

    out_path = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "recommended": best}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

