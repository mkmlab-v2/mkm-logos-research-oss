param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$SkipCompressionAlarm
)

$ErrorActionPreference = "Stop"

if ($SkipCompressionAlarm) {
    exit 0
}

$kpiPath = Join-Path $WorkspaceRoot "reports\constitution\btrack_pilot\ultra_compression_kpi_summary_latest.json"
$thrPath = Join-Path $WorkspaceRoot "docs\final\artifacts\compression_alarm_thresholds_v1.json"

$suppressKpi = [string]$env:MKM_WEBHOOK_SUPPRESS_COMPRESSION_KPI
if ($suppressKpi -match '^(1|true|yes|on)$') {
    Write-Host "[compression_kpi_alarm] SKIP: MKM_WEBHOOK_SUPPRESS_COMPRESSION_KPI=1" -ForegroundColor DarkGray
    exit 0
}

$webhook = $env:COMPRESSION_KPI_ALARM_WEBHOOK_URL
if ([string]::IsNullOrWhiteSpace($webhook)) {
    $webhook = $env:OPS_ALARM_WEBHOOK_URL
}
if ([string]::IsNullOrWhiteSpace($webhook)) {
    Write-Host "[compression_kpi_alarm] SKIP: no COMPRESSION_KPI_ALARM_WEBHOOK_URL or OPS_ALARM_WEBHOOK_URL" -ForegroundColor DarkGray
    exit 0
}

if (-not (Test-Path -LiteralPath $kpiPath)) {
    Write-Host "[compression_kpi_alarm] WARN: missing KPI file: $kpiPath" -ForegroundColor Yellow
    exit 0
}

$kpi = Get-Content -LiteralPath $kpiPath -Raw | ConvertFrom-Json
$active = $kpi.active_kpi
if ($null -eq $active) {
    Write-Host "[compression_kpi_alarm] WARN: active_kpi missing in KPI JSON" -ForegroundColor Yellow
    exit 0
}

$thr = $null
if (Test-Path -LiteralPath $thrPath) {
    $thr = Get-Content -LiteralPath $thrPath -Raw | ConvertFrom-Json
}

function Get-DefaultThresholds {
    return @{
        min_avg_reconstruction_fidelity_jaccard = 0.4
        min_global_token_saving_rate            = $null
        min_avg_sensitive_integrity             = 0.8
        bench_saving_floor_min                  = 0.47
        alarm_if_jaccard_guardrail_false        = $true
        alarm_if_sensitive_integrity_ok_false   = $false
        alarm_if_go_no_go_no_go                 = $false
        alarm_if_bench_saving_floor_false       = $true
    }
}

$defaults = Get-DefaultThresholds
$reasons = New-Object System.Collections.Generic.List[string]

function Thr-Num($name) {
    if ($null -eq $thr) { return $defaults[$name] }
    if ($thr.PSObject.Properties.Name -contains $name) { return $thr.$name }
    return $defaults[$name]
}

function Thr-Bool($name) {
    if ($null -eq $thr) { return $defaults[$name] }
    if ($thr.PSObject.Properties.Name -contains $name) { return [bool]$thr.$name }
    return $defaults[$name]
}

$minJac = Thr-Num "min_avg_reconstruction_fidelity_jaccard"
if ($null -ne $minJac) {
    $v = [double]$active.avg_reconstruction_fidelity_jaccard
    if ($v -lt [double]$minJac) {
        [void]$reasons.Add("avg_reconstruction_fidelity_jaccard=$v < min=$minJac")
    }
}

$minSave = Thr-Num "min_global_token_saving_rate"
if ($null -ne $minSave) {
    $v = [double]$active.global_token_saving_rate
    if ($v -lt [double]$minSave) {
        [void]$reasons.Add("global_token_saving_rate=$v < min=$minSave")
    }
}

$minInt = Thr-Num "min_avg_sensitive_integrity"
if ($null -ne $minInt) {
    $v = [double]$active.avg_sensitive_integrity
    if ($v -lt [double]$minInt) {
        [void]$reasons.Add("avg_sensitive_integrity=$v < min=$minInt")
    }
}

if (Thr-Bool "alarm_if_jaccard_guardrail_false") {
    if (-not [bool]$active.jaccard_guardrail_ok) {
        [void]$reasons.Add("jaccard_guardrail_ok=false")
    }
}

if (Thr-Bool "alarm_if_sensitive_integrity_ok_false") {
    if ($active.PSObject.Properties.Name -contains "sensitive_integrity_ok") {
        if (-not [bool]$active.sensitive_integrity_ok) {
            [void]$reasons.Add("sensitive_integrity_ok=false")
        }
    }
}

if (Thr-Bool "alarm_if_go_no_go_no_go") {
    $d = $kpi.decision
    if ($null -ne $d -and $d.go_no_go -eq "NO_GO") {
        [void]$reasons.Add("decision.go_no_go=NO_GO")
    }
}

if (Thr-Bool "alarm_if_bench_saving_floor_false") {
    if ($active.PSObject.Properties.Name -contains "bench_saving_floor_ok") {
        if (-not [bool]$active.bench_saving_floor_ok) {
            $floorMin = Thr-Num "bench_saving_floor_min"
            [void]$reasons.Add("bench_saving_floor_ok=false (RQ-016 floor=$floorMin)")
        }
    }
}

if ($reasons.Count -eq 0) {
    Write-Host "[compression_kpi_alarm] OK: within thresholds" -ForegroundColor Green
    exit 0
}

$sensOk = $null
if ($active.PSObject.Properties.Name -contains "sensitive_integrity_ok") {
    $sensOk = $active.sensitive_integrity_ok
}

$payload = [ordered]@{
    event          = "compression_kpi_alarm"
    ts_utc         = (Get-Date).ToUniversalTime().ToString("o")
    reasons        = @($reasons)
    kpi_path       = $kpiPath
    threshold_path = $thrPath
    active_kpi     = @{
        global_token_saving_rate            = $active.global_token_saving_rate
        avg_reconstruction_fidelity_jaccard = $active.avg_reconstruction_fidelity_jaccard
        avg_sensitive_integrity             = $active.avg_sensitive_integrity
        jaccard_guardrail_ok                = $active.jaccard_guardrail_ok
        sensitive_integrity_ok              = $sensOk
    }
}

$json = $payload | ConvertTo-Json -Depth 8 -Compress
try {
    $null = Invoke-RestMethod -Uri $webhook -Method Post -Body $json -ContentType "application/json; charset=utf-8" -TimeoutSec 30
    Write-Host "[compression_kpi_alarm] SENT: $($reasons.Count) reason(s)" -ForegroundColor Yellow
}
catch {
    Write-Host "[compression_kpi_alarm] FAIL: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

exit 0
