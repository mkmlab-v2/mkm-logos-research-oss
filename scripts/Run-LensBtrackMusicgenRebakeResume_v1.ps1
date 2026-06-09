# Resume lens MusicGen 32s bake (NVIDIA warm batch) — detached worker avoids agent-shell timeout.
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Run-LensBtrackMusicgenRebakeResume_v1.ps1 -Detached -ForceRegen
#   powershell ... -Status
#   powershell ...                    # inline (same shell; may timeout in Cursor agent)

param(
    [switch]$Detached,
    [switch]$Status,
    [switch]$ForceRegen,
    [switch]$RemainingOnly,
    [switch]$ShortFix,
    [switch]$SkipSync,
    [string]$WorkspaceRoot = $(if ($env:MKM_WORKSPACE_ROOT) { $env:MKM_WORKSPACE_ROOT } else { "C:\workspace" })
)

$ErrorActionPreference = "Stop"
Set-Location $WorkspaceRoot

$log = Join-Path $WorkspaceRoot "reports\lens_musicgen_rebake_resume_32s.log"
$state = Join-Path $WorkspaceRoot "reports\lens_musicgen_rebake_state_v1_latest.json"
$pidFile = Join-Path $WorkspaceRoot "reports\lens_musicgen_rebake_worker.pid"
$worker = Join-Path $WorkspaceRoot "scripts\Invoke-LensBtrackMusicgenRebakeWorker_v1.ps1"

function Write-Log([string]$Message) {
    $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Message"
    Add-Content -LiteralPath $log -Value $line -Encoding utf8
    Write-Host $line
}

if ($Status) {
    $workerRunning = $false
    if (Test-Path -LiteralPath $pidFile) {
        $wpid = (Get-Content -LiteralPath $pidFile -Raw).Trim()
        $proc = Get-Process -Id ([int]$wpid) -ErrorAction SilentlyContinue
        if ($proc) {
            $workerRunning = $true
            Write-Host "worker_pid=$wpid (running)"
        } else {
            Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
            Write-Host "worker_pid=$wpid (stale — process gone; removed pid file)"
        }
    } else {
        Write-Host "worker_pid=none"
    }
    if (Test-Path -LiteralPath $state) {
        Get-Content -LiteralPath $state -Raw
    } else {
        Write-Host "state=missing"
    }
    $wavCount = (Get-ChildItem -Path (Join-Path $WorkspaceRoot "reports\track_c_audio_hook_samples_v1\hp050_*.wav") -ErrorAction SilentlyContinue).Count
    Write-Host "local_hp050_wavs=$wavCount"
    exit 0
}

if ($Detached) {
    if (Test-Path -LiteralPath $pidFile) {
        $existingPid = (Get-Content -LiteralPath $pidFile -Raw).Trim()
        if (Get-Process -Id ([int]$existingPid) -ErrorAction SilentlyContinue) {
            Write-Log "DETACHED skip: worker already running pid=$existingPid"
            exit 0
        }
        Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
    }
    $argParts = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", "`"$worker`"",
        "-WorkspaceRoot", "`"$WorkspaceRoot`""
    )
    if ($ForceRegen) { $argParts += "-ForceRegen" }
    if ($RemainingOnly) { $argParts += "-RemainingOnly" }
    if ($ShortFix) { $argParts += "-ShortFix" }
    if ($SkipSync) { $argParts += "-SkipSync" }
    $psExe = if (Get-Command pwsh -ErrorAction SilentlyContinue) { "pwsh.exe" } else { "powershell.exe" }
    Start-Process -FilePath $psExe -ArgumentList $argParts -WorkingDirectory $WorkspaceRoot -WindowStyle Hidden | Out-Null
    Write-Log "DETACHED started worker ForceRegen=$ForceRegen RemainingOnly=$RemainingOnly ShortFix=$ShortFix"
    Write-Host "Detached worker started. Check: scripts\Run-LensBtrackMusicgenRebakeResume_v1.ps1 -Status"
    exit 0
}

# Inline fallback
$inlineArgs = @("-WorkspaceRoot", $WorkspaceRoot)
if ($ForceRegen) { $inlineArgs += "-ForceRegen" }
if ($RemainingOnly) { $inlineArgs += "-RemainingOnly" }
if ($ShortFix) { $inlineArgs += "-ShortFix" }
if ($SkipSync) { $inlineArgs += "-SkipSync" }
& powershell -NoProfile -ExecutionPolicy Bypass -File $worker @inlineArgs
exit $LASTEXITCODE
