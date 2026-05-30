# CF deploy token readiness — secret template, probe, readiness JSON (no token creation).
param(
    [switch]$OpenDashboard,
    [switch]$ApplyIfPresent
)

$ErrorActionPreference = "Stop"
Set-Location "C:\workspace"

$template = "reports\cloudflare_mkmlife_deploy_token_secret_LOCAL.template.json"
$secret = "reports\cloudflare_mkmlife_deploy_token_secret_LOCAL.json"
$out = "reports\mkmlife_cf_deploy_token_readiness_v1_latest.json"

if (-not (Test-Path -LiteralPath $secret) -and (Test-Path -LiteralPath $template)) {
    Copy-Item -LiteralPath $template -Destination $secret -Force
    Write-Host "[readiness] created $secret from template — paste Workers+KV token then re-run with -ApplyIfPresent" -ForegroundColor Yellow
}

$hasSecret = $false
$tokenPlaceholder = $true
if (Test-Path -LiteralPath $secret) {
    $raw = Get-Content -LiteralPath $secret -Raw -Encoding UTF8
    $hasSecret = $true
    $tokenPlaceholder = $raw -match "PASTE_CF_TOKEN_HERE"
}

$probeOk = $null
$probeExit = $null
$probeDetail = $null
if ($ApplyIfPresent -and $hasSecret -and -not $tokenPlaceholder) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-ApplyMkmlifeCfDeployTokenFromSecret_v1.ps1
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if ($hasSecret -and -not $tokenPlaceholder) {
    $probeOut = & py scripts\_probe_cf_mkmlife_deploy_token_v1.py 2>&1 | Out-String
    $probeExit = $LASTEXITCODE
    $probeOk = ($probeExit -eq 0 -or $probeExit -eq 2)
    $probeDetail = $probeOut.Trim()
}

$ready = [bool]($hasSecret -and -not $tokenPlaceholder -and $probeOk)

$workersRoutesOk = $null
if ($hasSecret -and -not $tokenPlaceholder -and $probeDetail) {
    if ($probeDetail -match "workers_routes_list: http=\d+ success=True") {
        $workersRoutesOk = $true
    } elseif ($probeDetail -match "workers_routes_list:") {
        $workersRoutesOk = $false
    }
}

$doc = @{
    schema = "mkmlife_cf_deploy_token_readiness_v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    secret_path = $secret
    secret_exists = $hasSecret
    token_placeholder = $tokenPlaceholder
    workers_kv_probe_ok = $probeOk
    workers_routes_probe_ok = $workersRoutesOk
    deploy_token_ready = $ready
    deploy_token_routes_ready = [bool]($probeExit -eq 0)
    oauth_fallback_ok = $true
    notes_ko = "Workers Scripts+KV (account) + Workers Routes+Zone Read (mkmlife zone); no-routes wrangler fallback if routes scope missing"
}
$doc | ConvertTo-Json -Depth 6 | Set-Content -Path $out -Encoding UTF8

if ($OpenDashboard -and -not $ready) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Open-MkmlifeCloudflareDeployTokenTemplate_v1.ps1
}

if ($ready) {
    if ($workersRoutesOk -eq $false) {
        Write-Host "[OK] deploy token ready (Worker+KV) — default deploy skips wrangler routes sync (no auth warning)" -ForegroundColor Green
        Write-Host "     optional full routes sync: add Workers Routes Edit + MKM_MKMLIFE_WRANGLER_SYNC_ROUTES=1" -ForegroundColor DarkGray
        Write-Host "     repair: powershell -File scripts\Invoke-RepairMkmlifeCfDeployToken_v1.ps1" -ForegroundColor DarkGray
    } else {
        Write-Host "[OK] deploy token ready (incl. Workers Routes) -> $out" -ForegroundColor Green
    }
    exit 0
}

Write-Host "[INFO] deploy token not ready (OAuth still works) -> $out" -ForegroundColor Cyan
exit 0
