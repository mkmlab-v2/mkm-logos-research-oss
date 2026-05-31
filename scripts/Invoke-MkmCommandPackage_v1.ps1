#Requires -Version 5.1

<#

.SYNOPSIS

  MKM 수동 명령 패키지 — 「아테나 소환」 등 원클릭 체인.



.DESCRIPTION

  SSOT: docs/final/artifacts/mkm_command_package_manifest_v1.json

  Fact-Lock: exit code만 판정. 예약 Task 대체 아님 — 지휘관이 매일/주간 직접 실행.



  Paste Helper (기본 ON): 종료 시 1줄 요약을 클립보드 + reports/mkm_command_package_paste_latest.json



.PARAMETER Package

  OpsSummonLite | AthenaSummon | DailyOpsPatrol | WeeklyOpsPatrol | AthenaSummonFull | AthenaOpsMemory | InterpretBtrackGate | BillingPatrol | AmsaengPatrol



.PARAMETER List

  등록 패키지·별칭 목록만 출력.



.PARAMETER DryRun

  실행 계획만 출력.



.PARAMETER ContinueOnFail

  required=false 단계 실패 시 계속 (required=true 실패 시 중단).



.PARAMETER NoClipboard

  Paste Helper 1줄 요약을 클립보드에 넣지 않음 (파일·콘솔만).



.PARAMETER SendTelegram

  Paste 1줄을 Telegram으로 전송 (TELEGRAM_BOT_TOKEN·TELEGRAM_CHAT_ID 필요; 미설정 시 skip).



.EXAMPLE

  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmCommandPackage_v1.ps1 -Package DailyOpsPatrol



.EXAMPLE

  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmCommandPackage_v1.ps1 -List

#>

param(

    [Parameter(ParameterSetName = 'Run')]

    [ValidateSet(

        'OpsSummonLite', 'AthenaSummon', 'DailyOpsPatrol', 'WeeklyOpsPatrol',

        'AthenaSummonFull', 'AthenaOpsMemory', 'InterpretBtrackGate', 'BillingPatrol', 'AmsaengPatrol'

    )]

    [string]$Package,



    [Parameter(ParameterSetName = 'List')]

    [switch]$List,



    [switch]$DryRun,

    [switch]$ContinueOnFail,

    [switch]$NoClipboard,

    [switch]$SendTelegram

)



Set-StrictMode -Version Latest

$ErrorActionPreference = 'Stop'



$script:StepResults = [System.Collections.Generic.List[object]]::new()

$script:PackageRunFailed = $false

$script:PackageRunRequiredFailed = $false



$WorkspaceRoot = if ($env:MKM_WORKSPACE_ROOT -and (Test-Path -LiteralPath $env:MKM_WORKSPACE_ROOT)) {

    $env:MKM_WORKSPACE_ROOT.TrimEnd('\', '/')

} else {

    (Resolve-Path (Join-Path $PSScriptRoot '..')).Path

}



$ManifestPath = Join-Path $WorkspaceRoot 'docs/final/artifacts/mkm_command_package_manifest_v1.json'

if (-not (Test-Path -LiteralPath $ManifestPath)) {

    throw "Missing manifest: $ManifestPath"

}



$manifest = Get-Content -LiteralPath $ManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json

$packages = $manifest.packages



function Get-ResolvedSteps {

    param($PkgDef)

    $steps = @()

    $names = $PkgDef.PSObject.Properties.Name

    if ($names -contains 'extends') {

        $parentName = $PkgDef.extends

        $parent = $packages.$parentName

        if (-not $parent) { throw "extends parent not found: $parentName" }

        $steps += Get-ResolvedSteps -PkgDef $parent

    }

    if ($names -contains 'steps' -and $PkgDef.steps) {

        $steps += @($PkgDef.steps)

    }

    if ($names -contains 'steps_after_extend' -and $PkgDef.steps_after_extend) {

        $steps += @($PkgDef.steps_after_extend)

    }

    return $steps

}



function Show-PackageList {

    $packages.PSObject.Properties | ForEach-Object {

        $name = $_.Name

        $p = $_.Value

        $aliases = @($p.aliases) -join ' · '

        Write-Host "[$name] $($p.label_ko) (~$($p.estimated_minutes) min)"

        if ($aliases) { Write-Host "  aliases: $aliases" }

        $triggers = @($p.chat_triggers) -join ' '

        if ($triggers) { Write-Host "  chat: $triggers" }

    }

}



function Get-StepStatusLabel {

    param([int]$ExitCode)

    if ($ExitCode -eq 0) { return 'pass' }

    return 'fail'

}



function Get-EnrichmentHints {

    $hints = @{}

    $reconcilePath = Join-Path $WorkspaceRoot 'projects\bitcoin-trading\memory\v2\ops\automation_registry_reconcile_latest.json'

    if (Test-Path -LiteralPath $reconcilePath) {

        try {

            $rec = Get-Content -LiteralPath $reconcilePath -Raw -Encoding UTF8 | ConvertFrom-Json

            $drift = $null

            if ($rec.PSObject.Properties.Name -contains 'drift_count') { $drift = [int]$rec.drift_count }

            elseif ($rec.PSObject.Properties.Name -contains 'missing_task_count') { $drift = [int]$rec.missing_task_count }

            if ($null -ne $drift) {

                $hints['Athena'] = if ($drift -eq 0) { 'aligned' } else { "drift:$drift" }

            }

        }

        catch { }

    }

    $mcpPath = Join-Path $WorkspaceRoot 'reports\mcp_hygiene_probe_latest.json'

    if (Test-Path -LiteralPath $mcpPath) {

        try {

            $mcp = Get-Content -LiteralPath $mcpPath -Raw -Encoding UTF8 | ConvertFrom-Json

            if ($mcp.PSObject.Properties.Name -contains 'summary') {

                $hints['MCP'] = [string]$mcp.summary

            }

        }

        catch { }

    }

    $taskGuard = Join-Path $WorkspaceRoot 'reports\mkm_scheduled_task_whitelist_guard_latest.json'

    if (Test-Path -LiteralPath $taskGuard) {

        try {

            $tg = Get-Content -LiteralPath $taskGuard -Raw -Encoding UTF8 | ConvertFrom-Json

            if ($tg.summary) { $hints['Tasks'] = [string]$tg.summary }

        }

        catch { }

    }

    return $hints

}



function Build-PackagePasteLine {

    param(

        [string]$PackageName,

        [int]$OptionalFailCount,

        [int]$ProcessExitCode

    )



    $labelMap = @{

        'p0_paths'                   = 'P0'

        'athena_automation_registry' = 'Athena'

        'ops_patrol_health'          = 'Env'

        'amsaeng_governance'         = 'Amsaeng'

        'notebooklm_prereqs'         = 'NL-MCP'

        'secrets_hybrid'             = 'Secrets'

        'git_sanity'                 = 'Git'

        'remote_mode'                = 'Remote'

        'chat_resume_pack'           = 'Resume'

        'schtasks_whitelist_guard'   = 'Tasks'

    }



    $parts = [System.Collections.Generic.List[string]]::new()

    $seen = @{}

    foreach ($r in $script:StepResults) {

        $id = [string]$r.id

        $short = if ($labelMap.ContainsKey($id)) { $labelMap[$id] } else { $id }

        if ($seen.ContainsKey($short)) { continue }

        $seen[$short] = $true

        $st = Get-StepStatusLabel -ExitCode ([int]$r.exit_code)

        $parts.Add("${short}:$st") | Out-Null

    }



    $hints = Get-EnrichmentHints

    foreach ($key in @('Athena', 'MCP', 'Tasks')) {
        if (-not $hints.ContainsKey($key) -or -not $seen.ContainsKey($key)) { continue }
        $prefix = "${key}:"
        for ($i = 0; $i -lt $parts.Count; $i++) {
            if ($parts[$i].StartsWith($prefix)) {
                $parts[$i] = "$key`:$($hints[$key])"
                break
            }
        }
    }



    $dateLocal = (Get-Date).ToString('yyyy-MM-dd')

    $overall = if ($script:PackageRunRequiredFailed) { 'FAIL' }

    elseif ($OptionalFailCount -gt 0 -or $ProcessExitCode -ne 0) { 'WARN' }

    else { 'OK' }



    $detail = ($parts -join ', ')

    $tail = "opt_fail:$OptionalFailCount"

    $line = "[$PackageName] $dateLocal $overall ($detail; $tail) | Shadow Only | No Track A/live"

    return $line

}



function Write-PackagePasteArtifact {

    param(

        [string]$PackageName,

        [string]$PasteLine,

        [int]$ProcessExitCode,

        [int]$OptionalFailCount

    )

    $outPath = Join-Path $WorkspaceRoot 'reports\mkm_command_package_paste_latest.json'

    $dir = Split-Path -Parent $outPath

    if (-not (Test-Path -LiteralPath $dir)) {

        New-Item -ItemType Directory -Path $dir -Force | Out-Null

    }

    $payload = [ordered]@{

        schema              = 'mkm_command_package_paste_v1'

        package             = $PackageName

        paste_line          = $PasteLine

        generated_at_local  = (Get-Date).ToString('o')

        process_exit_code   = $ProcessExitCode

        optional_fail_count = $OptionalFailCount

        required_failed     = $script:PackageRunRequiredFailed

        steps               = @($script:StepResults | ForEach-Object {

            [ordered]@{ id = $_.id; exit_code = $_.exit_code; required = $_.required }

        })

    }

    $payload | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $outPath -Encoding UTF8

    return $outPath

}



function Set-PackagePasteClipboard {

    param([string]$Line)

    try {

        Set-Clipboard -Value $Line

        return $true

    }

    catch {

        Write-Host "  (clipboard unavailable: $($_.Exception.Message))" -ForegroundColor Yellow

        return $false

    }

}



function Send-PackagePasteTelegram {

    param([string]$Line)

    $token = $env:TELEGRAM_BOT_TOKEN

    $chat = $env:TELEGRAM_CHAT_ID

    if ([string]::IsNullOrWhiteSpace($token) -or [string]::IsNullOrWhiteSpace($chat)) {

        Write-Host "  Telegram skip: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set" -ForegroundColor Yellow

        return

    }

    $body = @{ chat_id = $chat; text = $Line; disable_web_page_preview = $true } | ConvertTo-Json -Compress

    try {

        Invoke-RestMethod -Uri "https://api.telegram.org/bot$token/sendMessage" `

            -Method Post -ContentType 'application/json; charset=utf-8' -Body $body | Out-Null

        Write-Host "  Telegram sent (1 line)" -ForegroundColor Green

    }

    catch {

        Write-Host "  Telegram send failed: $($_.Exception.Message)" -ForegroundColor Yellow

    }

}



function Invoke-StepCommand {

    param(

        [string]$StepId,

        [string]$Title,

        [object[]]$Command,

        [bool]$Required

    )

    $cmdDisplay = $Command -join ' '

    Write-Host ""

    Write-Host "==> [$StepId] $Title"

    Write-Host "    $cmdDisplay"

    if ($DryRun) {

        $script:StepResults.Add([pscustomobject]@{ id = $StepId; exit_code = 0; required = $Required }) | Out-Null

        return 0

    }



    $exe = $Command[0]

    $args = @($Command[1..($Command.Length - 1)])

    & $exe @args 2>&1 | Out-Null

    $code = if ($null -ne $LASTEXITCODE) { [int]$LASTEXITCODE } else { 0 }

    $script:StepResults.Add([pscustomobject]@{ id = $StepId; exit_code = $code; required = $Required }) | Out-Null



    if ($code -ne 0) {

        Write-Host "    exit $code" -ForegroundColor Red

        $script:PackageRunFailed = $true

        if ($Required) {

            $script:PackageRunRequiredFailed = $true

            throw "Required step failed: $StepId (exit $code)"

        }

        if (-not $ContinueOnFail) {

            throw "Step failed: $StepId (exit $code). Use -ContinueOnFail to skip optional failures."

        }

        Write-Host "    (continuing)" -ForegroundColor Yellow

    }

    else {

        Write-Host "    exit 0" -ForegroundColor Green

    }

    return $code

}



if ($List) {

    Show-PackageList

    exit 0

}



if (-not $Package) {

    Write-Host "Usage: -Package <name> | -List"

    Show-PackageList

    exit 1

}



$pkgDef = $packages.$Package

if (-not $pkgDef) { throw "Unknown package: $Package" }



$processExit = 0

Push-Location -LiteralPath $WorkspaceRoot

try {

    Write-Host "MKM Command Package: $Package - $($pkgDef.label_ko)"

    if ($pkgDef.PSObject.Properties.Name -contains 'cost_lock_note') {

        Write-Host "cost_lock: $($pkgDef.cost_lock_note)"

    }



    $steps = Get-ResolvedSteps -PkgDef $pkgDef

    $failed = 0

    foreach ($step in $steps) {

        try {

            $code = Invoke-StepCommand -StepId $step.id -Title $step.title -Command $step.command -Required ([bool]$step.required)

            if ($code -ne 0) { $failed++ }

        }

        catch {

            if ($DryRun) { throw }

            break

        }

    }



    Write-Host ""

    Write-Host "==> artifacts (paste / @ in Cursor)"

    if (($pkgDef.PSObject.Properties.Name -contains 'artifacts_after') -and $pkgDef.artifacts_after) {

        foreach ($rel in $pkgDef.artifacts_after) {

            $full = Join-Path $WorkspaceRoot ($rel -replace '/', '\')

            $ok = Test-Path -LiteralPath $full

            $tag = if ($ok) { '[ok]' } else { '[missing]' }

            Write-Host "  $tag $rel"

        }

    }

    if (($pkgDef.PSObject.Properties.Name -contains 'cursor_open') -and $pkgDef.cursor_open) {

        Write-Host ""

        Write-Host "==> Cursor open hints"

        foreach ($c in $pkgDef.cursor_open) {

            $at = if ($c -match '^@') { $c } else { "@$c" }

            Write-Host "  $at"

        }

    }

    if (($pkgDef.PSObject.Properties.Name -contains 'manual_after') -and $pkgDef.manual_after) {

        Write-Host ""

        Write-Host "==> manual (not scripted)"

        foreach ($m in $pkgDef.manual_after) { Write-Host "  - $m" }

    }



    if ($failed -gt 0 -and -not $DryRun) {

        $processExit = 1

    }



    $pasteLine = Build-PackagePasteLine -PackageName $Package -OptionalFailCount $failed -ProcessExitCode $processExit

    $artifactPath = Write-PackagePasteArtifact -PackageName $Package -PasteLine $pasteLine -ProcessExitCode $processExit -OptionalFailCount $failed



    Write-Host ""

    Write-Host "==> paste helper (1 line)"

    Write-Host "  $pasteLine"

    Write-Host "  file: $artifactPath"



    if (-not $DryRun -and -not $NoClipboard) {

        if (Set-PackagePasteClipboard -Line $pasteLine) {

            Write-Host "  clipboard: copied (Ctrl+V)" -ForegroundColor Green

        }

    }



    if ($SendTelegram -and -not $DryRun) {

        Send-PackagePasteTelegram -Line $pasteLine

    }

    if (-not $DryRun) {
        $resumeJson = Join-Path $WorkspaceRoot 'docs\final\artifacts\mkm_chat_resume_pack_latest.json'
        if (Test-Path -LiteralPath $resumeJson) {
            $mergePy = Join-Path $WorkspaceRoot 'scripts\merge_mkm_ops_patrol_into_resume_pack_v1.py'
            if (Test-Path -LiteralPath $mergePy) {
                Write-Host ""
                Write-Host "==> resume pack merge (last_ops_patrol)"
                & py $mergePy 2>&1 | Out-Null
                if ($LASTEXITCODE -eq 0) {
                    Write-Host "  merged into mkm_chat_resume_pack_latest.json (field: last_ops_patrol)" -ForegroundColor Green
                }
                else {
                    Write-Host "  merge skip or fail (exit $LASTEXITCODE); paste file still valid" -ForegroundColor Yellow
                }
            }
        }
    }

    Write-Host ""

    Write-Host "==> chat one-liner"

    Write-Host "  @docs/final/artifacts/mkm_chat_resume_pack_latest.json includes last_ops_patrol when merge OK."



    if ($processExit -ne 0) {

        Write-Host "Completed with $failed non-zero optional step(s)." -ForegroundColor Yellow

        exit $processExit

    }

    Write-Host "OK: $Package"

    exit 0

}

finally {

    Pop-Location

}


