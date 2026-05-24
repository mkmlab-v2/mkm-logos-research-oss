# Daily mkmlab.space: CF zone finalize poll, DNS ensure, probe. Stops stressing when zone=active.
param(
    [int]$ActivationPolls = 3,
    [int]$PollSleepSec = 30,
    [switch]$SkipDnsEnsure
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$log = Join-Path $root "reports\mkmlab_space_daily_health_log.jsonl"

function Append-Log($obj) {
    $line = ($obj | ConvertTo-Json -Compress -Depth 8)
    Add-Content -LiteralPath $log -Value $line -Encoding UTF8
}

$started = (Get-Date).ToUniversalTime().ToString("o")
$exit = 0

try {
    & py (Join-Path $root "scripts\finalize_mkmlab_cloudflare_zone_v1.py") --polls $ActivationPolls --sleep-s $PollSleepSec
    if ($LASTEXITCODE -ne 0) { $exit = [Math]::Max($exit, $LASTEXITCODE) }
    $fin = Get-Content (Join-Path $root "reports\mkmlab_cloudflare_zone_finalize_latest.json") -Raw | ConvertFrom-Json

    if (-not $SkipDnsEnsure) {
        & py (Join-Path $root "scripts\ensure_mkmlab_space_cloudflare_dns_v1.py") --origin-ip 148.230.97.246 --zone-id 38a47f29983bd4ebce3798be08f59ba3
        if ($LASTEXITCODE -ne 0) { $exit = [Math]::Max($exit, $LASTEXITCODE) }
    }

    & py (Join-Path $root "scripts\probe_mkmlab_space_readiness_v1.py")
    if ($LASTEXITCODE -ne 0) { $exit = [Math]::Max($exit, $LASTEXITCODE) }
    $probe = Get-Content (Join-Path $root "reports\mkmlab_space_readiness_latest.json") -Raw | ConvertFrom-Json

    Append-Log @{
        schema = "mkmlab_space_daily_health_v1"
        at_utc = $started
        zone_status = $fin.zone_status
        http_all_ok = $probe.http_all_ok
        exit = $exit
    }

    if ($fin.zone_status -eq "active") {
        Write-Host "mkmlab CF zone active; edge settings applied. Task can be disabled." -ForegroundColor Green
    } else {
        Write-Host "mkmlab live (probe); CF zone still $($fin.zone_status) — NS OK, CF dashboard may need time." -ForegroundColor Yellow
    }
} catch {
    Append-Log @{ schema = "mkmlab_space_daily_health_v1"; at_utc = $started; error = $_.Exception.Message; exit = 1 }
    throw
}

exit $exit
