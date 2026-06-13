param(
    [string]$TaskName = "MKM_NewsNeutralizer_Shadow_Weekly",
    [string]$ExpectedRunner = "Run-NewsNeutralizerShadowChain_v1.ps1"
)

$ErrorActionPreference = "Stop"
$shortName = $TaskName.TrimStart("\")
$t = Get-ScheduledTask -TaskName $shortName -ErrorAction Stop
$info = Get-ScheduledTaskInfo -InputObject $t
$a = $t.Actions[0]
$argsText = [string]$a.Arguments
$runnerOk = $argsText -like "*$ExpectedRunner*"

Write-Output "task_name=$shortName"
Write-Output ("state={0}" -f $t.State)
Write-Output ("last_run_time={0}" -f $info.LastRunTime)
Write-Output ("last_task_result={0}" -f $info.LastTaskResult)
Write-Output ("execute={0}" -f $a.Execute)
Write-Output ("arguments={0}" -f $a.Arguments)
Write-Output ("working_directory={0}" -f $a.WorkingDirectory)
Write-Output ("runner_present={0}" -f $runnerOk)
Write-Output ("billing_azure={0}" -f ($argsText -match '\-Billing\s+azure\b'))
Write-Output ("include_live={0}" -f ($argsText -match '\-Live\b'))
Write-Output ("use_fixture={0}" -f ($argsText -match '\-Fixture\b'))

if (-not $runnerOk) {
    exit 1
}
exit 0
