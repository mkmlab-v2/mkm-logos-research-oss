param()

$ErrorActionPreference = "Stop"

py "c:\workspace\scripts\build_smartfarm_profile_comparison_report_v1.py" `
  --standard-json "c:\workspace\data\smartfarm_rda_extract_v1\out\smartfarm_gap_policy_daily_gate_v1_standard.json" `
  --aggressive-json "c:\workspace\data\smartfarm_rda_extract_v1\out\smartfarm_gap_policy_daily_gate_v1_aggressive.json" `
  --history-jsonl "c:\workspace\reports\smartfarm_profile_comparison_history_v1.jsonl" `
  --output-json "c:\workspace\data\smartfarm_rda_extract_v1\out\smartfarm_profile_comparison_report_latest.json" `
  --window-days 3

exit $LASTEXITCODE
