# D-8 push: ordered waves with in-wave parallelism (Hostinger VPS + Cloudflare SSOT)
# Wave A: North Star (fabric+DECOY+mkmlife) || RAG weekly || prophecy sweep
# Wave B: topology + gates + P0 path smoke
# Does NOT: O-P5 SSH (human), PayApp/live trading, LO-CG reopen
param(
    [switch]$SkipRag,
    [switch]$SkipProphecy,
    [switch]$SkipNorthStar,
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$logDir = Join-Path $Root 'reports'
$logDir | Out-Null
$ts = Get-Date -Format 'yyyyMMdd_HHmmss'
$summaryPath = Join-Path $logDir "mkm_d8_parallel_push_${ts}.json"

function Invoke-Step([string]$Name, [string]$Cmd, [string]$LogPath) {
    Write-Host "== $Name ==" -ForegroundColor Cyan
    if ($DryRun) {
        Write-Host "DRYRUN: $Cmd" -ForegroundColor Yellow
        return @{ name = $Name; exit_code = 0; dry_run = $true }
    }
    $prev = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        Invoke-Expression $Cmd 2>&1 | Tee-Object -FilePath $LogPath | Out-Null
        $code = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $prev
    }
    if ($code -ne 0) { Write-Host "FAIL $Name exit $code (log: $LogPath)" -ForegroundColor Red }
    else { Write-Host "OK $Name" -ForegroundColor Green }
    , @{ name = $Name; exit_code = $code; log = $LogPath }
}

$waveA = @()
if (-not $SkipNorthStar) {
    $waveA += @{
        Name = 'north_star_final_ops'
        Cmd  = 'powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-MkmFinalParallelOps_v1.ps1 -SkipMsPasteWarn'
    }
}
if (-not $SkipRag) {
    $waveA += @{
        Name = 'rag_full_auto_skip_pilots'
        Cmd  = 'py scripts/run_logos_rag_full_auto_v1.py --skip-pilots'
    }
}
if (-not $SkipProphecy) {
    $waveA += @{
        Name = 'prophecy_recommended_sweep'
        Cmd  = 'powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Run-BtrackRecommendedEvalAutoSweep_v1.ps1'
    }
}

$results = @()
$jobs = @()
foreach ($step in $waveA) {
    $log = Join-Path $logDir "$($step.Name)_$ts.log"
    if ($DryRun) {
        $results += Invoke-Step $step.Name $step.Cmd $log
        continue
    }
    $sb = {
        param($c, $r, $lp)
        Set-Location $r
        Invoke-Expression $c 2>&1 | Out-File -FilePath $lp -Encoding utf8
        return $LASTEXITCODE
    }
    $jobs += @{
        Name = $step.Name
        Job  = Start-Job -ScriptBlock $sb -ArgumentList $step.Cmd, $Root, $log
        Log  = $log
    }
    Write-Host "started job: $($step.Name)" -ForegroundColor DarkCyan
}

foreach ($j in $jobs) {
    Wait-Job $j.Job | Out-Null
    $code = Receive-Job $j.Job
    if ($null -eq $code) { $code = if ((Get-Job -Id $j.Job.Id).State -eq 'Completed') { 0 } else { 1 } }
    Remove-Job $j.Job -Force
    $results += @{ name = $j.Name; exit_code = [int]$code; log = $j.Log }
}

Write-Host "`n== Wave B (serial) ==" -ForegroundColor Magenta
$serial = @(
    @{ Name = 'infra_topology'; Cmd = 'py scripts/check_mkm_hostinger_cloudflare_topology_v1.py' },
    @{ Name = 'rag_gate'; Cmd = 'py scripts/check_logos_rag_btrack_promotion_gate_v1.py' },
    @{ Name = 'p0_paths'; Cmd = 'powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify_p0_constitution_gate_paths.ps1' }
)
foreach ($s in $serial) {
    $log = Join-Path $logDir "$($s.Name)_$ts.log"
    $results += @(Invoke-Step $s.Name $s.Cmd $log)
}

$stepRows = @($results | Where-Object { $_ -is [hashtable] -and $null -ne $_.exit_code })
$failed = @($stepRows | Where-Object { $_.exit_code -ne 0 } | ForEach-Object { $_.name })
$doc = @{
    schema = 'mkm_d8_parallel_push_v1'
    ts_utc = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    ok     = ($failed.Count -eq 0)
    failed = $failed
    steps  = $stepRows
    human_remainder = @(
        'O-P5: jema12 nginx /studio -> v5 (SSH, Cloudflare DNS only)'
        'VPS ST query smoke: query_logos_vector_index_ann_lite_v1.py + sentence-transformer model on Hostinger'
    )
    topology_ssot = 'docs/final/MKM_HOSTINGER_CLOUDFLARE_TOPOLOGY_V1.md'
}
$doc | ConvertTo-Json -Depth 6 | Set-Content -Path $summaryPath -Encoding utf8
Write-Host "`nSummary: $summaryPath" -ForegroundColor Cyan
if ($failed.Count -gt 0) {
    Write-Host "FAILED: $($failed -join ', ')" -ForegroundColor Red
    exit 1
}
Write-Host 'D-8 parallel push OK' -ForegroundColor Green
exit 0
