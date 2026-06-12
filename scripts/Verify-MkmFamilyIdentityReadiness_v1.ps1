<#
.SYNOPSIS
  MKM Family identity readiness: gate, pytest, DPAPI keys, optional live smoke.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Verify-MkmFamilyIdentityReadiness_v1.ps1
.EXAMPLE
  powershell … -IncludeLiveSmoke
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$IncludeLiveSmoke
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path $WorkspaceRoot).Path
$issues = @()

function Step([string]$name, [scriptblock]$block) {
    Write-Host "==> $name" -ForegroundColor Cyan
    & $block
    if ($LASTEXITCODE -ne 0) {
        $script:issues += "$name exit $LASTEXITCODE"
    }
}

Step "check_mkm_family_identity_v1" {
    py (Join-Path $root "scripts\check_mkm_family_identity_v1.py")
}

Step "pytest mkm_family" {
    py -m pytest (Join-Path $root "tests\test_mkm_family_identity_v1.py") -q
}

$storeScript = Join-Path $root "scripts\Invoke-EncryptedSecretStore.ps1"
$dpapiKeys = @("MKM_FAMILY_AUTH_SECRET", "GOOGLE_OAUTH_CLIENT_ID", "GOOGLE_OAUTH_CLIENT_SECRET")
$present = 0
foreach ($k in $dpapiKeys) {
    $out = & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $storeScript -Action get -Key $k -AsPlainText 2>$null
    if ($LASTEXITCODE -eq 0 -and -not [string]::IsNullOrWhiteSpace(($out | Out-String).Trim())) {
        $present++
        Write-Host "[dpapi] $k present" -ForegroundColor Green
    }
    else {
        Write-Host "[dpapi] $k missing" -ForegroundColor Yellow
    }
}
if ($present -lt 3) {
    $issues += "dpapi_keys_incomplete ($present/3)"
}

$envLocal = Join-Path $root "projects\no1kmedi\.env.local"
if (Test-Path $envLocal) {
    Write-Host "[local] .env.local exists" -ForegroundColor Green
}
else {
    Write-Host "[local] .env.local missing — run Invoke-ApplyMkmFamilyGoogleOAuthFromDpapi_v1.ps1" -ForegroundColor Yellow
}

if ($IncludeLiveSmoke) {
    Step "smoke_mkm_family_identity_live_v1" {
        py (Join-Path $root "scripts\smoke_mkm_family_identity_live_v1.py")
    }
}

if ($issues.Count -gt 0) {
    Write-Host "READINESS: FAIL — $($issues -join '; ')" -ForegroundColor Red
    exit 1
}
Write-Host "READINESS: OK" -ForegroundColor Green
exit 0
