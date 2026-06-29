# Nemotron Kaggle notebook lane — local validate + optional push/run (smoke).
# NEVER competition submit. Requires -AllowKernelPush to upload/run on Kaggle.
param(
    [switch]$AllowKernelPush,
    [switch]$PushOnly,
    [switch]$KaggleFull,
    [switch]$WaitForKernelComplete,
    [switch]$PollKernelOnly,
    [int]$PrepLimit = 32,
    [int]$DryRunLimit = 8,
    [int]$PushTimeoutSec = 14400,
    [int]$KernelPollSec = 120,
    [int]$KernelMaxWaitSec = 14400,
    [ValidateSet('fast', 'nemotron')]
    [string]$TrainProfile = 'fast',
    [string]$Accelerator = 'gpu-t4-x2'
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$slug = 'nvidia-nemotron-model-reasoning-challenge'
$nbDir = Join-Path $root "data\kaggle\$slug\kaggle_train_nb"
$report = Join-Path $root 'reports\kaggle_nemotron_resume_latest.json'
$logJsonl = Join-Path $root 'reports\kaggle_private_dev_log.jsonl'

function Write-AuditLog([hashtable] $row) {
    $row['schema'] = 'kaggle_private_dev_log_v1'
    $row['at_utc'] = (Get-Date).ToUniversalTime().ToString('o')
    $row['lane'] = 'nemotron_qlora_smoke'
    $row['mkm_core_exposed'] = $false
    $row['submit_attempted'] = $false
    Add-Content -Path $logJsonl -Value ($row | ConvertTo-Json -Compress)
}

function Step([string] $name, [scriptblock] $block) {
    Write-Host "`n=== $name ==="
    & $block
    if ($LASTEXITCODE -ne 0) {
        throw "Step failed: $name (exit $LASTEXITCODE)"
    }
    Write-Host "[OK] $name"
}

$steps = [ordered]@{}
$fail = $null
$finalStatus = $null

try {
    if (-not $PollKernelOnly) {
    Step 'notebook_sync' {
        $nbArgs = @('scripts/build_kaggle_nemotron_notebook_from_py_v1.py', '--train-profile', $TrainProfile)
        if ($KaggleFull) { $nbArgs += '--kaggle-full' }
        py @nbArgs
    }
    Step 'kernel_bundle' {
        py scripts/build_kaggle_nemotron_kernel_bundle_v1.py
    }
    Step 'prep' {
        py scripts/run_kaggle_nemotron_private_prep_v1.py --limit $PrepLimit
    }
    Step 'train_dryrun' {
        py (Join-Path $root "data\kaggle\$slug\kaggle_train\nemotron_qlora_train_v1.py") --dry-run --limit $DryRunLimit
    }
    Step 'kaggle_auth_probe' {
        py scripts/probe_kaggle_facts_official_access_v1.py
    }
    }

    $pushResult = 'skipped'
    if ($PollKernelOnly) {
        if (-not (Get-Command kaggle -ErrorAction SilentlyContinue)) {
            throw 'kaggle CLI not on PATH'
        }
        $pushResult = 'poll_only'
        $kernelId = 'familyunion/nemotron-qlora-private-train-v2-notebook-t4'
        $WaitForKernelComplete = $true
    } elseif ($AllowKernelPush) {
        if (-not (Get-Command kaggle -ErrorAction SilentlyContinue)) {
            throw 'kaggle CLI not on PATH'
        }
        Step 'kernels_push_notebook' {
            kaggle kernels push -p $nbDir --accelerator $Accelerator -t $PushTimeoutSec
        }
        $pushResult = 'pushed'
        $kernelId = 'familyunion/nemotron-qlora-private-train-v2-notebook-t4'
    }
    if (($AllowKernelPush -or $PollKernelOnly) -and -not $PushOnly) {
        Write-Host "`n=== kernel_status (poll) ==="
        Start-Sleep -Seconds 45
        $kernelId = 'familyunion/nemotron-qlora-private-train-v2-notebook-t4'
        $deadline = (Get-Date).AddSeconds($KernelMaxWaitSec)
        $finalStatus = 'unknown'
        $statusLine = ''
        $pollErrors = 0
        do {
            try {
                $prevEap = $ErrorActionPreference
                $ErrorActionPreference = 'Continue'
                $statusLine = (kaggle kernels status $kernelId 2>&1 | Out-String).Trim()
                $statusExit = $LASTEXITCODE
                $ErrorActionPreference = $prevEap
                if ($statusExit -ne 0 -and $statusLine -match '500|Internal Server Error|503|429') {
                    $pollErrors++
                    Write-Host "[WARN] status API transient ($pollErrors): $statusLine"
                    if ($pollErrors -ge 3 -and $WaitForKernelComplete) {
                        Write-Host "[WARN] status API unavailable x$pollErrors — treating as poll_degraded"
                        break
                    }
                    Start-Sleep -Seconds $KernelPollSec
                    continue
                }
                Write-Host $statusLine
                if ($statusLine -match 'COMPLETE') {
                    $finalStatus = 'COMPLETE'
                    break
                }
                if ($statusLine -match 'ERROR|CANCEL') {
                    $finalStatus = 'ERROR'
                    break
                }
            } catch {
                $pollErrors++
                Write-Host "[WARN] status poll exception ($pollErrors): $_"
            }
            if (-not $WaitForKernelComplete) { break }
            Start-Sleep -Seconds $KernelPollSec
        } while ((Get-Date) -lt $deadline)
        if ($statusLine -match 'P100|sm_60|capability 6\.0') {
            Write-Host "[BLOCKER] Kaggle ran P100, not T4 x2. CLI --accelerator may be ignored." -ForegroundColor Yellow
            Write-Host "  Fix: open kernel URL -> Settings -> Accelerator -> GPU T4 x2 -> Save Version -> Run All"
        }
        if ($WaitForKernelComplete -and $finalStatus -ne 'COMPLETE') {
            if ($pollErrors -ge 3 -or (($pushResult -eq 'pushed' -or $pushResult -eq 'poll_only') -and $pollErrors -gt 0)) {
                Write-Host "[WARN] Kernel push recorded; status API degraded (errors=$pollErrors). Verify on Kaggle UI." -ForegroundColor Yellow
                Write-Host "  https://www.kaggle.com/code/$kernelId"
                $finalStatus = 'poll_degraded'
            } else {
                throw "Kernel did not COMPLETE (status=$finalStatus). See kaggle kernels logs $kernelId"
            }
        }
    } elseif (-not $PollKernelOnly -and -not $AllowKernelPush) {
        Write-Host "`n[INFO] Remote push skipped. Re-run with -AllowKernelPush to upload+run on Kaggle."
        Write-Host "  kaggle kernels push -p $nbDir --accelerator $Accelerator"
    }

    $summary = [ordered]@{
        schema = 'kaggle_nemotron_resume_v1'
        finished_at_utc = (Get-Date).ToUniversalTime().ToString('o')
        lane = 'private_dev_no_mkm_core'
        research_only = $true
        local_validate_ok = $true
        push_result = $pushResult
        accelerator = $Accelerator
        kaggle_full = $KaggleFull.IsPresent
        train_profile = $TrainProfile
        kernel_wait = $WaitForKernelComplete.IsPresent
        kernel_final_status = if ($finalStatus) { $finalStatus } else { $null }
        kernel_url = 'https://www.kaggle.com/code/familyunion/nemotron-qlora-private-train-v2-notebook-t4'
        allow_competition_submit = $false
        hf_token_kaggle_secret = 'Set HF_TOKEN in Kaggle Notebook Secrets if Hub download fails'
        next_human = @(
            'Paste ONE cell: reports/kaggle_nemotron_notebook_cell12_combined_v45.txt (v45 keeps /kaggle/tmp/nemotron_hf_model on retry)'
            'Kaggle Secrets: HF_TOKEN → Restart session'
            'Settings: GPU T4 x2, Internet ON, Private'
            'Smoke default; full: MKM_KAGGLE_FULL=1 in combined cell (change sys.argv)'
            'Download /kaggle/working/submission.zip — do NOT Submit'
        )
        notebook_paste = @{
            combined_v45 = 'reports/kaggle_nemotron_notebook_cell12_combined_v45.txt'
            cell1_writefile = 'reports/kaggle_nemotron_notebook_cell1_writefile_v45.txt'
            cell2_smoke = 'reports/kaggle_nemotron_notebook_cell2_run_nemotron_smoke_v1.txt'
            ipynb = 'data/kaggle/nvidia-nemotron-model-reasoning-challenge/kaggle_train_nb/nemotron_qlora_train_v1.ipynb'
        }
    }
    $summary | ConvertTo-Json -Depth 6 | Set-Content -Path $report -Encoding utf8
    Write-AuditLog @{ event = 'resume_lane'; push_result = $pushResult; local_ok = $true }
    Write-Host "`n[OK] wrote $report"
    exit 0
}
catch {
    $fail = $_.Exception.Message
    Write-Host "[FAIL] $fail" -ForegroundColor Red
    Write-AuditLog @{ event = 'resume_lane_fail'; error = $fail }
    @{
        schema = 'kaggle_nemotron_resume_v1'
        finished_at_utc = (Get-Date).ToUniversalTime().ToString('o')
        local_validate_ok = $false
        error = $fail
    } | ConvertTo-Json | Set-Content -Path $report -Encoding utf8
    exit 1
}
