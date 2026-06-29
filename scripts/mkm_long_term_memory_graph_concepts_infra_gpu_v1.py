"""Infra/GPU LTM graph concepts — venv isolation · Ollama · Lambda credits ([HYPO])."""

from __future__ import annotations

from mkm_long_term_memory_graph_lib_v1 import ConceptSpec, CoordinateSpec

INFRA_GPU_CONCEPT_SPECS: tuple[ConceptSpec, ...] = (
    ConceptSpec(
        concept_id="infra_en_tech_gpu_poc_venv",
        label_ko="en_tech GPU PoC venv · global py 금지",
        essence=(
            "GPU/ML·interpret·LoRA는 `.venv/en_tech_gpu_poc`만 — "
            "global `py` pip·NumPy2+구 TF 체인 금지; torch cu128 isolated"
        ),
        must_keep_tags=("en_tech_gpu_poc", "venv"),
        query_aliases=(
            "en_tech",
            "gpu poc",
            "venv",
            "torch",
            "peft",
            "interpret",
            "lora",
            "cuda",
            "5060",
        ),
        field_tags=("infra", "gpu", "venv", "en_tech", "training"),
        priority=9,
        coordinates=(
            CoordinateSpec(
                kind="json_pointer",
                file_path="reports/weekly_top5_queue_v1_latest.json",
                json_pointers=("/items/2/one_liner", "/items/2/lane"),
            ),
            CoordinateSpec(
                kind="markdown_anchor",
                file_path="MISSION_LOG.md",
                anchor_start="| **Infra/GPU** |",
                anchor_end="| **Clinic",
            ),
        ),
        related_concepts=("infra_solo_scheduler_stack", "infra_lambda_credits_hold_gate"),
        lane_hint="infra",
    ),
    ConceptSpec(
        concept_id="infra_ollama_qwen_local_default",
        label_ko="Ollama local default · qwen2.5-coder 24h",
        essence=(
            "로컬 코딩/도구 기본 `qwen2.5-coder:7b` — keep_alive 24h preload; "
            "gemma4:e2b는 shadow/light; models junction F:\\workspace_offload"
        ),
        must_keep_tags=("qwen2.5-coder", "7b"),
        query_aliases=(
            "ollama",
            "qwen",
            "qwen2.5-coder",
            "keep_alive",
            "preload",
            "local model",
            "gemma",
            "24h",
        ),
        field_tags=("infra", "ollama", "gpu", "local"),
        priority=8,
        coordinates=(
            CoordinateSpec(
                kind="json_pointer",
                file_path="reports/gemma4_12b_ondevice_smoke_hypo_v1_latest.json",
                json_pointers=("/ollama_registry_fact/installed_models_preserved",),
            ),
            CoordinateSpec(
                kind="markdown_anchor",
                file_path="docs/final/CENTRAL_AGENT_MEMORY_V1.md",
                anchor_start="<!-- ATHENA_CHECKPOINT_V1_START -->",
                anchor_end="<!-- ATHENA_CHECKPOINT_V1_END -->",
            ),
        ),
        related_concepts=("infra_en_tech_gpu_poc_venv",),
        lane_hint="infra",
    ),
    ConceptSpec(
        concept_id="infra_lambda_credits_hold_gate",
        label_ko="Lambda credits HOLD · burn 금지",
        essence=(
            "credits_status pending_partner_apply — no_gpu_spinup_until_credits_confirmed; "
            "P3 shard 0–3·merge deferred; SEND_GATE HOLD"
        ),
        must_keep_tags=("pending_partner_apply", "HOLD", "no_gpu_spinup"),
        query_aliases=(
            "lambda",
            "credits",
            "nvidia inception",
            "p3",
            "shard",
            "burn",
            "pending",
            "innovation lab",
        ),
        field_tags=("infra", "lambda", "gpu", "governance", "send_gate"),
        priority=9,
        coordinates=(
            CoordinateSpec(
                kind="json_pointer",
                file_path="reports/lambda_first_wire_policy_v1_latest.json",
                json_pointers=(
                    "/credits_status",
                    "/send_gate",
                    "/compute_policy",
                    "/forbidden",
                ),
            ),
        ),
        related_concepts=(
            "send_gate_hold_doctrine",
            "web_ops_regime_gate_nebius",
            "infra_en_tech_gpu_poc_venv",
        ),
        lane_hint="infra",
    ),
    ConceptSpec(
        concept_id="infra_integrity_guard_probe_regen",
        label_ko="integrity_guard · 16_STATE probe regen",
        essence=(
            "probe drift 시 myeongni_summary_gen → 16_STATE_MASTER_PROBE_v1.json 재생성 후 "
            "integrity_guard.py exit 0 — AthenaBundle integrity_guard gate"
        ),
        must_keep_tags=("checks_total", "all_pass"),
        query_aliases=(
            "integrity_guard",
            "master probe",
            "16 state",
            "probe regen",
            "149",
            "athenabundle",
            "myeongni_summary_gen",
        ),
        field_tags=("infra", "myeongni", "fact_lock", "governance"),
        priority=7,
        coordinates=(
            CoordinateSpec(
                kind="file_excerpt",
                file_path="scripts/integrity_guard.py",
                anchor_start="checks_total",
                anchor_end="Exit: 0 if all checks pass",
            ),
            CoordinateSpec(
                kind="file_excerpt",
                file_path="docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md",
                anchor_start="myeongni_summary_gen.py",
                anchor_end="회귀 `tests/test_emit_myeongni_weekly_ops_summary_v1.py`",
            ),
        ),
        related_concepts=("verify_p0_constitution_paths", "fact_lock_implementation"),
        lane_hint="infra",
    ),
)
