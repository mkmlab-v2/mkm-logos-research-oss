# MKM AI API branding bridge (contract-preserving)

**Purpose:** Keep public-facing labels aligned with the token compression OpenAPI stub **without** changing request or response schemas.

**Contract SSOT:** `docs/final/openapi_token_compression_stub_v1.yaml`, implementation `scripts/compression_token_api_stub.py`.

**Rules:**

- Do not rename documented paths (`/v1/compress`, `/v1/expand`, `/v1/metering/log`, research routes) in marketing copy without matching OpenAPI revision.
- Research-only routes (`/v1/research/...`) must not be described as production SLA endpoints.

**Governance:** Fact-lock paths per `docs/final/P0_COMMERCIALIZATION_TRACKER.md` and `P1_COMPRESSION_API_PILOT_TRANSITION_CHECKLIST_V1.md`.
