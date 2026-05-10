#Requires -Version 5.1
<#
.SYNOPSIS
  Non-interactive VPS SSH smoke — disk evidence for schedules / 암행어사 bundle (not Cursor MCP).

.DESCRIPTION
  Runs one short remote command via ssh.exe when MKM_VPS_HOST and a private key resolve.
  Separate from devops-mcp (agent tools); same env/key conventions as mcp-servers/devops_mcp_server.py.

  Skip (no host or no key): writes JSON with skipped=true, exits 0.

.PARAMETER SoftFail
  Always exit 0; record ssh outcome in JSON (use at tail of Run-AmsaengEosaMonitoringBundleTask.ps1).

.PARAMETER RemoteCommand
  Single remote shell command (default: echo marker).

.PARAMETER OutJson
  Output path (default: reports/vps_ops_smoke_latest.json).

.NOTES
  Env: MKM_VPS_HOST, MKM_VPS_USER (default root), MKM_VPS_SSH_KEY_PATH, SSH_KEY_PATH.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$RemoteCommand = 'echo VPS_OPS_SMOKE_OK',
    [string]$OutJson = "",
    [switch]$SoftFail
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($OutJson)) {
    $OutJson = Join-Path $WorkspaceRoot "reports\vps_ops_smoke_latest.json"
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
if (-not [string]::IsNullOrWhiteSpace($hostAddr)) {
    $hostAddr = $hostAddr.Trim()
}
else {
    $hostAddr = $null
}

$user = $env:MKM_VPS_USER
if ([string]::IsNullOrWhiteSpace($user)) { $user = "root" }

$keyPath = Resolve-SshKeyPath -Root $WorkspaceRoot
$ts = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")

$payload = [ordered]@{
    schema           = "vps_ops_smoke_v1"
    generated_at_utc = $ts
    workspace_root   = $WorkspaceRoot
    skipped          = $false
    skip_reason      = $null
    host             = $hostAddr
    user             = $user
    key_resolved     = [bool]$keyPath
    ssh_success      = $false
    returncode       = $null
    stdout_excerpt   = $null
    stderr_excerpt   = $null
    remote_command   = $RemoteCommand
    notes            = "Disk smoke only; not devops-mcp. Compare CENTRAL/devops-mcp for interactive VPS tools."
}

if (-not $hostAddr -or -not $keyPath) {
    $payload.skipped = $true
    if (-not $hostAddr) { $payload.skip_reason = "MKM_VPS_HOST unset" }
    elseif (-not $keyPath) { $payload.skip_reason = "no_ssh_key (MKM_VPS_SSH_KEY_PATH / SSH_KEY_PATH / hostinger_mkmlife)" }
}

else {
    $sshExe = (Get-Command ssh.exe -ErrorAction SilentlyContinue).Source
    if (-not $sshExe) {
        $payload.skipped = $true
        $payload.skip_reason = "ssh.exe not on PATH"
    }
    else {
        $argList = @(
            "-i", $keyPath,
            "-o", "BatchMode=yes",
            "-o", "StrictHostKeyChecking=no",
            "-o", "ConnectTimeout=15",
            "-o", "UserKnownHostsFile=NUL",
            "${user}@${hostAddr}",
            $RemoteCommand
        )
        $outFile = [System.IO.Path]::GetTempFileName()
        $errFile = [System.IO.Path]::GetTempFileName()
        try {
            $proc = Start-Process -FilePath $sshExe -ArgumentList $argList -Wait -PassThru -NoNewWindow `
                -RedirectStandardOutput $outFile -RedirectStandardError $errFile
            # Cap read: avoid huge stdout/err blowing JSON or memory (Fact-Lock).
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
            $out = [string](Read-TextHead $outFile)
            $err = [string](Read-TextHead $errFile)
            $payload.returncode = $proc.ExitCode
            $payload.ssh_success = ($proc.ExitCode -eq 0)
            if ($out.Length -gt 1200) { $payload.stdout_excerpt = $out.Substring(0, 1200) + "..." }
            else { $payload.stdout_excerpt = $out }
            if ($err.Length -gt 800) { $payload.stderr_excerpt = $err.Substring(0, 800) + "..." }
            else { $payload.stderr_excerpt = $err }
        }
        finally {
            Remove-Item -LiteralPath $outFile -ErrorAction SilentlyContinue
            Remove-Item -LiteralPath $errFile -ErrorAction SilentlyContinue
        }
    }
}

$json = $payload | ConvertTo-Json -Depth 6 -Compress
$dir = Split-Path -Parent $OutJson
if ($dir -and -not (Test-Path -LiteralPath $dir)) {
    New-Item -ItemType Directory -Path $dir -Force | Out-Null
}
Set-Content -LiteralPath $OutJson -Value $json -Encoding UTF8
Write-Output $json

if ($SoftFail) { exit 0 }
if ($payload.skipped) { exit 0 }
if ($payload.ssh_success) { exit 0 }
exit 1
