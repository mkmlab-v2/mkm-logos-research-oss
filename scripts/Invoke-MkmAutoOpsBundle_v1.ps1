# Auto-ops: local RAG+compression gates || VPS RAG sync+smoke (B-track, no live trading).
param([switch]$RefreshSqlite)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$ts = Get-Date -Format 'yyyyMMdd_HHmmss'
$log = Join-Path $root "reports\mkm_auto_ops_bundle_${ts}.log"
$failed = [System.Collections.Generic.List[string]]::new()

function Invoke-Step([string]$Name, [scriptblock]$Block) {
    Write-Host "== $Name ==" -ForegroundColor Cyan
    $prev = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        & $Block 2>&1 | Tee-Object -FilePath $log -Append
    } finally {
        $ErrorActionPreference = $prev
    }
    if ($LASTEXITCODE -ne 0) {
        $failed.Add($Name) | Out-Null
        Write-Host "FAIL $Name exit $LASTEXITCODE" -ForegroundColor Red
    } else {
        Write-Host "OK $Name" -ForegroundColor Green
    }
}

Invoke-Step 'rag_full_auto' { py scripts/run_logos_rag_full_auto_v1.py --skip-pilots }
Invoke-Step 'compression_policy' { py scripts/run_compression_recommended_policy_chain_v1.py }
Invoke-Step 'compression_hardening' {
    py scripts/run_compression_hardening_milestone_chain_v1.py --skip-demo --skip-bench-smoke
}

Invoke-Step 'rag_bridge_gate' {
    py scripts/build_semantic_rag_bridge_insight_bundle_v1.py `
        --philosophy-pilot-json reports/constitution/btrack_pilot/philosophy_lane_rag_pilot_r6_merged_q01_q12_ko_only_latest.json `
        --calibration-kind none
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    py scripts/check_logos_rag_btrack_promotion_gate_v1.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    py scripts/build_logos_rag_promotion_review_packet_v1.py
}

Invoke-Step 'ms_fusion' { py scripts/build_ms_ma_jung_fusion_check_v1.py }

if ($RefreshSqlite) {
    Invoke-Step 'vps_l3_sqlite' {
        powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Sync-LogosRagL3ProdIndexToVps_v1.ps1
    }
}
Invoke-Step 'vps_json' {
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Sync-LogosRagVpsJsonBundle_v1.ps1
}
Invoke-Step 'vps_scripts' {
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Sync-LogosRagVpsQueryScripts_v1.ps1
}
Invoke-Step 'vps_smoke' {
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-LogosRagVpsRemoteQuerySmoke_v1.ps1
}

Invoke-Step 'checkpoint' {
    py scripts/athena_checkpoint.py "auto-ops RAG VPS+local gates $(Get-Date -Format 'yyyy-MM-dd HH:mm') UTC"
}

Write-Host "log: $log" -ForegroundColor Cyan
if ($failed.Count -gt 0) {
    Write-Host "FAILED: $($failed -join ', ')" -ForegroundColor Red
    exit 1
}
Write-Host 'AUTO-OPS OK' -ForegroundColor Green
exit 0
