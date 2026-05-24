"""Regression: B-track LLM input bundle v1.3 includes interpretive bridge slice."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_build_btrack_llm_input_bundle_outputs_v13_with_interpretive(tmp_path: Path) -> None:
    myeongni = tmp_path / "myeongni.json"
    sasang = tmp_path / "sasang.json"
    logos = tmp_path / "logos.json"
    fusion = tmp_path / "fusion.json"
    minority = tmp_path / "minority_monthly.json"
    interpretive = tmp_path / "interpretive.json"
    out = tmp_path / "bundle.json"
    for p, label in (
        (myeongni, "m"),
        (sasang, "s"),
        (logos, "l"),
        (fusion, "f"),
        (minority, "mm"),
    ):
        p.write_text(json.dumps({"slot": label}), encoding="utf-8")

    interpretive.write_text(
        json.dumps(
            {
                "schema": "sasang_interpretive_insight_bundle_v1",
                "version": "1.1.0",
                "decision_authority": "human_only",
                "rail": "B_TRACK",
                "synthesis_v1": {
                    "forbidden_synthesis_ko": "auto merge forbidden",
                    "disagreement_protocol_ko": "hold observation",
                },
                "sections": [
                    {
                        "axis_id": "byeongjeung_yakri",
                        "title_ko": "병증",
                        "availability": "partial",
                        "summary_ko": "문헌 앵커",
                        "interpretive_depth_ko": "must not appear in bridge",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    cmd = [
        "py",
        str(ROOT / "scripts" / "build_btrack_llm_input_bundle.py"),
        "--myeongni",
        str(myeongni),
        "--sasang",
        str(sasang),
        "--logos",
        str(logos),
        "--fusion",
        str(fusion),
        "--minority-monthly",
        str(minority),
        "--interpretive",
        str(interpretive),
        "--output",
        str(out),
    ]
    cp = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)
    assert cp.returncode == 0, cp.stderr + cp.stdout
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["version"] == "1.4.0"
    bridge = data["artifacts"]["sasang_interpretive_bridge_context"]
    assert bridge["available"] is True
    assert bridge["auto_weight_adjustment_forbidden"] is True
    assert bridge["track_a_live_routing_forbidden"] is True
    assert bridge["axis_count"] == 1
    assert bridge["sections_slice"][0]["axis_id"] == "byeongjeung_yakri"
    assert "interpretive_depth_ko" not in json.dumps(bridge, ensure_ascii=False)
    assert str(interpretive.resolve()) in data["artifact_paths"]["sasang_interpretive_insight_bundle"]


def test_build_btrack_llm_input_bundle_market_observation_slots(tmp_path: Path) -> None:
    out = tmp_path / "bundle.json"
    for name in ("m.json", "s.json", "l.json", "f.json", "mm.json"):
        (tmp_path / name).write_text("{}", encoding="utf-8")
    market_myeongni = tmp_path / "market_myeongni.json"
    market_sasang = tmp_path / "market_sasang.json"
    market_myeongni.write_text(
        json.dumps(
            {
                "schema": "market_myeongni_lens_v1",
                "scores": {"direction_score": 0.05, "confidence": 0.6},
                "direction_sign": "neutral",
                "overlay": {"upstream_lens_id": "myeongni", "applied": {}},
                "ts_utc": "2026-05-25T00:00:00Z",
            }
        ),
        encoding="utf-8",
    )
    market_sasang.write_text(
        json.dumps(
            {
                "schema": "market_sasang_lens_v1",
                "fusion_bridge": {"score_hint": 0.1},
                "uncertainty": {"composite_uncertainty": 0.9},
                "veto": {"force_hold": True, "reason_codes": ["HIGH_ENTROPY_SOFTMAX"]},
                "ts_utc": "2026-05-25T00:00:00Z",
            }
        ),
        encoding="utf-8",
    )
    cmd = [
        "py",
        str(ROOT / "scripts" / "build_btrack_llm_input_bundle.py"),
        "--myeongni",
        str(tmp_path / "m.json"),
        "--sasang",
        str(tmp_path / "s.json"),
        "--logos",
        str(tmp_path / "l.json"),
        "--fusion",
        str(tmp_path / "f.json"),
        "--minority-monthly",
        str(tmp_path / "mm.json"),
        "--skip-interpretive",
        "--market-myeongni-lens",
        str(market_myeongni),
        "--market-sasang-lens",
        str(market_sasang),
        "--output",
        str(out),
    ]
    cp = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)
    assert cp.returncode == 0, cp.stderr + cp.stdout
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["version"] == "1.4.0"
    mm_slot = data["artifacts"]["market_myeongni_observation_slot"]
    ms_slot = data["artifacts"]["market_sasang_observation_slot"]
    assert mm_slot["available"] is True
    assert mm_slot["bridge_mode"] == "read_only_observation"
    assert mm_slot["track_a_live_routing_forbidden"] is True
    assert ms_slot["available"] is True
    assert ms_slot["market_sasang_summary"]["veto_force_hold"] is True
    assert ms_slot["direction_score"] == 0.1
    assert ms_slot["confidence"] is not None


def test_build_btrack_llm_input_bundle_skip_interpretive(tmp_path: Path) -> None:
    out = tmp_path / "bundle.json"
    for name in ("m.json", "s.json", "l.json", "f.json", "mm.json"):
        (tmp_path / name).write_text("{}", encoding="utf-8")
    cmd = [
        "py",
        str(ROOT / "scripts" / "build_btrack_llm_input_bundle.py"),
        "--myeongni",
        str(tmp_path / "m.json"),
        "--sasang",
        str(tmp_path / "s.json"),
        "--logos",
        str(tmp_path / "l.json"),
        "--fusion",
        str(tmp_path / "f.json"),
        "--minority-monthly",
        str(tmp_path / "mm.json"),
        "--skip-interpretive",
        "--output",
        str(out),
    ]
    cp = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)
    assert cp.returncode == 0, cp.stderr + cp.stdout
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["artifacts"]["sasang_interpretive_bridge_context"]["available"] is False
