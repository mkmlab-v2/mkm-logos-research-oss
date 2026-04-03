# B-track Swarm sentiment metric (NotebookLM bundle)

**역할:** Hub B RAG용. A-track 실매매 트리거와 합선 금지. 로컬 SSOT는 동명 JSON·JSONL 파일 경로와 동일 내용.

---

## SWARM_SENTIMENT_METRIC_SCHEMA_DRAFT.json

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "B_Track_Swarm_Sentiment_Metric_v1",
  "type": "object",
  "description": "MiroFish 등 군집 지능 엔진의 텍스트 결과를 A-track 파이프라인이 소화할 수 있는 이산 수치로 정규화하는 데이터 계약 (B-track 전용; 본선 트리거 아님)",
  "properties": {
    "timestamp_utc": {
      "type": "string",
      "format": "date-time",
      "description": "스코어 추출 및 파일 생성 시각"
    },
    "seed_event_id": {
      "type": "string",
      "description": "자극이 된 뉴스/이벤트의 식별자 (예: ftx_bankruptcy_20221108)"
    },
    "seed_cutoff_time": {
      "type": "string",
      "format": "date-time",
      "description": "PIT(Point-in-Time) 보장을 위한 컷오프. 이 시각 이후의 데이터는 프롬프트에 포함 불가"
    },
    "metrics": {
      "type": "object",
      "properties": {
        "panic_ratio": { "type": "number", "minimum": 0.0, "maximum": 1.0 },
        "fomo_index": { "type": "number", "minimum": 0.0, "maximum": 1.0 },
        "consensus_strength": {
          "type": "number",
          "minimum": 0.0,
          "maximum": 1.0,
          "description": "방향성 일치도 (군중 분산의 역수)"
        }
      },
      "required": ["panic_ratio", "fomo_index", "consensus_strength"]
    },
    "simulation_meta": {
      "type": "object",
      "properties": {
        "engine_name": { "type": "string", "default": "MiroFish" },
        "agent_count": { "type": "integer" },
        "prompt_hash": {
          "type": "string",
          "description": "재현성을 위한 프롬프트 해시값"
        }
      }
    }
  },
  "required": ["timestamp_utc", "seed_event_id", "seed_cutoff_time", "metrics"]
}
```

---

## dummy_swarm_score.jsonl (line 1, wiring test)

```json
{"timestamp_utc": "2026-04-04T12:00:00+00:00", "seed_event_id": "wiring_test_lab_001", "seed_cutoff_time": "2026-04-04T11:00:00+00:00", "metrics": {"panic_ratio": 0.35, "fomo_index": 0.42, "consensus_strength": 0.58}, "simulation_meta": {"engine_name": "manual_dummy", "agent_count": 0, "prompt_hash": "sha256:0000000000000000000000000000000000000000000000000000000000000000"}}
```

**검증:** 로컬에서 `jsonschema` Draft7로 위 인스턴스 스키마 통과(exit 0).
