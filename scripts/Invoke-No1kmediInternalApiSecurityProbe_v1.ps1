#Requires -Version 5.1
<#
.SYNOPSIS
  no1kmedi 내부 API(admin) 통신 규격 정적 검사 + 선택적 Security Agent(DPAPI) 프로브.

.DESCRIPTION
  암행어사 거버넌스 주기(Invoke-AmsaengEosaGovernanceCycle.ps1)에서 호출한다.
  비밀 값은 출력하지 않는다.

.PARAMETER SecurityAgentProbe
  security_agent_manager 가 NO1KMEDI_ADMIN_TOKEN 키를 해석할 수 있는지 시도(DPAPI 등).
#>
param(
    [string]$WorkspaceRoot = "",
    [switch]$SecurityAgentProbe
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($WorkspaceRoot)) {
    $WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}

$py = Join-Path $env:WINDIR "py.exe"
if (-not (Test-Path -LiteralPath $py)) {
    $py = (Get-Command -Name "py" -ErrorAction Stop).Source
}

$scriptPath = Join-Path $WorkspaceRoot "scripts\check_no1kmedi_internal_api_security_contract_v1.py"
if (-not (Test-Path -LiteralPath $scriptPath)) {
    Write-Error "Missing $scriptPath"
    exit 2
}

$cli = @($scriptPath, "--workspace-root", $WorkspaceRoot)
if ($SecurityAgentProbe) {
    $cli += "--security-agent-probe"
}

Push-Location -LiteralPath $WorkspaceRoot
$exitCode = 1
try {
    & $py @cli
    $exitCode = $LASTEXITCODE
}
finally {
    Pop-Location
}
exit $exitCode
