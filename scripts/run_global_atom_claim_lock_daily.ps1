param(
    [string]$WorkspaceRoot = "C:\workspace"
)

$ErrorActionPreference = "Stop"
Set-Location $WorkspaceRoot

py "scripts/check_global_atom_claim_lock_v1.py" --strict
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

py "scripts/check_global_atom_edge_claim_atom_set_v1.py" --strict
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

py "scripts/check_global_atom_corpus_profile_lock_v1.py" --strict
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

py "scripts/build_chronicle_history_news_signal_stub_v1.py"
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

py "scripts/evaluate_chronicle_history_news_signal_weekly_v1.py"
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

py "scripts/check_chronicle_history_news_weekly_alert_v1.py" --strict --strict-on critical
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

py "scripts/update_chronicle_human_gate_ledger_v1.py"
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

py "scripts/build_chronicle_human_gate_weekly_report_v1.py"
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

py "scripts/build_chronicle_threshold_switch_review_packet_v1.py"
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

py "scripts/build_global_atom_corpus_fact_brief_latest_v1.py"
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

py "scripts/build_domain_graph_ops_dashboard_summary_latest_v1.py"
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

py "scripts/update_global_atom_profile_approval_log_v1.py"
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

py "scripts/check_global_atom_daily_outputs_freshness_v1.py" --strict --max-age-hours 24
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

powershell -NoProfile -ExecutionPolicy Bypass -File "scripts/show_chronicle_ops_minicheck_v1.ps1" -WorkspaceRoot $WorkspaceRoot
exit $LASTEXITCODE
