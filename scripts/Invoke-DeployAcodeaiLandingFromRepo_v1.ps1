#Requires -Version 5.1
<#
.SYNOPSIS
  Deploy a-codeai static landing + runtime JSON payloads to VPS (scp, no git on VPS required).

.EXAMPLE
  pwsh -NoProfile -File scripts/Invoke-DeployAcodeaiLandingFromRepo_v1.ps1
  pwsh -NoProfile -File scripts/Invoke-DeployAcodeaiLandingFromRepo_v1.ps1 -DryRun
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$WebRoot = "/var/www/a-codeai-next-preview",
    [switch]$DryRun,
    [switch]$SkipPayloadBuild,
    [switch]$SkipBindingCheck
)

$ErrorActionPreference = "Stop"
Set-Location $WorkspaceRoot

function Get-EnvAny([string]$name) {
    $v = [Environment]::GetEnvironmentVariable($name, "Process")
    if ($v) { return $v.Trim() }
    $v = [Environment]::GetEnvironmentVariable($name, "User")
    if ($v) { return $v.Trim() }
    return ""
}

$hostName = Get-EnvAny "MKM_VPS_HOST"
if (-not $hostName) { $hostName = "vps-mkmlife" }
# Live nginx root is a-codeai-next-preview (see sites-enabled/a-codeai.com on vps-mkmlife).
$user = Get-EnvAny "MKM_VPS_USER"
if (-not $user) { $user = "root" }
$remote = "${user}@${hostName}"

$scpArgs = @()
$sshArgs = @()
$extra = Get-EnvAny "MKM_VPS_SCP_EXTRA_ARGS"
if ($extra) {
    $scpArgs = $extra -split "\s+" | Where-Object { $_ }
    $sshArgs = $scpArgs
}

$nginx = Join-Path $WorkspaceRoot "scripts\deploy\nginx"
$art = Join-Path $WorkspaceRoot "docs\final\artifacts"

$need = @(
    (Join-Path $nginx "a-codeai.com.index.en.html.example"),
    (Join-Path $nginx "a-codeai.com.pilot.en.html.example"),
    (Join-Path $nginx "a-codeai.com.benchmark.en.html.example"),
    (Join-Path $nginx "a-codeai.com.index.html.example"),
    (Join-Path $nginx "a-codeai.com.pilot.html.example"),
    (Join-Path $nginx "a-codeai.com.benchmark.html.example"),
    (Join-Path $art "a_codeai_public_copy_web_payload_latest.json"),
    (Join-Path $art "a_codeai_public_bench_landing_payload_v1_latest.json")
)
foreach ($p in $need) {
    if (-not (Test-Path $p)) { throw "missing required file: $p" }
}

if (-not $SkipPayloadBuild) {
    & py (Join-Path $WorkspaceRoot "scripts\build_a_codeai_fact_lock_public_copy_v1.py")
    if ($LASTEXITCODE -ne 0) { throw "build_a_codeai_fact_lock_public_copy_v1 failed" }
    & py (Join-Path $WorkspaceRoot "scripts\build_a_codeai_public_copy_web_payload_v1.py")
    if ($LASTEXITCODE -ne 0) { throw "build_a_codeai_public_copy_web_payload_v1 failed" }
    & py (Join-Path $WorkspaceRoot "scripts\build_a_codeai_public_bench_landing_payload_v1.py")
    if ($LASTEXITCODE -ne 0) { throw "build_a_codeai_public_bench_landing_payload_v1 failed" }
}

$staging = Join-Path $env:TEMP "acodeai_landing_deploy_$(Get-Date -Format yyyyMMddHHmmss)"
New-Item -ItemType Directory -Force -Path $staging | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $staging "pilot") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $staging "benchmark") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $staging "ko\pilot") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $staging "ko\benchmark") | Out-Null

Copy-Item (Join-Path $nginx "a-codeai.com.index.en.html.example") (Join-Path $staging "index.html")
Copy-Item (Join-Path $nginx "a-codeai.com.pilot.en.html.example") (Join-Path $staging "pilot\index.html")
Copy-Item (Join-Path $nginx "a-codeai.com.benchmark.en.html.example") (Join-Path $staging "benchmark\index.html")
Copy-Item (Join-Path $nginx "a-codeai.com.index.html.example") (Join-Path $staging "ko\index.html")
Copy-Item (Join-Path $nginx "a-codeai.com.pilot.html.example") (Join-Path $staging "ko\pilot\index.html")
Copy-Item (Join-Path $nginx "a-codeai.com.benchmark.html.example") (Join-Path $staging "ko\benchmark\index.html")
Copy-Item (Join-Path $art "a_codeai_public_copy_web_payload_latest.json") $staging
Copy-Item (Join-Path $art "a_codeai_public_bench_landing_payload_v1_latest.json") $staging

Write-Host "[INFO] staging=$staging remote=$remote WEB_ROOT=$WebRoot"

if ($DryRun) {
    Write-Host "[dry-run] scp -r staging/* -> $WebRoot"
    exit 0
}

& ssh @($sshArgs + @($remote, "mkdir -p $WebRoot/pilot $WebRoot/benchmark $WebRoot/ko/pilot $WebRoot/ko/benchmark"))
if ($LASTEXITCODE -ne 0) { throw "ssh mkdir failed" }

& scp @($scpArgs + @("-r", "$staging/*", "${remote}:${WebRoot}/"))
if ($LASTEXITCODE -ne 0) { throw "scp failed" }

& ssh @($sshArgs + @($remote, "chown -R www-data:www-data $WebRoot && find $WebRoot -type d -exec chmod 755 {} \; && find $WebRoot -type f -exec chmod 644 {} \;"))
if ($LASTEXITCODE -ne 0) { throw "chown/chmod failed" }

Write-Host "[OK] a-codeai landing deploy completed." -ForegroundColor Green

if (-not $SkipBindingCheck) {
    function Test-BindingJson([string]$path) {
        if (-not (Test-Path $path)) { return $false }
        try {
            $doc = Get-Content $path -Raw -Encoding UTF8 | ConvertFrom-Json
            return [bool]$doc.all_ok
        } catch {
            return $false
        }
    }
    & py (Join-Path $WorkspaceRoot "scripts\check_a_codeai_public_binding_v1.py") | Out-Null
    $copyOk = Test-BindingJson (Join-Path $art "a_codeai_public_binding_check_latest.json")
    & py (Join-Path $WorkspaceRoot "scripts\check_a_codeai_open_bench_binding_v1.py") | Out-Null
    $benchOk = Test-BindingJson (Join-Path $art "a_codeai_open_bench_binding_check_latest.json")
    if (-not ($copyOk -and $benchOk)) {
        Write-Host "[WARN] binding check: copy=$copyOk bench=$benchOk (see artifacts/*binding_check_latest.json)" -ForegroundColor Yellow
        exit 1
    }
    Write-Host "[OK] copy + open-bench binding PASS" -ForegroundColor Green
}
