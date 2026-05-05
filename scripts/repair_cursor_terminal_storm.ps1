param(
    [int]$MaxCursorPwsh = 1
)

$ErrorActionPreference = "SilentlyContinue"

function Get-Count([string]$name) {
    (Get-Process -Name $name -ErrorAction SilentlyContinue | Measure-Object).Count
}

function Get-CursorNodePids {
    (Get-CimInstance Win32_Process -Filter "Name='Cursor.exe'" |
        Where-Object { $_.CommandLine -match '--type=utility --utility-sub-type=node.mojom.NodeService' } |
        Select-Object -ExpandProperty ProcessId)
}

$beforeCon = Get-Count "conhost"
$beforePwsh = Get-Count "pwsh"
Write-Output "[before] conhost=$beforeCon pwsh=$beforePwsh"

$cursorNodePids = @(Get-CursorNodePids)
$killedCursorPwsh = 0

if ($cursorNodePids.Count -gt 0) {
    $cursorPwsh = Get-CimInstance Win32_Process -Filter "Name='pwsh.exe'" |
        Where-Object { $cursorNodePids -contains $_.ParentProcessId } |
        Sort-Object CreationDate

    $excess = @()
    if ($cursorPwsh.Count -gt $MaxCursorPwsh) {
        $excess = $cursorPwsh | Select-Object -First ($cursorPwsh.Count - $MaxCursorPwsh)
    }
    $killedCursorPwsh = @($excess).Count
    $excess | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
}

$orphans = Get-CimInstance Win32_Process -Filter "Name='conhost.exe'" |
    Where-Object { -not (Get-Process -Id $_.ParentProcessId -ErrorAction SilentlyContinue) }
$killedOrphanConhost = @($orphans).Count
$orphans | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }

Start-Sleep -Seconds 1

$remainingCursorPwsh = 0
if ($cursorNodePids.Count -gt 0) {
    $remainingCursorPwsh = @(
        Get-CimInstance Win32_Process -Filter "Name='pwsh.exe'" |
            Where-Object { $cursorNodePids -contains $_.ParentProcessId }
    ).Count
}
$remainingOrphanConhost = (Get-CimInstance Win32_Process -Filter "Name='conhost.exe'" |
    Where-Object { -not (Get-Process -Id $_.ParentProcessId -ErrorAction SilentlyContinue) }).Count

Write-Output "[result] cursor_node_pids=$($cursorNodePids -join ',')"
Write-Output "[result] killed_cursor_pwsh=$killedCursorPwsh remain_cursor_pwsh=$remainingCursorPwsh"
Write-Output "[result] killed_orphan_conhost=$killedOrphanConhost remain_orphan_conhost=$remainingOrphanConhost"
Write-Output "[after] conhost=$(Get-Count 'conhost') pwsh=$(Get-Count 'pwsh')"
