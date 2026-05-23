#Requires -Version 5.1
<#
.SYNOPSIS
  Read-only VPS PM2 preflight for no1kmedi / mkmlife (no deploy, no git push).

.DESCRIPTION
  SSH → pm2 describe + path probes. Parses exec cwd into structured pm2_facts.
  SSOT: docs/final/NO1KMEDI_MKMLIFE_REPO_PATH_SSOT_2026-04-08.md
  Deploy (tarball): /opt/mkm-destiny-ai-41e38ec6/projects/no1kmedi

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-No1kmediVpsPm2Preflight_v1.ps1
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$OutJson = "",
    [switch]$Strict
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($OutJson)) {
    $OutJson = Join-Path $WorkspaceRoot "reports\no1kmedi_vps_pm2_preflight_latest.json"
}

function Get-EnvAny([string]$name) {
    $v = [Environment]::GetEnvironmentVariable($name, "Process")
    if ($v) { return $v.Trim() }
    $v = [Environment]::GetEnvironmentVariable($name, "User")
    if ($v) { return $v.Trim() }
    return ""
}

function Resolve-SshKeyPath([string]$Root) {
    foreach ($p in @((Get-EnvAny "MKM_VPS_SSH_KEY_PATH"), (Get-EnvAny "SSH_KEY_PATH"))) {
        if ($p -and (Test-Path -LiteralPath $p)) { return $p }
    }
    foreach ($c in @(
            (Join-Path $Root ".ssh\hostinger_mkmlife"),
            (Join-Path $env:USERPROFILE ".ssh\hostinger_mkmlife")
        )) {
        if (Test-Path -LiteralPath $c) { return $c }
    }
    return $null
}

function Read-TextHead([string]$path, [int]$maxBytes = 16384) {
    if (-not (Test-Path -LiteralPath $path)) { return "" }
    $fs = [System.IO.File]::OpenRead($path)
    try {
        $buf = New-Object byte[] $maxBytes
        $n = $fs.Read($buf, 0, $maxBytes)
        [System.Text.Encoding]::UTF8.GetString($buf, 0, $n)
    }
    finally {
        $fs.Dispose()
    }
}

function Parse-Pm2ExecCwd([string]$text, [string]$processName) {
    $block = $null
    if ($text -match "(?s)=== PM2 $([regex]::Escape($processName)) ===(.+?)(?:=== PM2 |=== PATH PROBE ===|$)") {
        $block = $Matches[1]
    }
    if (-not $block) {
        return @{ name = $processName; found = $false }
    }
    $facts = @{ name = $processName; found = ($block -notmatch "MISSING:") }
    if ($block -match "status[^\n]*?\b(online|stopped|errored|launching)\b") {
        $facts.status = $Matches[1]
    }
    if ($block -match "exec cwd[^\n]*?(/opt/[^\s│\|]+|/var/[^\s│\|]+)") {
        $facts.exec_cwd = $Matches[1].Trim()
    }
    if ($block -match "script path[^\n]*?(/[^\s│\|]+)") {
        $facts.script_path = $Matches[1].Trim()
    }
    if ($block -match "script args[^\n]*?[│\|]\s*([^│\|\r\n]+)") {
        $facts.script_args = $Matches[1].Trim()
    }
    if ($block -match "restarts[^\n]*?[│\|]\s*(\d+)") {
        $facts.restarts = $Matches[1].Trim()
    }
    if ($block -match "uptime[^\n]*?[│\|]\s*([^│\|\r\n]+)") {
        $facts.uptime = $Matches[1].Trim()
    }
    return $facts
}

$hostAddr = Get-EnvAny "MKM_VPS_HOST"
if (-not $hostAddr) { $hostAddr = "vps-mkmlife" }
$user = Get-EnvAny "MKM_VPS_USER"
if (-not $user) { $user = "root" }
$keyPath = Resolve-SshKeyPath -Root $WorkspaceRoot

$remoteScript = @'
echo "=== PATH PROBE ==="
for p in /opt/no1kmedi-com/.next/standalone /opt/mkm-destiny-ai-41e38ec6/projects/no1kmedi /var/www/mkmlife_runtime/mkm-life; do
  if [ -d "$p" ]; then echo "EXISTS $p"; else echo "ABSENT $p"; fi
done
echo "=== PM2 no1kmedi-com ==="
pm2 describe no1kmedi-com 2>/dev/null | sed -n '1,22p' || echo "MISSING: no1kmedi-com"
echo "=== PM2 no1kmedi-payapp-api ==="
pm2 describe no1kmedi-payapp-api 2>/dev/null | sed -n '1,22p' || echo "MISSING: no1kmedi-payapp-api"
echo "=== PM2 mkmlife ==="
pm2 describe mkmlife 2>/dev/null | sed -n '1,22p' || echo "MISSING: mkmlife"
echo "=== CURL LOCAL API 127.0.0.1 ==="
curl -sS -m 5 http://127.0.0.1:3847/health 2>/dev/null | head -c 200 || echo "curl_3847_failed"
echo "=== NGINX ==="
nginx -t 2>&1 | tail -n 2 || echo "nginx_t_failed"
echo "=== LOCAL NEXT 3010 ==="
curl -sS -m 5 -o /dev/null -w "LOCAL_3010_HTTP_CODE=%{http_code}\n" http://127.0.0.1:3010/ || echo "LOCAL_3010_FAIL"
'@ -replace "`r`n", "`n"

$payload = [ordered]@{
    schema               = "no1kmedi_vps_pm2_preflight_v1"
    generated_at_utc     = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    deploy_triggered     = $false
    git_push             = $false
    host                 = $hostAddr
    user                 = $user
    key_resolved         = [bool]$keyPath
    skipped              = $false
    skip_reason          = $null
    ssh_success          = $false
    ssh_returncode       = $null
    stdout_excerpt       = $null
    stderr_excerpt       = $null
    pm2_facts            = @{}
    path_probe           = @{}
    origin_probe         = @{}
    ssot_reconciliation  = @{}
    ssot_pm2_paths       = @{
        no1kmedi_com_doc     = "/opt/no1kmedi-com/.next/standalone"
        no1kmedi_tarball     = "/opt/mkm-destiny-ai-41e38ec6/projects/no1kmedi"
        mkmlife              = "/var/www/mkmlife_runtime/mkm-life"
    }
    deploy_script        = "scripts/Deploy-No1kmediDestinyTarball_v1.ps1"
}

if (-not $keyPath) {
    $payload.skipped = $true
    $payload.skip_reason = "no_ssh_key"
}
elseif (-not (Get-Command ssh.exe -ErrorAction SilentlyContinue)) {
    $payload.skipped = $true
    $payload.skip_reason = "ssh.exe not on PATH"
}
else {
    $outFile = [System.IO.Path]::GetTempFileName()
    $errFile = [System.IO.Path]::GetTempFileName()
    try {
        $argList = @(
            "-i", $keyPath,
            "-o", "BatchMode=yes",
            "-o", "StrictHostKeyChecking=no",
            "-o", "ConnectTimeout=20",
            "-o", "UserKnownHostsFile=NUL",
            "${user}@${hostAddr}",
            $remoteScript
        )
        $proc = Start-Process -FilePath "ssh.exe" -ArgumentList $argList -Wait -PassThru -NoNewWindow `
            -RedirectStandardOutput $outFile -RedirectStandardError $errFile
        $out = [string](Read-TextHead $outFile 20000)
        $err = [string](Read-TextHead $errFile 2000)
        $payload.ssh_returncode = $proc.ExitCode
        $hasPm2 = ($out -match "=== PM2 no1kmedi-com ===")
        $payload.ssh_success = ($proc.ExitCode -eq 0) -or $hasPm2
        if ($out.Length -gt 6000) { $payload.stdout_excerpt = $out.Substring(0, 6000) + "..." }
        else { $payload.stdout_excerpt = $out }
        if ($err.Length -gt 800) { $payload.stderr_excerpt = $err.Substring(0, 800) + "..." }
        else { $payload.stderr_excerpt = $err }

        foreach ($name in @("no1kmedi-com", "no1kmedi-payapp-api", "mkmlife")) {
            $payload.pm2_facts[$name] = Parse-Pm2ExecCwd -text $out -processName $name
        }
        foreach ($line in ($out -split "[\r\n]+")) {
            $line = $line.Trim()
            if ($line -match '^(EXISTS|ABSENT)\s+(\S+)') {
                $payload.path_probe[$Matches[2]] = ($Matches[1] -eq "EXISTS")
            }
        }
        if ($out -match "nginx: configuration file .+ test is successful") {
            $payload.origin_probe.nginx_config_test = "ok"
        }
        elseif ($out -match "=== NGINX ===") {
            $payload.origin_probe.nginx_config_test = "unknown_or_failed"
        }
        if ($out -match "LOCAL_3010_HTTP_CODE=(\d{3})") {
            $payload.origin_probe.local_next_3010_status = [int]$Matches[1]
        }
        elseif ($out -match "LOCAL_3010_FAIL") {
            $payload.origin_probe.local_next_3010_status = $null
            $payload.origin_probe.local_next_3010_error = "curl_failed"
        }
        if ($out -match '"ok"\s*:\s*true') {
            $payload.origin_probe.payapp_local_health_snippet = $true
        }

        $no1Exec = $payload.pm2_facts["no1kmedi-com"].exec_cwd
        $payload.ssot_reconciliation = @{
            vps_no1kmedi_uses_tarball_path = ($no1Exec -eq $payload.ssot_pm2_paths.no1kmedi_tarball)
            standalone_path_on_disk        = [bool]$payload.path_probe[$payload.ssot_pm2_paths.no1kmedi_com_doc]
            doc_standalone_path_stale      = ($no1Exec -and $no1Exec -ne $payload.ssot_pm2_paths.no1kmedi_com_doc)
            canonical_runtime_path         = $payload.ssot_pm2_paths.no1kmedi_tarball
            note                           = "VPS runs npm start from monorepo tarball path; local next build has no output:standalone"
        }
    }
    finally {
        Remove-Item -LiteralPath $outFile, $errFile -Force -ErrorAction SilentlyContinue
    }
}

$dir = Split-Path -Parent $OutJson
if (-not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
$jsonBody = $payload | ConvertTo-Json -Depth 8 -Compress
[System.IO.File]::WriteAllText($OutJson, $jsonBody, (New-Object System.Text.UTF8Encoding $false))

Write-Host "[Invoke-No1kmediVpsPm2Preflight_v1] wrote $OutJson"
if ($payload.skipped) {
    Write-Host "[Invoke-No1kmediVpsPm2Preflight_v1] skipped: $($payload.skip_reason)" -ForegroundColor Yellow
    exit 0
}
if (-not $payload.ssh_success) {
    Write-Host "[Invoke-No1kmediVpsPm2Preflight_v1] ssh failed (rc=$($payload.ssh_returncode))" -ForegroundColor Red
    exit $(if ($Strict) { 1 } else { 0 })
}
Write-Host "[Invoke-No1kmediVpsPm2Preflight_v1] ssh ok — no1kmedi exec cwd: $($payload.pm2_facts['no1kmedi-com'].exec_cwd)" -ForegroundColor Green
exit 0
