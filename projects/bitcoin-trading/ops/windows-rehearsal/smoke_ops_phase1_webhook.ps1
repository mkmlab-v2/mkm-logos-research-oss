$ErrorActionPreference = "Stop"

function Get-EnvAny([string]$name) {
    foreach ($scope in @("Process", "User", "Machine")) {
        $v = [Environment]::GetEnvironmentVariable($name, $scope)
        if (-not [string]::IsNullOrWhiteSpace($v)) { return $v }
    }
    return $null
}

$url = Get-EnvAny "OPS_ALARM_WEBHOOK_URL"
if ([string]::IsNullOrWhiteSpace($url)) {
    Write-Host "[smoke] SKIP: OPS_ALARM_WEBHOOK_URL not set (run sync_required_env_to_user.ps1 or set User env)."
    exit 0
}

$bodyObj = [ordered]@{
    event   = "ops_phase1_chain"
    kind    = "smoke_test"
    message = "manual or CI smoke; no chain failure"
    report_path = "C:\workspace\projects\bitcoin-trading\memory\v2\ops\ops_phase1_chain_report_latest.json"
    ts_utc  = [DateTimeOffset]::UtcNow.ToString("o")
}
$json = $bodyObj | ConvertTo-Json -Compress -Depth 5
try {
    Invoke-RestMethod -Uri $url -Method Post -Body $json -ContentType "application/json; charset=utf-8" -TimeoutSec 30
    Write-Host "[smoke] OK: POST sent to OPS_ALARM_WEBHOOK_URL"
    exit 0
}
catch {
    Write-Host ("[smoke] FAIL: {0}" -f $_.Exception.Message) -ForegroundColor Red
    exit 1
}
