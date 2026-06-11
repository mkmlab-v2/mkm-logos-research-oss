# Long-running lens MusicGen rebake worker (NVIDIA warm batch). Run detached from resume wrapper.
param(
    [string]$WorkspaceRoot = $(if ($env:MKM_WORKSPACE_ROOT) { $env:MKM_WORKSPACE_ROOT } else { "C:\workspace" }),
    [switch]$ForceRegen,
    [switch]$RemainingOnly,
    [switch]$ShortFix,
    [switch]$SkipSync
)

$ErrorActionPreference = "Stop"
Set-Location $WorkspaceRoot

$log = Join-Path $WorkspaceRoot "reports\lens_musicgen_rebake_resume_32s.log"
$state = Join-Path $WorkspaceRoot "reports\lens_musicgen_rebake_state_v1_latest.json"
$pidFile = Join-Path $WorkspaceRoot "reports\lens_musicgen_rebake_worker.pid"

function Write-Log([string]$Message) {
    $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Message"
    Add-Content -LiteralPath $log -Value $line -Encoding utf8
    Write-Host $line
}

function Write-WorkerState([string]$Phase, [hashtable]$Extra = @{}) {
    $payload = [ordered]@{
        schema = "lens_musicgen_rebake_worker_v1"
        updated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
        phase = $Phase
        pid = $PID
        force_regen = [bool]$ForceRegen
    }
    foreach ($k in $Extra.Keys) { $payload[$k] = $Extra[$k] }
    $payload | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $state -Encoding utf8
}

try {
    Set-Content -LiteralPath $pidFile -Value "$PID" -Encoding ascii -Force
    Write-WorkerState "worker_start"
    Write-Log "WORKER START pid=$PID ForceRegen=$ForceRegen RemainingOnly=$RemainingOnly ShortFix=$ShortFix"

    $regenPairsAll = @(
        "hp050_taeyang_defend_v1.wav",
        "hp050_taeyang_attack_v1.wav",
        "hp050_taeeum_idle_v1.wav",
        "hp050_taeeum_defend_v1.wav",
        "hp050_taeeum_attack_v1.wav",
        "hp050_soeum_idle_v1.wav",
        "hp050_soeum_defend_v1.wav",
        "hp050_soeum_attack_v1.wav"
    )
    $regenPairsRemaining = @(
        "hp050_taeeum_attack_v1.wav",
        "hp050_soeum_idle_v1.wav",
        "hp050_soeum_defend_v1.wav",
        "hp050_soeum_attack_v1.wav"
    )
    $regenPairsShortFix = @(
        "hp050_taeeum_defend_v1.wav",
        "hp050_taeeum_idle_v1.wav",
        "hp050_taeyang_attack_v1.wav"
    )
    $regenPairs = if ($ShortFix) {
        $regenPairsShortFix
    } elseif ($RemainingOnly) {
        $regenPairsRemaining
    } else {
        $regenPairsAll
    }
    if ($ForceRegen -or $RemainingOnly -or $ShortFix) {
        $outDir = Join-Path $WorkspaceRoot "reports\track_c_audio_hook_samples_v1"
        foreach ($name in $regenPairs) {
            $path = Join-Path $outDir $name
            if (Test-Path -LiteralPath $path) {
                Remove-Item -LiteralPath $path -Force
                Write-Log "removed stale $name"
            }
        }
    }

    $bakeScript = Join-Path $WorkspaceRoot "scripts\build_lens_btrack_audio_loops_musicgen_v1.py"
    $bakeArgs = @(
        $bakeScript,
        "--seconds", "32",
        "--skip-existing",
        "--warm-batch",
        "--gate-mode", "warn"
    )
    if ($ForceRegen) {
        $bakeArgs += "--force-regen"
    } elseif (-not $RemainingOnly -and -not $ShortFix) {
        $bakeArgs += "--recover-from-gen"
    }

    Write-Log "bake: py $($bakeArgs -join ' ')"
    & py @bakeArgs 2>&1 | ForEach-Object { Write-Log $_ }
    $bakeExit = $LASTEXITCODE

    Write-Log "post-bake recover-from-gen (publish gen/*.wav when gate-warn missed)"
    $recoverArgs = @(
        $bakeScript,
        "--seconds", "32",
        "--skip-existing",
        "--recover-from-gen"
    )
    & py @recoverArgs 2>&1 | ForEach-Object { Write-Log $_ }
    if ($LASTEXITCODE -ne 0) {
        Write-WorkerState "worker_fail" @{ exit_code = $LASTEXITCODE; step = "recover_from_gen" }
        Write-Log "FAIL recover exit=$LASTEXITCODE"
        exit $LASTEXITCODE
    }
    if ($bakeExit -ne 0) {
        Write-Log "WARN bake exit=$bakeExit (continuing after recover-from-gen)"
    }

    Write-Log "offline QA"
    & py (Join-Path $WorkspaceRoot "scripts\check_lens_media_hub_live_qa_v1.py") --offline 2>&1 | ForEach-Object { Write-Log $_ }
    if ($LASTEXITCODE -ne 0) {
        Write-WorkerState "worker_fail" @{ exit_code = $LASTEXITCODE; step = "offline_qa" }
        exit $LASTEXITCODE
    }

    if (-not $SkipSync) {
        Write-Log "VPS sync"
        & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $WorkspaceRoot "scripts\sync_showroom_to_vps.ps1") -SkipDotenvUserSync 2>&1 | ForEach-Object { Write-Log $_ }
        if ($LASTEXITCODE -ne 0) {
            Write-WorkerState "worker_fail" @{ exit_code = $LASTEXITCODE; step = "vps_sync" }
            exit $LASTEXITCODE
        }

        Write-Log "live QA"
        & py (Join-Path $WorkspaceRoot "scripts\check_lens_media_hub_live_qa_v1.py") 2>&1 | ForEach-Object { Write-Log $_ }
        if ($LASTEXITCODE -ne 0) {
            Write-WorkerState "worker_fail" @{ exit_code = $LASTEXITCODE; step = "live_qa" }
            exit $LASTEXITCODE
        }
    }

    Write-WorkerState "worker_done" @{ exit_code = 0 }
    Write-Log "DONE exit=0"
    exit 0
}
finally {
    if (Test-Path -LiteralPath $pidFile) { Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue }
}
