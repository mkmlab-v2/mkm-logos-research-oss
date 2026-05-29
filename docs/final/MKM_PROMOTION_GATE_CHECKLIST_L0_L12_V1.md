# MKM Promotion Gate Checklist — Track L (L0–L12) v1

**Track:** Logos Hermeneutics (Track L) · **Charter:** `docs/final/LOGOS_HERMENEUTICS_TRACK_L_CHARTER_V1.md`

Promotion is **evidence + exit code**, not narrative. Logos remains **`[NON_GATING]`** for market action through L12 unless a separate human contract says otherwise.

## L0 — Corpus + resolver (required for “Track L exists”)

| # | Gate | Command / path | Pass |
| --- | --- | --- | --- |
| L0-1 | Charter on disk | `docs/final/LOGOS_HERMENEUTICS_TRACK_L_CHARTER_V1.md` | file exists |
| L0-2 | Checklist on disk | `docs/final/MKM_PROMOTION_GATE_CHECKLIST_L0_L12_V1.md` | file exists |
| L0-3 | Corpus manifest | `docs/final/artifacts/logos_corpus_manifest_v1_latest.json` | `verse_count == 31102` |
| L0-4 | Resolver smoke | `py scripts/resolve_logos_verse_reference_v1.py "John 19:34"` | exit 0 · `primary_verse_id == Jhn.19.34` |
| L0-5 | Corpus row | `data/logos/verse_decoded_v2_single_anchor_v1.jsonl` | row `Jhn.19.34` present |
| L0-6 | Bundle | `py scripts/run_logos_track_l_l0_readiness_v1.py` | exit 0 · `l0_ok: true` |
| L0-7 | CI | `.github/workflows/logos-hermeneutics-l0-smoke.yml` | pytest green on PR/push |

**One-shot:** `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmPersonaHealth_v1.ps1 -Persona LogosTrackL0`

## L1 — Track B Logos pipeline readiness (pointer)

| # | Gate | Pointer |
| --- | --- | --- |
| L1-1 | Policy readiness | `scripts/report_logos_track_b_policy_readiness_v1.py` |
| L1-2 | Pipeline chain | `scripts/run_logos_track_b_pipeline_chain_v1.py --skip-distill` |
| L1-3 | CI smoke | `.github/workflows/logos-track-b-pipeline-smoke.yml` |

## L2 — Deterministic-before-ANN in RAG pilot

| # | Gate | Evidence |
| --- | --- | --- |
| L2-1 | Philosophy pilot emits `verse_reference_resolve` when query contains ref | `scripts/philosophy_lane_rag_pilot_v1.py` output JSON |
| L2-2 | Regression | `tests/test_resolve_logos_verse_reference_v1.py` |

## L3–L5 — GraphRAG / original-language bridge (research)

SSOT: `docs/final/LOGOS_ORIGINAL_LANGUAGE_GRAPH_RAG_BRIDGE_V1.md` · static bridges Phase 0. **No** arbitrary theology Q&A product claim until L5 evidence pack exists.

## L6–L8 — Shadow advisory · S1 review packet

Reuse Track B shadow path: `build_logos_s1_shadow_promotion_review_packet_v1.py` · human approval recorder — **Track L label** in packet metadata only; no A-track merge.

## L9–L12 — Human sign-off · external send

| # | Gate | Rule |
| --- | --- | --- |
| L12-1 | Public / B2B copy | `docs/final/PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md` |
| L12-2 | Track wall | `combined_all_passed` + explicit human — never from metaphor or ANN top-1 alone |

## Fail closed

- L0 fail → do not claim “Track L operational” in briefings.
- P0 path verify (`verify_p0_constitution_gate_paths.ps1`) proves **file existence**, not hermeneutic quality.
