#Requires -Version 5.1
$ErrorActionPreference = "Stop"
$fixture = "C:\workspace\projects\no1kmedi\scripts\fixtures\paste-chart-sample-ko-v1.txt"
$expected = (Get-Content -LiteralPath $fixture -Raw -Encoding UTF8).TrimEnd()
Set-Clipboard -Value $expected
$clip = (Get-Clipboard -Raw).TrimEnd()

function Normalize-Text([string]$t) {
    return ($t -replace "`r`n", "`n").TrimEnd()
}

$expNorm = Normalize-Text $expected
$clipNorm = Normalize-Text $clip
$expBytes = [System.Text.Encoding]::UTF8.GetBytes($expNorm)
$clipBytes = [System.Text.Encoding]::UTF8.GetBytes($clipNorm)

if ($expBytes.Length -ne $clipBytes.Length) {
    throw "clipboard utf8 byte len mismatch clip=$($clipBytes.Length) expected=$($expBytes.Length)"
}
for ($i = 0; $i -lt $expBytes.Length; $i++) {
    if ($expBytes[$i] -ne $clipBytes[$i]) {
        throw "clipboard utf8 byte mismatch at index $i"
    }
}
Write-Host "[paste-chart-utf8] clipboard OK (utf8 bytes=$($expBytes.Length))" -ForegroundColor Green
