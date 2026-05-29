# Logos Hermeneutics — Track L Charter v1

**Status:** L0 package (2026-05-29) · **not** Track A compression ops · **not** live trading / prophecy trigger.

## Role

| Rail | Role |
| --- | --- |
| **Track A** | Frozen compression bench · MS paste · operational KPI |
| **Track B** | General R&D · `[HYPO]` · multilens / prophecy research |
| **Track C** | Commercial / B2B / showroom |
| **Track L** | **Logos-primary hermeneutics** — corpus integrity, verse ID contract, deterministic reference resolution, GraphRAG / ANN as **secondary** retrieval |

Track L has **organizational parity** with A/B/C (own charter, L0–L12 gates, dedicated CI smoke). It does **not** replace the Logos lens in the 3-lens stack; that lens stays **`[NON_GATING]`** per workspace lens contract.

## `track_wall` (mandatory)

- No auto-merge into Track A `MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json` or compression KPI claims.
- No auto-merge into live trading, `regime_map` triggers, or prophecy promotion without human sign-off.
- ANN semantic hits (e.g. `philosophy_lane_rag_pilot_v1.py`) remain **Track B pilot** unless explicitly labeled Track L and still `research_only`.

## Verse ID contract (Fact-Lock)

- Canonical IDs: `Book.chapter.verse` (e.g. `Jhn.19.34`, `1John.5.6`, `Mark.1.1`).
- Gospel of John = **`Jhn.*`**, not `John.*` (ingest: `scripts/ingest_logos_gap_original_text_v1.py` → `Jn` → `Jhn`).
- Corpus SSOT: `data/logos/verse_decoded_v2_single_anchor_v1.jsonl` · manifest `docs/final/artifacts/logos_corpus_manifest_v1_latest.json` (**31,102** verses).

## L0 entrypoints

| Artifact | Path |
| --- | --- |
| Verse resolver | `scripts/resolve_logos_verse_reference_v1.py` |
| L0 readiness | `scripts/run_logos_track_l_l0_readiness_v1.py` |
| Promotion gates | `docs/final/MKM_PROMOTION_GATE_CHECKLIST_L0_L12_V1.md` |
| L0 report | `docs/final/artifacts/logos_track_l_l0_readiness_v1_latest.json` |
| CI | `.github/workflows/logos-hermeneutics-l0-smoke.yml` |
| Persona (optional) | `Invoke-MkmPersonaHealth_v1.ps1 -Persona LogosTrackL0` |

## Reuse (Track B Logos pipeline)

Track L **builds on** existing Track B infrastructure without renaming it:

- `scripts/run_logos_track_b_pipeline_chain_v1.py` · `.github/workflows/logos-track-b-pipeline-smoke.yml`
- ANN lite: `reports/constitution/btrack_pilot/logos_vector_index_ann_lite_st_u_v1.sqlite`

Track B chain remains the **vector / distill** lane; Track L adds **deterministic verse routing** before semantic ANN.

## Known quality notes

- `Jhn.19.32`–`Jhn.19.34` may share duplicate paragraph text in ingest (versification QA; separate fix).
- RAG pilot missing `John 19:34` was a **routing** issue, not corpus absence — use resolver first.
