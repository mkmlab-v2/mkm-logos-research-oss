<#
.SYNOPSIS
  Weekly Universal Root community GTM — poll Discussions #2; auto Thread B when external repro gate passes.

.NOTES
  [HYPO] B-track · send_gate HOLD — Thread B live post only when external_repro>=1 and not yet posted.
#>
$ErrorActionPreference = "Stop"
$workspaceRoot = if ($env:MKM_WORKSPACE_ROOT) { $env:MKM_WORKSPACE_ROOT.TrimEnd('\', '/') } else { "C:\workspace" }
$reportPath = Join-Path $workspaceRoot "reports\universal_root_community_gtm_weekly_v1_latest.json"
$gtmPath = Join-Path $workspaceRoot "reports\universal_root_community_gtm_v1_latest.json"
$pollPath = Join-Path $workspaceRoot "reports\universal_root_community_poll_v1_latest.json"
$threadBPath = Join-Path $workspaceRoot "reports\universal_root_discussions_thread_b_post_v1_latest.json"

function Read-JsonFile {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) { return $null }
    return Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json
}

function Thread-BAlreadyPosted {
    $gtm = Read-JsonFile -Path $gtmPath
    if ($gtm -and $gtm.channels -and $gtm.channels.github_discussions) {
        $status = [string]$gtm.channels.github_discussions.thread_b_status
        if ($status -eq "posted") { return $true }
    }
    $post = Read-JsonFile -Path $threadBPath
    if ($post -and $post.ok -eq $true -and $post.discussion_url) { return $true }
    return $false
}

Push-Location $workspaceRoot
try {
    $started = (Get-Date).ToUniversalTime().ToString("o")
    $steps = @()

    function Add-Step {
        param([string]$Name, [int]$Code, [bool]$Required = $true)
        $ok = if ($Required) { $Code -eq 0 } else { $true }
        $script:steps += [ordered]@{
            step      = $Name
            exit_code = $Code
            ok        = $ok
            required  = $Required
        }
        if ($Required -and $Code -ne 0) { throw "FAIL: $Name exit $Code" }
    }

    & py scripts/poll_universal_root_community_gtm_v1.py
    $pollExit = $LASTEXITCODE
    Add-Step "poll_discussions" $pollExit -Required:$false

    & py scripts/check_universal_root_gtm_freeze_v1.py --patch-gtm
    $freezeExit = $LASTEXITCODE
    Add-Step "gtm_freeze_check" $freezeExit -Required:$false

    $gtmFreezeActive = $false
    $gtm = Read-JsonFile -Path $gtmPath
    if ($gtm -and $gtm.gtm_freeze -and $gtm.gtm_freeze.active -eq $true) {
        $gtmFreezeActive = $true
    }

    $externalRepro = 0
    $poll = Read-JsonFile -Path $pollPath
    if ($poll -and $poll.discussion) {
        $externalRepro = [int]($poll.discussion.external_repro_like_count)
        if ($externalRepro -eq 0) {
            $externalRepro = [int]($poll.discussion.external_comment_count)
        }
    }

    $threadBPosted = Thread-BAlreadyPosted
    $threadBAction = "skipped_already_posted"
    $threadBExit = 0

    if ($threadBPosted) {
        Add-Step "thread_b_post" 0 -Required:$false
    }
    elseif ($externalRepro -lt 1) {
        $threadBAction = "blocked_await_external_repro"
        Add-Step "thread_b_post" 0 -Required:$false
    }
    elseif ($gtmFreezeActive) {
        $threadBAction = "blocked_gtm_freeze"
        Add-Step "thread_b_post" 0 -Required:$false
    }
    else {
        & py scripts/post_universal_root_discussions_thread_b_v1.py --acknowledge-send
        $threadBExit = $LASTEXITCODE
        if ($threadBExit -eq 0) {
            $threadBAction = "posted_live"
        }
        elseif ($threadBExit -eq 3) {
            $threadBAction = "blocked_external_repro_gate"
        }
        else {
            $threadBAction = "post_failed"
        }
        Add-Step "thread_b_post" $threadBExit -Required:$false
    }

    $chainPass = ($steps | Where-Object { $_.required -and -not $_.ok }).Count -eq 0

    $payload = [ordered]@{
        schema                  = "universal_root_community_gtm_weekly_v1"
        generated_at_utc        = (Get-Date).ToUniversalTime().ToString("o")
        started_at_utc          = $started
        research_only           = $true
        send_gate               = "HOLD"
        chain_pass              = $chainPass
        external_repro_like     = $externalRepro
        gtm_freeze_active       = $gtmFreezeActive
        thread_b_action         = $threadBAction
        thread_b_already_posted = $threadBPosted
        steps                   = $steps
        repro                   = "powershell -File scripts\Invoke-UniversalRootCommunityGtmWeeklyRoutine_v1.ps1"
    }
    $payload | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $reportPath -Encoding utf8
    Write-Host "OK: UR community GTM weekly -> $reportPath action=$threadBAction repro=$externalRepro"
    exit 0
}
finally {
    Pop-Location
}
