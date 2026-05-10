#Requires -Version 5.1
<#
.SYNOPSIS
  SCP로 VPS의 daemon_alive_check.json 을 live_sync/incoming 으로 가져온다 (풀 자동화).

.DESCRIPTION
  Invoke-VpsOpsSmoke_v1.ps1 과 동일한 MKM_VPS_HOST / 키 규약.
  원격 기본 경로: MKM_LIVE_SYNC_REMOTE_PATH 또는 /tmp/daemon_alive_check.json (linux 스니펫 출력과 동일).

.PARAMETER SoftFail
  실패해도 exit 0 (스케줄 태스크 스팸 방지). 결과는 JSON에 기록.

.NOTES
  VPS에서 cron 예: */5 * * * * /path/live_sync_push_heartbeat_snippet.sh /tmp/daemon_alive_check.json
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$RemotePath = "",
    [string]$LocalRelativePath = "live_sync\incoming\daemon_alive_check.json",
    [string]$OutJson = "",
    [switch]$SoftFail,
    [switch]$SkipHeartbeatCheck
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($WorkspaceRoot)) {
    $WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}

if ([string]::IsNullOrWhiteSpace($OutJson)) {
    $OutJson = Join-Path $WorkspaceRoot "reports\live_sync_pull_latest.json"
}

function Resolve-SshKeyPath([string]$Root) {
    foreach ($p in @($env:MKM_VPS_SSH_KEY_PATH, $env:SSH_KEY_PATH)) {
        if (-not [string]::IsNullOrWhiteSpace($p) -and (Test-Path -LiteralPath $p)) {
            return $p
        }
    }
    $candidates = @(
        (Join-Path $Root '.ssh\hostinger_mkmlife'),
        (Join-Path $env:USERPROFILE '.ssh\hostinger_mkmlife')
    )
    foreach ($c in $candidates) {
        if (Test-Path -LiteralPath $c) { return $c }
    }
    return $null
}

$hostAddr = $env:MKM_VPS_HOST
if (-not [string]::IsNullOrWhiteSpace($hostAddr)) { $hostAddr = $hostAddr.Trim() } else { $hostAddr = $null }

$user = $env:MKM_VPS_USER
if ([string]::IsNullOrWhiteSpace($user)) { $user = "root" }

$keyPath = Resolve-SshKeyPath -Root $WorkspaceRoot

if ([string]::IsNullOrWhiteSpace($RemotePath)) {
    $RemotePath = $env:MKM_LIVE_SYNC_REMOTE_PATH
}
if ([string]::IsNullOrWhiteSpace($RemotePath)) {
    $RemotePath = "/tmp/daemon_alive_check.json"
}

$localFull = Join-Path $WorkspaceRoot $LocalRelativePath
$incomingDir = Split-Path -Parent $localFull
if (-not (Test-Path -LiteralPath $incomingDir)) {
    New-Item -ItemType Directory -Path $incomingDir -Force | Out-Null
}

$ts = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")

$payload = [ordered]@{
    schema           = "live_sync_pull_v1"
    generated_at_utc = $ts
    workspace_root   = $WorkspaceRoot
    skipped          = $false
    skip_reason      = $null
    host             = $hostAddr
    user             = $user
    key_resolved     = [bool]$keyPath
    remote_path      = $RemotePath
    local_path       = $localFull
    scp_success      = $false
    returncode       = $null
    stderr_excerpt   = $null
    heartbeat_check_exit = $null
}

if (-not $hostAddr -or -not $keyPath) {
    $payload.skipped = $true
    if (-not $hostAddr) { $payload.skip_reason = "MKM_VPS_HOST unset" }
    elseif (-not $keyPath) { $payload.skip_reason = "no_ssh_key" }
}
else {
    $scpExe = (Get-Command scp.exe -ErrorAction SilentlyContinue).Source
    if (-not $scpExe) {
        $payload.skipped = $true
        $payload.skip_reason = "scp.exe not on PATH (install OpenSSH Client)"
    }
    else {
        $remoteUri = "${user}@${hostAddr}:${RemotePath}"
        $argList = @(
            "-i", $keyPath,
            "-o", "BatchMode=yes",
            "-o", "StrictHostKeyChecking=no",
            "-o", "ConnectTimeout=20",
            "-o", "UserKnownHostsFile=NUL",
            $remoteUri,
            $localFull
        )
        $errFile = [System.IO.Path]::GetTempFileName()
        try {
            $proc = Start-Process -FilePath $scpExe -ArgumentList $argList -Wait -PassThru -NoNewWindow `
                -RedirectStandardError $errFile
            $payload.returncode = $proc.ExitCode
            $payload.scp_success = ($proc.ExitCode -eq 0)
            if (Test-Path $errFile) {
                $bytes = [System.IO.File]::ReadAllBytes($errFile)
                $cap = [Math]::Min($bytes.Length, 4096)
                $payload.stderr_excerpt = [System.Text.Encoding]::UTF8.GetString($bytes, 0, $cap)
            }
        }
        finally {
            Remove-Item -LiteralPath $errFile -Force -ErrorAction SilentlyContinue
        }

        if (-not $SkipHeartbeatCheck -and $payload.scp_success) {
            $hb = Join-Path $WorkspaceRoot "scripts\Invoke-LiveSyncHeartbeatCheck.ps1"
            if (Test-Path -LiteralPath $hb) {
                & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $hb -WorkspaceRoot $WorkspaceRoot
                $payload.heartbeat_check_exit = $LASTEXITCODE
            }
        }
    }
}

if (-not (Test-Path -LiteralPath (Split-Path -Parent $OutJson))) {
    New-Item -ItemType Directory -Path (Split-Path -Parent $OutJson) -Force | Out-Null
}
$payload | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $OutJson -Encoding UTF8
Write-Output "live_sync_pull_written=$OutJson skipped=$($payload.skipped) scp_success=$($payload.scp_success)"

$failed = (-not $payload.skipped) -and (-not $payload.scp_success)
if ($failed -and -not $SoftFail) {
    exit 1
}
exit 0
