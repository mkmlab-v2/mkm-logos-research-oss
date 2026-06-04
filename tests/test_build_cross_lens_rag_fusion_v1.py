from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_cross_lens_rag_fusion_v1.py"


def _write(path: Path, obj: dict) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")


def test_fusion_emits_sasang_axis_block_in_json_and_md(tmp_path: Path) -> None:
    logos_wealth = tmp_path / "logos_wealth.json"
    logos_justice = tmp_path / "logos_justice.json"
    logos_empire = tmp_path / "logos_empire.json"
    fusion_stub = tmp_path / "fusion_stub.json"
    myeongni = tmp_path / "myeongni.json"
    sasang = tmp_path / "sasang.json"
    logos_lens = tmp_path / "logos.json"
    out_json = tmp_path / "fusion_out.json"
    out_md = tmp_path / "fusion_out.md"

    theme_doc = {"top_k": [{"verse_id": "v1", "score": 0.4}], "ts_utc": "2099-01-01T00:00:00Z"}
    _write(logos_wealth, theme_doc)
    _write(logos_justice, theme_doc)
    _write(logos_empire, theme_doc)
    _write(fusion_stub, {"consensus": {"consensus_sign": "bull"}})
    _write(
        myeongni,
        {
            "schema": "myeongni_independent_lens_v0",
            "lens_id": "myeongni",
            "scores": {"direction_score": 0.2, "confidence": 0.8},
            "ts_utc": "2099-01-01T00:00:00Z",
        },
    )
    _write(
        sasang,
        {
            "schema": "sasang_independent_lens_v0",
            "lens_id": "sasang",
            "scores": {"direction_score": 0.1, "confidence": 0.6},
            "b_track_axis_scores_v1": {
                "schema": "sasang_b_track_axis_scores_v1",
                "heat_proxy": 0.7,
                "cold_proxy": 0.3,
                "volatility_rarefaction_proxy": 0.5,
                "thermal_imbalance_proxy": 0.4,
                "disclaimer_ko": "테스트 면책",
            },
            "ts_utc": "2099-01-01T00:00:00Z",
        },
    )
    _write(
        logos_lens,
        {
            "schema": "logos_independent_lens_v0",
            "lens_id": "logos",
            "scores": {"direction_score": -0.05, "confidence": 0.4},
            "ts_utc": "2099-01-01T00:00:00Z",
        },
    )

    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--logos-wealth",
            str(logos_wealth),
            "--logos-justice",
            str(logos_justice),
            "--logos-empire",
            str(logos_empire),
            "--fusion-stub",
            str(fusion_stub),
            "--myeongni-lens",
            str(myeongni),
            "--sasang-lens",
            str(sasang),
            "--logos-lens",
            str(logos_lens),
            "--no-market-sasang",
            "--no-market-myeongni",
            "--skip-history-append",
            "--skip-alert-emit",
            "--out-json",
            str(out_json),
            "--out-md",
            str(out_md),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stdout + cp.stderr

    out = json.loads(out_json.read_text(encoding="utf-8"))
    assert out.get("version") == "1.2.0"
    assert out.get("lens_music_symbolic_passthrough_v1") is None
    ax = out.get("sasang_b_track_axis_scores_v1")
    assert isinstance(ax, dict)
    assert ax.get("schema") == "sasang_b_track_axis_scores_v1"
    assert ax.get("thermal_imbalance_proxy") == 0.4

    md = out_md.read_text(encoding="utf-8")
    assert "Sasang `b_track_axis_scores_v1`" in md
    assert "thermal_imbalance_proxy" in md
    assert "테스트 면책" in md


def test_fusion_includes_lens_music_passthrough_when_json_provided(tmp_path: Path) -> None:
    logos_wealth = tmp_path / "logos_wealth.json"
    logos_justice = tmp_path / "logos_justice.json"
    logos_empire = tmp_path / "logos_empire.json"
    fusion_stub = tmp_path / "fusion_stub.json"
    myeongni = tmp_path / "myeongni.json"
    sasang = tmp_path / "sasang.json"
    logos_lens = tmp_path / "logos.json"
    music_chain = tmp_path / "lens_music_gate_chain.json"
    out_json = tmp_path / "fusion_out.json"
    out_md = tmp_path / "fusion_out.md"

    theme_doc = {"top_k": [{"verse_id": "v1", "score": 0.4}], "ts_utc": "2099-01-01T00:00:00Z"}
    _write(logos_wealth, theme_doc)
    _write(logos_justice, theme_doc)
    _write(logos_empire, theme_doc)
    _write(fusion_stub, {"consensus": {"consensus_sign": "bull"}})
    _write(
        myeongni,
        {
            "schema": "myeongni_independent_lens_v0",
            "lens_id": "myeongni",
            "scores": {"direction_score": 0.2, "confidence": 0.8},
            "ts_utc": "2099-01-01T00:00:00Z",
        },
    )
    _write(
        sasang,
        {
            "schema": "sasang_independent_lens_v0",
            "lens_id": "sasang",
            "scores": {"direction_score": 0.1, "confidence": 0.6},
            "b_track_axis_scores_v1": {
                "schema": "sasang_b_track_axis_scores_v1",
                "heat_proxy": 0.5,
                "cold_proxy": 0.5,
                "volatility_rarefaction_proxy": 0.5,
                "thermal_imbalance_proxy": 0.5,
                "disclaimer_ko": "테스트",
            },
            "ts_utc": "2099-01-01T00:00:00Z",
        },
    )
    _write(
        logos_lens,
        {
            "schema": "logos_independent_lens_v0",
            "lens_id": "logos",
            "scores": {"direction_score": -0.05, "confidence": 0.4},
            "ts_utc": "2099-01-01T00:00:00Z",
        },
    )
    _write(
        music_chain,
        {
            "schema": "lens_music_gate_chain_v1",
            "ts_utc": "2099-01-01T00:00:00Z",
            "final_decision": "GO",
            "emotion_overlay_stage": "preview",
            "quality_guard_m7": {"status": "OK"},
        },
    )

    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--logos-wealth",
            str(logos_wealth),
            "--logos-justice",
            str(logos_justice),
            "--logos-empire",
            str(logos_empire),
            "--fusion-stub",
            str(fusion_stub),
            "--myeongni-lens",
            str(myeongni),
            "--sasang-lens",
            str(sasang),
            "--logos-lens",
            str(logos_lens),
            "--lens-music-gate-chain-json",
            str(music_chain),
            "--no-market-sasang",
            "--no-market-myeongni",
            "--skip-history-append",
            "--skip-alert-emit",
            "--out-json",
            str(out_json),
            "--out-md",
            str(out_md),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stdout + cp.stderr

    out = json.loads(out_json.read_text(encoding="utf-8"))
    lm = out.get("lens_music_symbolic_passthrough_v1")
    assert isinstance(lm, dict)
    assert lm.get("available") is True
    assert lm.get("passthrough", {}).get("final_decision") == "GO"

    md = out_md.read_text(encoding="utf-8")
    assert "Lens music (symbolic gate chain, passthrough)" in md
    assert "final_decision=GO" in md
