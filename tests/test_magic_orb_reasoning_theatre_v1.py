"""Magic Orb reasoning theatre v1 — schema, builder, mkmlife lib parity."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "docs/final/schemas/magic_orb_reasoning_theatre_v1.schema.json"
EXAMPLE = ROOT / "docs/final/artifacts/fixtures/magic_orb_reasoning_theatre_v1.example.json"
THEATRE_LIB = ROOT / "projects/mkm/mkm-life/lib/magic-orb-reasoning-theatre-v1.ts"
BUILDER = ROOT / "scripts/build_magic_orb_reasoning_theatre_v1.py"
ENVELOPE = ROOT / "projects/mkm/mkm-life/public/data/three_lens_sphere_envelope_public_v1.json"
INSIGHT = ROOT / "projects/mkm/mkm-life/public/data/magic_orb_question_insight_v1_latest.json"
STREAM_ROUTE = ROOT / "projects/mkm/mkm-life/app/api/v1/magic-orb/reasoning-theatre/stream/route.ts"
EVENT_SCHEMA = ROOT / "docs/final/schemas/magic_orb_reasoning_theatre_event_v1.schema.json"
AUDIO_LIB = ROOT / "projects/mkm/mkm-life/lib/magic-orb-reasoning-theatre-audio-v1.ts"
PD_THEATRE_LIB = ROOT / "projects/no1kmedi/src/lib/personadiaryReasoningTheatreV1.ts"
PD_THEATRE_UI = ROOT / "projects/no1kmedi/src/components/personadiary/PersonadiaryReasoningTheatre.tsx"


def test_schema_required_step_ids() -> None:
    doc = json.loads(SCHEMA.read_text(encoding="utf-8"))
    step_enum = doc["properties"]["active_step_id"]["enum"]
    assert "ingest" in step_enum
    assert "lens_logos" in step_enum
    assert "conflict" in step_enum
    assert "bloom" in step_enum
    assert "resolve" in step_enum
    assert doc["properties"]["research_only"]["const"] is True
    assert doc["properties"]["non_gating"]["const"] is True


def test_builder_emits_valid_doc_public_logos() -> None:
    proc = subprocess.run(
        [sys.executable, str(BUILDER), "--active-step", "field", "--public-logos-only"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    out = ROOT / "docs/final/artifacts/magic_orb_reasoning_theatre_v1_latest.json"
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "magic_orb_reasoning_theatre_v1"
    assert doc["active_step_id"] == "field"
    ids = [s["id"] for s in doc["steps"]]
    assert "lens_logos" in ids
    assert "lens_myeongni" not in ids
    assert "lens_sasang" not in ids
    assert all("orbit_hue" in s for s in doc["steps"])


def test_builder_full_lens_when_envelope_has_lenses() -> None:
    env = json.loads(ENVELOPE.read_text(encoding="utf-8"))
    insight = json.loads(INSIGHT.read_text(encoding="utf-8"))
    proc = subprocess.run(
        [
            sys.executable,
            str(BUILDER),
            "--full-lens",
            "--active-step",
            "conflict",
            "--seed-query",
            "test query",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    out = ROOT / "docs/final/artifacts/magic_orb_reasoning_theatre_v1_latest.json"
    doc = json.loads(out.read_text(encoding="utf-8"))
    ids = [s["id"] for s in doc["steps"]]
    assert "lens_logos" in ids
    assert env.get("schema") == "three_lens_sphere_envelope_v1"
    assert insight.get("schema") == "magic_orb_question_insight_v1"


def test_example_fixture_matches_schema_ids() -> None:
    doc = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    assert doc["schema"] == "magic_orb_reasoning_theatre_v1"
    assert doc["hypothesis_tier"] == "B"
    step_ids = {s["id"] for s in doc["steps"]}
    assert doc["active_step_id"] in step_ids
    blob = json.dumps(doc, ensure_ascii=False)
    assert "Track A" not in blob


def test_mkmlife_lib_exports_builder() -> None:
    text = THEATRE_LIB.read_text(encoding="utf-8")
    assert "magic_orb_reasoning_theatre_v1" in text
    assert "buildReasoningTheatreFromSources" in text
    assert "REASONING_THEATRE_DISCLAIMER_KO" in text
    assert "latticePhaseToTheatreStep" in text


def test_sse_stream_route_and_event_schema() -> None:
    route = STREAM_ROUTE.read_text(encoding="utf-8")
    assert "text/event-stream" in route
    assert "magic_orb_reasoning_theatre_event_v1" in route
    assert "buildReasoningTheatreFromSources" in route
    event_doc = json.loads(EVENT_SCHEMA.read_text(encoding="utf-8"))
    assert event_doc["properties"]["schema"]["const"] == "magic_orb_reasoning_theatre_event_v1"
    audio = AUDIO_LIB.read_text(encoding="utf-8")
    assert "playReasoningTheatreStepTone" in audio
    assert "createStereoPanner" in audio


def test_orb_reasoning_theatre_ui_no_canvas_label() -> None:
    ui = ROOT / "projects/mkm/mkm-life/components/magic-orb/OrbReasoningTheatre.tsx"
    exp = ROOT / "projects/mkm/mkm-life/components/magic-orb/MagicOrbExperience.tsx"
    strip = ROOT / "projects/mkm/mkm-life/components/magic-orb/OracleSphereArtifactStrip.tsx"
    css = ROOT / "projects/mkm/mkm-life/app/globals.css"
    ui_text = ui.read_text(encoding="utf-8")
    exp_text = exp.read_text(encoding="utf-8")
    strip_text = strip.read_text(encoding="utf-8")
    css_text = css.read_text(encoding="utf-8")
    assert "fillText" not in ui_text
    assert "magic-orb-reasoning-theatre-caption" in exp_text
    assert "layerOpacity" in ui_text
    assert "OracleSphereArtifactStrip" in exp_text
    assert "magic-orb-artifact-strip" in strip_text
    assert "oracleSpherePhase" in exp_text
    assert "consumerLang === 'en'" in exp_text
    assert ".magic-orb-artifact-strip" in css_text
    assert "data-oracle-sphere-phase='ask'" in css_text


def test_personadiary_reasoning_theatre_parity() -> None:
    lib = PD_THEATRE_LIB.read_text(encoding="utf-8")
    ui = PD_THEATRE_UI.read_text(encoding="utf-8")
    ritual = ROOT / "projects/no1kmedi/src/components/personadiary/PersonadiaryRitualDraw.tsx"
    ritual_text = ritual.read_text(encoding="utf-8")
    assert "personadiaryPhaseToTheatreStep" in lib
    assert "fetchMkmlifeReasoningTheatreSteps" in lib
    assert "PD_REASONING_THEATRE_STEPS" in lib
    assert "PersonadiaryReasoningTheatre" in ui
    assert "fetchMkmlifeReasoningTheatreSteps" in ritual_text


def test_insight_payload_embeds_reasoning_theatre() -> None:
    insight = json.loads(INSIGHT.read_text(encoding="utf-8"))
    theatre = insight.get("reasoning_theatre_v1")
    if theatre is None:
        spec = importlib.util.spec_from_file_location(
            "build_magic_orb_question_insight_payload_v1",
            ROOT / "scripts/build_magic_orb_question_insight_payload_v1.py",
        )
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        bundle = {"schema": "semantic_rag_bridge_insight_bundle_v1", "rag_evidence": insight.get("rag_evidence") or []}
        rebuilt = mod.build_payload(
            query=str(insight.get("query") or "test"),
            query_id=str(insight.get("query_id") or "q01"),
            bundle=bundle,
            chain=None,
            router=None,
            graph_bloom=insight.get("graph_bloom"),
        )
        theatre = rebuilt.get("reasoning_theatre_v1")
    assert theatre and theatre.get("schema") == "magic_orb_reasoning_theatre_v1"
    assert len(theatre.get("steps") or []) >= 4


def test_smoke_stream_script_and_insight_route_embed() -> None:
    smoke = ROOT / "projects/mkm/mkm-life/scripts/smoke-magic-orb-reasoning-theatre-stream.mjs"
    insight_route = ROOT / "projects/mkm/mkm-life/app/api/v1/magic-orb/insight/route.ts"
    probe = ROOT / "scripts/probe_mkmlife_reasoning_theatre_v1.py"
    assert smoke.is_file()
    text = insight_route.read_text(encoding="utf-8")
    assert "reasoning_theatre_v1" in text
    assert "buildTheatreForInsight" in text
    assert (ROOT / "projects/mkm/mkm-life/lib/magic-orb-envelope-public-v1.ts").is_file()
    assert probe.is_file()
    assert "mkm_reasoning_theatre_probe_v1" in probe.read_text(encoding="utf-8")
    watch = ROOT / "projects/mkm/mkm-life/scripts/watch-reasoning-theatre-dev.mjs"
    invoke = ROOT / "scripts/Invoke-MkmlifeReasoningTheatreDevWatch_v1.ps1"
    assert watch.is_file()
    assert invoke.is_file()
    assert "smoke-magic-orb-reasoning-theatre-stream" in watch.read_text(encoding="utf-8")
