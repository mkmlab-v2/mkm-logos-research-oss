# Edge Encoder Spec Draft v1 — SKU-COORD client contract

**Status:** `[HYPO]` · `research_only` · `send_gate: HOLD` · `maturity: sdk_alpha`  
**Machine SSOT:** `docs/final/artifacts/edge_encoder_spec_v1_latest.json`  
**Coord wire schema:** `docs/final/schemas/edge_encoder_coord_wire_v1.schema.json`

## Purpose

User retains **original assets on the Edge** (PC / VPC / air-gap). MKM cloud receives only **`coord_wire`** + **`base_sha256`** — not bulk image bytes or unmasked customer logs. This is the **SKU-COORD** lane; it does **not** replace **SKU-MASK** (`active_kpi` ~47% universal bench).

## Client obligations (Edge Encoder)

| Rule | Requirement |
|------|-------------|
| Local retention | Original bytes stay on user device or licensed VPC cache |
| Pre-sync catalog | Client and peer share `base_asset_id` + `base_sha256` before wire send |
| Wire surface | Emit `coord_wire_minimal` JSON or `compact_coord_wire` only |
| Verify before send | Re-hash local base file; abort if SHA256 ≠ wire |

**Forbidden client uploads:** raw PNG/JPEG bytes, unmasked JSONL bulk, default-path base64 image payloads.

## Server obligations (control plane)

- Validate `coord_spec` version + `base_sha256` fingerprint  
- Meter token proxy on wire payload only  
- **Never** require original bulk to MKM SaaS (`original_bulk_to_mkm_saas: true` in forbidden set)

## On-wire payload (`coord_wire_minimal`)

Reference: `docs/final/artifacts/coord_wire_packet_example_v1_latest.json`

- `wire_mode`: `anatomy_overlay_coord_v1`  
- `base_sha256`: 64-char hex of licensed base asset  
- `coord_inject`: normalized points + layer metadata (~156 cl100k tok reference — not a global 99% claim)

## Deterministic sync gate (Phase 2 smoke)

**SKU-COORD coord wire**

```text
py scripts/check_edge_encoder_coord_wire_determinism_v1.py
```

Checks: JSON Schema · `parse_coord_wire_text` · compact roundtrip · fixture SHA256 match.

**SKU-MASK hybrid (`mkm_candidate_pool` · `public-open-web-v1`)**

```text
py scripts/check_edge_encoder_mask_hybrid_determinism_v1.py
```

Checks: duplicate `/v2/compress` fingerprint · hybrid router binding · cached packet expand stability (edge cache replay).

Wired into `scripts/run_rib55_coord_passive_audit_v1.py` as `edge_encoder_*` steps.

## Edge SDK CLI (sdk_alpha)

Local parser — **no original bulk upload**:

```text
py scripts/run_edge_encoder_sdk_cli_v1.py encode-manifest --entry-id pilot_ninth_rib_55deg_v0
py scripts/run_edge_encoder_sdk_cli_v1.py validate --entry-id pilot_ninth_rib_55deg_v0
py scripts/run_edge_encoder_sdk_cli_v1.py local-roundtrip --entry-id pilot_ninth_rib_55deg_v0
py scripts/run_edge_encoder_sdk_cli_v1.py smoke
```

## Air-gap PoC pack + offline bundle

```text
powershell -File scripts/Invoke-EdgeEncoderAirGapPoC_v1.ps1
py scripts/build_edge_encoder_air_gap_poc_pack_v1.py
py scripts/build_edge_encoder_air_gap_bundle_v1.py
py scripts/check_edge_encoder_air_gap_bundle_v1.py
```

Artifacts:
- `docs/final/artifacts/edge_encoder_air_gap_poc_pack_v1_latest.json` — `deployment_mode: air_gap_on_prem`
- `reports/edge_encoder_air_gap_bundle_v1_latest/` — local base + `wire/wire_only_export.json` (`original_bulk_sent: false`)

## FAIL-COMP-004

Do **not** merge coord wire token savings with Track A 47.5% headline, MASK pilot ROI, or LTM handoff 99% inject bench.

## Reproduce

```text
py scripts/build_coord_wire_packet_example_v1.py
py scripts/build_edge_encoder_spec_v1.py
py -m pytest tests/test_edge_encoder_spec_v1.py -q
```

**CONSTITUTION pointer:** `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` §1.2 Edge Encoder row.
