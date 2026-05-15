#Requires -Version 5.1
<#
.SYNOPSIS
  암행어사 거버넌스 단일 주기: SafeOps 표면 + NotebookLM MCP 위생 + 레포 비밀 위생 + no1kmedi 내부 API 규격 점검(읽기 전용).

.DESCRIPTION
  docs/final/artifacts/amsaeng_eosa_governance_scope_v1.json 과 정합. 고위험 청소·실매매·비밀 평문 처리는 포함하지 않음.

.PARAMETER IncludeVpsSmoke
  Invoke-SafeOpsSurfaceCheck 에 전달(VPS SSH 스모크 SoftFail은 SafeOps 내부).

.PARAMETER StrictTradingGoNoGo
  Invoke-SafeOpsSurfaceCheck 에 `-StrictTradingGoNoGo` 전달(Trinity LOCKED disk NO_GO를 verify 실패로; 감사용).

.PARAMETER SoftFail
  최종 exit 0 (reports JSON 에 would_exit 기록). 번들 말단 연동용.

.PARAMETER SkipSafeOps / SkipMcpHygiene / SkipSecretHygiene / SkipNo1kmediApiProbe
  단계 생략.

.PARAMETER SkipAlertLog
  worst_exit > 0 일 때 reports/amsaeng_eosa_governance_alert_log.jsonl 에 append 하지 않음.
#>
param(
    [string]$WorkspaceRoot = "",
    [switch]$IncludeVpsSmoke,
    [switch]$StrictTradingGoNoGo,
    [switch]$SkipSafeOps,
    [switch]$SkipMcpHygiene,
    [switch]$SkipSecretHygiene,
    [switch]$SkipNo1kmediApiProbe,
    [switch]$SoftFail,
    [switch]$SkipAlertLog,
    [string]$OutJson = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($WorkspaceRoot)) {
    $WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}
if ([string]::IsNullOrWhiteSpace($OutJson)) {
    $OutJson = Join-Path $WorkspaceRoot "reports\amsaeng_eosa_governance_cycle_latest.json"
}

$ts = [datetime]::UtcNow.ToString("o")
$phases = [System.Collections.Generic.List[object]]::new()
$worst = 0

function Normalize-PhaseExit([object]$Code) {
    if ($null -eq $Code) { return 0 }
    $c = [int]$Code
    if ($c -lt 0) { return 1 }
    return $c
}

function Add-Phase([string]$Name, [object]$ExitCode) {
    $c = Normalize-PhaseExit $ExitCode
    $script:phases.Add([ordered]@{ name = $Name; exit_code = $c })
    $script:worst = [Math]::Max($script:worst, $c)
}

if (-not $SkipSafeOps) {
    $safe = Join-Path $WorkspaceRoot "scripts\Invoke-SafeOpsSurfaceCheck.ps1"
    if (Test-Path -LiteralPath $safe) {
        $safeCli = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $safe, "-WorkspaceRoot", $WorkspaceRoot)
        if ($IncludeVpsSmoke) { $safeCli += "-IncludeVpsSmoke" }
        if ($StrictTradingGoNoGo) { $safeCli += "-StrictTradingGoNoGo" }
        & powershell.exe @safeCli
        Add-Phase "safe_ops_surface" $LASTEXITCODE
    }
    else {
        Add-Phase "safe_ops_surface" -1
    }
}

if (-not $SkipMcpHygiene) {
    $mcp = Join-Path $WorkspaceRoot "scripts\Invoke-McpHygieneProbe.ps1"
    $mcpOut = Join-Path $WorkspaceRoot "reports\amsaeng_eosa_mcp_hygiene_cycle_latest.json"
    if (Test-Path -LiteralPath $mcp) {
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $mcp -WorkspaceRoot $WorkspaceRoot -OutJson $mcpOut -Quiet
        Add-Phase "mcp_notebooklm_hygiene" $LASTEXITCODE
    }
    else {
        Add-Phase "mcp_notebooklm_hygiene" -1
    }
}

if (-not $SkipSecretHygiene) {
    $sec = Join-Path $WorkspaceRoot "scripts\Verify-MonorepoSecretHygiene.ps1"
    if (Test-Path -LiteralPath $sec) {
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $sec -RepoRoot $WorkspaceRoot
        Add-Phase "repo_secret_hygiene" $LASTEXITCODE
    }
    else {
        Add-Phase "repo_secret_hygiene" -1
    }
}

if (-not $SkipNo1kmediApiProbe) {
    $n1p = Join-Path $WorkspaceRoot "scripts\Invoke-No1kmediInternalApiSecurityProbe_v1.ps1"
    $saProbe = ($env:AMSAENG_NO1KMEDI_SECURITY_AGENT_PROBE -eq "1")
    if (Test-Path -LiteralPath $n1p) {
        $probeCli = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $n1p, "-WorkspaceRoot", $WorkspaceRoot)
        if ($saProbe) {
            $probeCli += "-SecurityAgentProbe"
        }
        & powershell.exe @probeCli
        Add-Phase "no1kmedi_internal_api_contract" $LASTEXITCODE
    }
    else {
        Add-Phase "no1kmedi_internal_api_contract" -1
    }
}

$payload = [ordered]@{
    schema             = "amsaeng_eosa_governance_cycle_v1"
    generated_at_utc   = $ts
    workspace_root     = $WorkspaceRoot
    include_vps_smoke  = [bool]$IncludeVpsSmoke
    phases             = @($phases)
    worst_exit         = $worst
    scope_registry     = "docs/final/artifacts/amsaeng_eosa_governance_scope_v1.json"
}

if ($SoftFail) {
    $payload.would_exit = $worst
}

$dir = Split-Path -Parent $OutJson
if (-not (Test-Path -LiteralPath $dir)) {
    New-Item -ItemType Directory -Path $dir -Force | Out-Null
}
$payload | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $OutJson -Encoding UTF8
Write-Output "amsaeng_eosa_governance_cycle_written=$OutJson worst_exit=$worst soft_fail=$SoftFail"

if ($worst -gt 0 -and -not $SkipAlertLog) {
    $alertPath = Join-Path $WorkspaceRoot "reports\amsaeng_eosa_governance_alert_log.jsonl"
    $phaseArr = @()
    foreach ($p in $phases) { $phaseArr += $p }
    $alertObj = [ordered]@{
        schema             = "amsaeng_eosa_governance_alert_v1"
        generated_at_utc   = [datetime]::UtcNow.ToString("o")
        worst_exit         = $worst
        soft_fail_run      = [bool]$SoftFail
        phases             = $phaseArr
        cycle_report_file  = [System.IO.Path]::GetFileName($OutJson)
    }
    ($alertObj | ConvertTo-Json -Compress -Depth 8) | Add-Content -LiteralPath $alertPath -Encoding UTF8
}

if ($SoftFail) {
    exit 0
}
exit $worst
