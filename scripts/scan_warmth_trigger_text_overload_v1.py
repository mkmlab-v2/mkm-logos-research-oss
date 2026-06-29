#!/usr/bin/env python3
"""Rule-based WTT text overload scan — T_high proxy from user text ([HYPO])."""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LEXICON = ROOT / "docs/final/artifacts/warmth_trigger_text_overload_lexicon_v1.json"
DEFAULT_PROFILE = ROOT / "docs/final/schemas/warmth_trigger_profile_v1.example.json"
DEFAULT_OUT = ROOT / "reports/warmth_trigger_text_overload_scan_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _clip(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _thresholds_from_profile(profile: dict[str, Any] | None) -> tuple[float, float]:
    if not profile:
        return -0.4, 0.55
    t_high = profile.get("epb", {}).get("thresholds", {}).get("t_high", {})
    return float(t_high.get("valence_floor", -0.4)), float(t_high.get("arousal_ceiling", 0.55))


def scan_text(
    *,
    text: str,
    lexicon: dict[str, Any],
    profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized = _normalize_text(text)
    defaults = lexicon.get("defaults", {})
    intensity = float(defaults.get("base_intensity_0_1", 0.25))
    valence = float(defaults.get("base_valence_proxy", 0.0))
    arousal = float(defaults.get("base_arousal_proxy", 0.0))
    surprisal = float(defaults.get("base_surprisal_0_1", 0.2))

    matched: list[dict[str, Any]] = []
    human_gate = False

    for sig in lexicon.get("signals") or []:
        for token in sig.get("tokens_ko") or []:
            if token.lower() in normalized:
                intensity += float(sig.get("intensity_delta", 0))
                valence += float(sig.get("valence_delta", 0))
                arousal += float(sig.get("arousal_delta", 0))
                surprisal += float(sig.get("surprisal_delta", 0))
                matched.append(
                    {
                        "signal_id": sig["signal_id"],
                        "weight": float(sig.get("intensity_delta", 0)),
                        "matched_token": token,
                    }
                )
                if sig.get("human_gate"):
                    human_gate = True
                break

    intensity = _clip(intensity, 0.0, 1.0)
    valence = _clip(valence, -1.0, 1.0)
    arousal = _clip(arousal, -1.0, 1.0)
    surprisal = _clip(surprisal, 0.0, 1.0)

    valence_floor, arousal_ceiling = _thresholds_from_profile(profile)
    t_high_breach = valence <= valence_floor or arousal >= arousal_ceiling

    med = float(defaults.get("overload_medium_intensity", 0.55))
    high = float(defaults.get("overload_high_intensity", 0.72))

    if human_gate:
        overload_risk = "human_gate_hold"
        suggested_arm = "human_gate_hold"
    elif t_high_breach or intensity >= high:
        overload_risk = "high"
        suggested_arm = "warm_only_cooldown"
    elif intensity >= med:
        overload_risk = "medium"
        suggested_arm = "re_dose_or_lower_intensity"
    else:
        overload_risk = "low"
        suggested_arm = "standard"

    return {
        "schema": "warmth_trigger_text_overload_scan_v1",
        "version": "1.0.0",
        "hypothesis_class": "HYPO",
        "track": "B",
        "research_only": True,
        "generated_at_utc": _utc_now(),
        "text_len": len(text),
        "proxies": {
            "intensity_0_1": round(intensity, 6),
            "valence_proxy": round(valence, 6),
            "arousal_proxy": round(arousal, 6),
            "surprisal_proxy_0_1": round(surprisal, 6),
        },
        "overload_risk": overload_risk,
        "t_high_breach_proxy": t_high_breach,
        "suggested_arm": suggested_arm,
        "profile_ref": profile.get("profile_version") if profile else None,
        "thresholds_used": {
            "valence_floor": valence_floor,
            "arousal_ceiling": arousal_ceiling,
        },
        "matched_signals": matched,
        "metaphor_notices": [
            "text_lexicon_proxy_not_clinical_diagnosis",
            "t_high_breach_is_epb_metaphor_alignment_not_brain_measurement",
            "human_gate_hold_requires_human_or_safeops_not_auto_treatment",
        ],
        "provenance": {
            "source": "scan_warmth_trigger_text_overload_v1",
            "experiment_id": lexicon.get("provenance", {}).get("experiment_id", "wtt_epb_pilot_01"),
            "lexicon_ref": "docs/final/artifacts/warmth_trigger_text_overload_lexicon_v1.json",
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--text", type=str, help="User utterance to scan.")
    ap.add_argument("--text-file", type=Path, help="UTF-8 text file input.")
    ap.add_argument("--lexicon-json", type=Path, default=DEFAULT_LEXICON)
    ap.add_argument("--profile-json", type=Path, default=DEFAULT_PROFILE)
    ap.add_argument("--no-profile", action="store_true")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if args.text_file:
        text = args.text_file.read_text(encoding="utf-8")
    elif args.text:
        text = args.text
    else:
        ap.error("Provide --text or --text-file")

    lexicon = _load_json(args.lexicon_json)
    profile = None if args.no_profile else _load_json(args.profile_json)
    report = scan_text(text=text, lexicon=lexicon, profile=profile)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "overload_risk": report["overload_risk"],
                "suggested_arm": report["suggested_arm"],
                "out": str(args.out.resolve()),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
