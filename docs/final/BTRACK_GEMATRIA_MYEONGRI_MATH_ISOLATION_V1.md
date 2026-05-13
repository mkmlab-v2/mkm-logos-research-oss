# B-track: Gematria–Myeongri deterministic math isolation (v1)

**Purpose:** Keep **convex blend + L2/cosine geometry** on `(S,L,K,M)` in a single versioned module with **no LLM, no LoRA training loop, no trading hooks**.

**SSOT module:** `tools/myeongni/gematria_myeongri_math_v1.py` — `MATH_MODULE_ID` / `MATH_MODULE_VERSION`, `blend_convex_renorm`, `geometric_metrics`, etc.

**Orchestration (upstream vectors):** `scripts/spike_gematria_myeongri_blend_v0.py` — builds gematria bridge + `MyeongriCompleteFusion` 4D, then calls the math module; artifact `docs/final/artifacts/gematria_myeongri_spike_blend_latest.json` remains B-track / `[HYPO]` by domain policy, not by non-determinism of the geometry layer.

**Regression:** `tests/test_gematria_myeongri_math_v1.py` (pure), `tests/test_gematria_myeongri_spike_smoke.py` (CLI).

**Fact-Lock:** `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` 명리 표의 게마트리아+명리 스파이크 행.

**Boundary:** Interpretation, narrative fusion, and A-track promotion stay **out of** this module; extend via new callers or new artifact schemas, not by growing LoRA into geometry code.
