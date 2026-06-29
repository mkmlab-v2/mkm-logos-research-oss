$path = 'c:\workspace\reports\kaggle_nemotron_notebook_cell1_writefile_v35.txt'
$text = Get-Content -Path $path -Raw -Encoding UTF8
Set-Clipboard -Value $text
$lines = ($text -split "`n").Count
Write-Host "OK: clipboard <- $path ($lines lines, $($text.Length) chars)"
