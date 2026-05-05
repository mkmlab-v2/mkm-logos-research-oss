# Chronicle Human Gate Manual Review Template v1

`chronicle_human_gate_manual_reviews_latest.jsonl`에 아래 JSON 한 줄을 append 하세요.

```json
{
  "schema": "chronicle_human_gate_manual_review_row_v1",
  "reviewed_at_utc": "YYYY-MM-DDTHH:MM:SSZ",
  "reviewed_recorded_at_utc": "YYYY-MM-DDTHH:MM:SSZ",
  "root_cause": "",
  "action_taken": "",
  "prevention_plan": ""
}
```

- `reviewed_recorded_at_utc`: `chronicle_human_gate_ledger_latest.jsonl`의 `recorded_at_utc` 값과 1:1 매칭
- 필수 3줄:
  - `root_cause` (원인)
  - `action_taken` (조치)
  - `prevention_plan` (재발방지)
