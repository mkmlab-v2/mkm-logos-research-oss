# NVIDIA NIM chat wrapper — smoke default
param(
    [Parameter(Position = 0)]
    [ValidateSet('smoke', 'list-models')]
    [string] $Mode = 'smoke',
    [string] $Prompt = '',
    [string] $Model = ''
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
if ($Prompt) {
    $pyArgs = @('scripts/nvidia_nim_chat_v1.py', 'chat', '--prompt', $Prompt)
} else {
    $pyArgs = @('scripts/nvidia_nim_chat_v1.py', $Mode)
}
if ($Model) { $pyArgs += @('--model', $Model) }
& py @pyArgs
exit $LASTEXITCODE
