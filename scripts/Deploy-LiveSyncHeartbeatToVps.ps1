#Requires -Version 5.1
<#
.SYNOPSIS
  VPS에 live_sync 하트비트 스니펫을 배포하고 cron(5분) 등록 후 로컬 SCP 풀을 한 번 검증한다.

.DESCRIPTION
  Invoke-VpsOpsSmoke_v1.ps1 / Invoke-LiveSyncHeartbeatPull.ps1 과 동일한 MKM_VPS_*·키 규약.
  Process 환경에 없으면 C:\workspace\.env 에서 MKM_VPS_HOST / MKM_VPS_USER / MKM_VPS_SSH_KEY_PATH 만 로드(값 출력 안 함).

.PARAMETER SkipPullTest
  배포 후 Invoke-LiveSyncHeartbeatPull 생략.

.PARAMETER SoftFail
  실패해도 exit 0 (로그 JSON 유지).
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$LocalScriptRelative = "scripts\linux\live_sync_push_heartbeat_snippet.sh",
    [string]$RemoteInstallPath = "/opt/mkm-tools/live_sync_push_heartbeat_snippet.sh",
    [string]$HeartbeatPath = "/tmp/daemon_alive_check.json",
    [string]$OutJson = "",
    [switch]$SkipPullTest,
    [switch]$SoftFail
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($WorkspaceRoot)) {
    $WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}

if ([string]::IsNullOrWhiteSpace($OutJson)) {
    $OutJson = Join-Path $WorkspaceRoot "reports\live_sync_vps_deploy_latest.json"
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

function Import-MkmVpsEnvFromDotEnv([string]$WorkspaceRoot) {
    $dotEnv = Join-Path $WorkspaceRoot ".env"
    if (-not (Test-Path -LiteralPath $dotEnv)) { return }
    foreach ($raw in Get-Content -LiteralPath $dotEnv) {
        $line = $raw.Trim()
        if (-not $line -or $line.StartsWith("#") -or $line.IndexOf("=") -lt 1) { continue }
        $idx = $line.IndexOf("=")
        $k = $line.Substring(0, $idx).Trim()
        if ($k -notmatch "^(MKM_VPS_HOST|MKM_VPS_USER|MKM_VPS_SSH_KEY_PATH)$") { continue }
        $v = $line.Substring($idx + 1).Trim().Trim('"')
        if ([string]::IsNullOrWhiteSpace($v)) { continue }
        $cur = [Environment]::GetEnvironmentVariable($k, "Process")
        if ([string]::IsNullOrWhiteSpace($cur)) {
            [Environment]::SetEnvironmentVariable($k, $v, "Process")
        }
    }
}

Import-MkmVpsEnvFromDotEnv -WorkspaceRoot $WorkspaceRoot

$hostAddr = $env:MKM_VPS_HOST
if (-not [string]::IsNullOrWhiteSpace($hostAddr)) { $hostAddr = $hostAddr.Trim() } else { $hostAddr = $null }

$user = $env:MKM_VPS_USER
if ([string]::IsNullOrWhiteSpace($user)) { $user = "root" }

$keyPath = Resolve-SshKeyPath -Root $WorkspaceRoot
$ts = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")

$payload = [ordered]@{
    schema              = "live_sync_vps_deploy_v1"
    generated_at_utc    = $ts
    workspace_root      = $WorkspaceRoot
    skipped             = $false
    skip_reason         = $null
    host                = $hostAddr
    user                = $user
    key_resolved        = [bool]$keyPath
    mkdir_exit          = $null
    scp_success         = $false
    remote_bootstrap_ok = $false
    remote_stdout       = $null
    remote_stderr       = $null
    pull_test_exit      = $null
    notes               = "Deploys bash snippet + root crontab; same paths as Invoke-LiveSyncHeartbeatPull."
}

function Read-TextHead([string]$path, [int]$maxBytes = 8192) {
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

if (-not $hostAddr -or -not $keyPath) {
    $payload.skipped = $true
    if (-not $hostAddr) { $payload.skip_reason = "MKM_VPS_HOST unset (.env or env)" }
    elseif (-not $keyPath) { $payload.skip_reason = "no_ssh_key" }
}
else {
    $sshExe = (Get-Command ssh.exe -ErrorAction SilentlyContinue).Source
    $scpExe = (Get-Command scp.exe -ErrorAction SilentlyContinue).Source
    if (-not $sshExe -or -not $scpExe) {
        $payload.skipped = $true
        $payload.skip_reason = if (-not $sshExe) { "ssh.exe not on PATH" } else { "scp.exe not on PATH" }
    }
    else {
        $localSrc = Join-Path $WorkspaceRoot $LocalScriptRelative
        if (-not (Test-Path -LiteralPath $localSrc)) {
            $payload.skipped = $true
            $payload.skip_reason = "missing_local_script"
        }
        else {
            $content = Get-Content -LiteralPath $localSrc -Raw
            $content = $content -replace "`r`n", "`n" -replace "`r", "`n"
            $tempLf = [System.IO.Path]::GetTempFileName()
            try {
                [System.IO.File]::WriteAllText($tempLf, $content, [System.Text.UTF8Encoding]::new($false))

                $mkdirCmd = "mkdir -p /opt/mkm-tools"
                $argMk = @(
                    "-i", $keyPath,
                    "-o", "BatchMode=yes",
                    "-o", "StrictHostKeyChecking=no",
                    "-o", "ConnectTimeout=20",
                    "-o", "UserKnownHostsFile=NUL",
                    "${user}@${hostAddr}",
                    $mkdirCmd
                )
                $outM = [System.IO.Path]::GetTempFileName()
                $errM = [System.IO.Path]::GetTempFileName()
                try {
                    $prM = Start-Process -FilePath $sshExe -ArgumentList $argMk -Wait -PassThru -NoNewWindow `
                        -RedirectStandardOutput $outM -RedirectStandardError $errM
                    $payload.mkdir_exit = $prM.ExitCode
                }
                finally {
                    Remove-Item -LiteralPath $outM -ErrorAction SilentlyContinue
                    Remove-Item -LiteralPath $errM -ErrorAction SilentlyContinue
                }

                $remoteUri = "${user}@${hostAddr}:${RemoteInstallPath}"
                $argScp = @(
                    "-i", $keyPath,
                    "-o", "BatchMode=yes",
                    "-o", "StrictHostKeyChecking=no",
                    "-o", "ConnectTimeout=20",
                    "-o", "UserKnownHostsFile=NUL",
                    $tempLf,
                    $remoteUri
                )
                $errS = [System.IO.Path]::GetTempFileName()
                try {
                    $prS = Start-Process -FilePath $scpExe -ArgumentList $argScp -Wait -PassThru -NoNewWindow `
                        -RedirectStandardError $errS
                    $payload.scp_success = ($prS.ExitCode -eq 0)
                }
                finally {
                    Remove-Item -LiteralPath $errS -ErrorAction SilentlyContinue
                }

                if ($payload.scp_success) {
                    $remoteCmd = @"
chmod +x $RemoteInstallPath && $RemoteInstallPath $HeartbeatPath && { crontab -l 2>/dev/null | grep -v live_sync_push_heartbeat_snippet.sh || true; echo '*/5 * * * * $RemoteInstallPath $HeartbeatPath'; } | crontab - && echo LIVE_SYNC_DEPLOY_OK
"@
                    $argBoot = @(
                        "-i", $keyPath,
                        "-o", "BatchMode=yes",
                        "-o", "StrictHostKeyChecking=no",
                        "-o", "ConnectTimeout=20",
                        "-o", "UserKnownHostsFile=NUL",
                        "${user}@${hostAddr}",
                        $remoteCmd.Trim()
                    )
                    $outB = [System.IO.Path]::GetTempFileName()
                    $errB = [System.IO.Path]::GetTempFileName()
                    try {
                        $prB = Start-Process -FilePath $sshExe -ArgumentList $argBoot -Wait -PassThru -NoNewWindow `
                            -RedirectStandardOutput $outB -RedirectStandardError $errB
                        $payload.remote_bootstrap_ok = ($prB.ExitCode -eq 0)
                        $payload.remote_stdout = [string](Read-TextHead $outB)
                        $payload.remote_stderr = [string](Read-TextHead $errB)
                    }
                    finally {
                        Remove-Item -LiteralPath $outB -ErrorAction SilentlyContinue
                        Remove-Item -LiteralPath $errB -ErrorAction SilentlyContinue
                    }
                }
            }
            finally {
                Remove-Item -LiteralPath $tempLf -Force -ErrorAction SilentlyContinue
            }

            if (-not $SkipPullTest -and $payload.remote_bootstrap_ok) {
                $pull = Join-Path $WorkspaceRoot "scripts\Invoke-LiveSyncHeartbeatPull.ps1"
                if (Test-Path -LiteralPath $pull) {
                    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $pull -WorkspaceRoot $WorkspaceRoot
                    $payload.pull_test_exit = $LASTEXITCODE
                }
            }
        }
    }
}

$dir = Split-Path -Parent $OutJson
if ($dir -and -not (Test-Path -LiteralPath $dir)) {
    New-Item -ItemType Directory -Path $dir -Force | Out-Null
}
$payload | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $OutJson -Encoding UTF8

$ok = $payload.skipped -or ($payload.scp_success -and $payload.remote_bootstrap_ok)
Write-Output "live_sync_vps_deploy_written=$OutJson ok=$ok skipped=$($payload.skipped) pull_exit=$($payload.pull_test_exit)"

if ($SoftFail) { exit 0 }
if ($payload.skipped) { exit 0 }
if ($payload.scp_success -and $payload.remote_bootstrap_ok) { exit 0 }
exit 1
