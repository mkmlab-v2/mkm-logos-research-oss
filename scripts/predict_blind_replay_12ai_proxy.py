# @MKM12-METADATA
# Type: Engine
# Vector: {S:0.7, L:0.8, K:0.8, M:0.5}
# Balance: 86
# Purpose: Generate 3-lens proxy predictions for blind replay dataset.
# Keywords: blind-replay, 12ai, multilens, predictions, exploratory_only
#!/usr/bin/env python3
"""Generate proxy 12AI multi-lens predictions for blind replay public dataset.

This is an exploratory B-track proxy predictor to validate the scoring pipeline.
It does not connect to live trading or A-track promotion paths.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROFILE_D_PARAMS_PATH = ROOT / "docs" / "final" / "artifacts" / "BLIND_REPLAY_PROXY_PROFILE_D_PARAMS_V1.json"
PROFILE_D_ENSEMBLE_PATH = (
    ROOT / "docs" / "final" / "artifacts" / "BLIND_REPLAY_PROXY_PROFILE_D_ENSEMBLE_SEARCH_V1.json"
)
REQUIRED_KEYS = {
    "m_myeongni",
    "d_myeongni",
    "m_sasang",
    "d_sasang",
    "v_penalty",
    "m_logos",
    "r_bonus",
    "band_m",
    "band_s",
    "band_l",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = line.strip().lstrip("\ufeff")
        if not s:
            continue
        try:
            o = json.loads(s)
        except json.JSONDecodeError:
            continue
        if isinstance(o, dict):
            out.append(o)
    return out


def _sign_from_score(score: float, neutral_band: float = 0.08) -> str:
    if score <= -neutral_band:
        return "DOWN_STRONG"
    if score >= neutral_band:
        return "UP_STRONG"
    return "NEUTRAL"


def _profile_params(profile: str) -> dict[str, float]:
    p = profile.strip().upper()
    if p == "A":
        return {
            "m_myeongni": 2.6,
            "d_myeongni": 1.0,
            "m_sasang": 1.3,
            "d_sasang": 0.35,
            "v_penalty": 0.22,
            "m_logos": 1.2,
            "r_bonus": 0.10,
            "band_m": 0.08,
            "band_s": 0.10,
            "band_l": 0.09,
        }
    if p == "B":
        return {
            "m_myeongni": 2.2,
            "d_myeongni": 0.8,
            "m_sasang": 1.2,
            "d_sasang": 0.3,
            "v_penalty": 0.2,
            "m_logos": 1.4,
            "r_bonus": 0.15,
            "band_m": 0.07,
            "band_s": 0.09,
            "band_l": 0.08,
        }
    if p == "C":
        return {
            "m_myeongni": 1.8,
            "d_myeongni": 0.6,
            "m_sasang": 1.0,
            "d_sasang": 0.25,
            "v_penalty": 0.15,
            "m_logos": 1.8,
            "r_bonus": 0.22,
            "band_m": 0.06,
            "band_s": 0.08,
            "band_l": 0.07,
        }
    if p == "D":
        if PROFILE_D_PARAMS_PATH.is_file():
            try:
                doc = json.loads(PROFILE_D_PARAMS_PATH.read_text(encoding="utf-8"))
                best = doc.get("best") if isinstance(doc, dict) else {}
                params = (best or {}).get("params") if isinstance(best, dict) else {}
                if isinstance(params, dict):
                    if REQUIRED_KEYS.issubset(set(params.keys())):
                        return {k: float(params[k]) for k in REQUIRED_KEYS}
            except Exception:
                pass
        # Fallback D baseline if tuned params artifact is missing.
        return {
            "m_myeongni": 2.0,
            "d_myeongni": 0.9,
            "m_sasang": 1.1,
            "d_sasang": 0.3,
            "v_penalty": 0.18,
            "m_logos": 1.6,
            "r_bonus": 0.18,
            "band_m": 0.065,
            "band_s": 0.085,
            "band_l": 0.075,
        }
    if p == "DS":
        # Soft-ensemble: weighted average of top-2 blend candidates from ensemble search artifact.
        if PROFILE_D_ENSEMBLE_PATH.is_file():
            try:
                doc = json.loads(PROFILE_D_ENSEMBLE_PATH.read_text(encoding="utf-8"))
                top = doc.get("top20") if isinstance(doc.get("top20"), list) else []
                picked: list[tuple[float, dict[str, float]]] = []
                for row in top[:2]:
                    params = row.get("params") if isinstance(row, dict) else {}
                    score = float((row or {}).get("unified_score_balanced") or 0.0)
                    if isinstance(params, dict) and REQUIRED_KEYS.issubset(set(params.keys())):
                        picked.append((max(0.0, score), {k: float(params[k]) for k in REQUIRED_KEYS}))
                if len(picked) >= 2:
                    total_w = sum(max(1e-6, x[0]) for x in picked)
                    return {
                        k: sum((max(1e-6, w) / total_w) * pmap[k] for w, pmap in picked)
                        for k in REQUIRED_KEYS
                    }
                if len(picked) == 1:
                    return picked[0][1]
            except Exception:
                pass
        # Fallback to canonical D if ensemble artifact is unavailable.
        return _profile_params("D")
    raise ValueError(f"Unknown profile: {profile} (use A/B/C/D/DS)")


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate proxy 12AI predictions for blind replay.")
    ap.add_argument("--public-dataset", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--profile", default="B", help="Prediction profile preset: A, B, C, D, or DS (default: B)")
    args = ap.parse_args()

    rows = _read_jsonl(args.public_dataset)
    if not rows:
        raise SystemExit(f"public dataset missing/empty: {args.public_dataset}")
    params = _profile_params(args.profile)

    preds: list[dict[str, Any]] = []
    for r in rows:
        sid = str(r.get("sample_id") or "")
        feat = r.get("features") if isinstance(r.get("features"), dict) else {}
        m = float(feat.get("momentum_index") or 0.0)
        v = float(feat.get("volatility_index") or 0.0)
        d = float(feat.get("drawdown_index") or 0.0)
        rp = float(feat.get("range_spread_index") or 0.0)

        # Lens-style proxy scores
        score_myeongni = (params["m_myeongni"] * m) + (params["d_myeongni"] * d)
        score_sasang = (params["m_sasang"] * m) + (params["d_sasang"] * d) - (
            params["v_penalty"] * max(0.0, v - 0.12)
        )
        score_logos = (params["m_logos"] * m) + (
            params["r_bonus"] * (0.25 - min(0.25, abs(rp - 0.25)))
        )

        sign_m = _sign_from_score(score_myeongni, neutral_band=params["band_m"])
        sign_s = _sign_from_score(score_sasang, neutral_band=params["band_s"])
        sign_l = _sign_from_score(score_logos, neutral_band=params["band_l"])

        votes = [sign_m, sign_s, sign_l]
        down = votes.count("DOWN_STRONG")
        up = votes.count("UP_STRONG")
        if down > up:
            final_sign = "DOWN_STRONG"
        elif up > down:
            final_sign = "UP_STRONG"
        else:
            final_sign = "NEUTRAL"

        confidence = min(0.95, max(0.15, (max(down, up) / 3.0) + 0.2))
        preds.append(
            {
                "sample_id": sid,
                "direction_sign": final_sign,
                "confidence_0_1": round(confidence, 4),
                "exploratory_only": True,
                "lens_votes": {
                    "myeongni": sign_m,
                    "sasang": sign_s,
                    "logos": sign_l,
                },
                "profile": args.profile.strip().upper(),
                "generated_at_utc": _utc_now(),
            }
        )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        for p in preds:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
    print(f"WROTE: {args.out.resolve()} rows={len(preds)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
