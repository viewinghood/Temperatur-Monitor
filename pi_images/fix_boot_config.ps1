# Fix hung Bullseye boot — write recovery config.txt to SD boot partition
$ErrorActionPreference = 'Stop'
$Src = 'C:\Users\ritchie\temp_monitor\pi_images\config.txt.recovery'
$PubKey = 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIA+WO1zLHQHMf5nRveK9m94K17bKLx1D4lL8pFlokErN ritchie@lenovo-temp-monitor'

if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Error 'Run as Administrator'
}

$boot = $null
foreach ($c in @('I','J','K','L','M','D')) {
    if (Test-Path "${c}:\config.txt") { $boot = "${c}:\"; break }
}
if (-not $boot) {
    $p = Get-Partition | Where-Object { $_.Type -match 'FAT32' -and $_.Size -lt 600MB -and $_.DriveLetter } | Select-Object -First 1
    if ($p) { $boot = "$($p.DriveLetter):\" }
}
if (-not $boot) { Write-Error 'SD boot partition not found — insert SD card' }

Write-Host "Fixing boot on $boot"
Copy-Item $Src (Join-Path $boot 'config.txt') -Force
if (Test-Path (Join-Path $boot 'config.txt.broken')) { Remove-Item (Join-Path $boot 'config.txt.broken') -Force }
if (-not (Test-Path (Join-Path $boot 'config.txt.broken'))) {
    # keep backup of broken if still named config.txt - already overwritten
}
New-Item -Path (Join-Path $boot 'ssh') -ItemType File -Force | Out-Null
Set-Content -Path (Join-Path $boot 'authorized_keys') -Value $PubKey -Encoding ascii
Write-Host 'Recovery config written. Safe eject and boot Pi with HDMI only.'
Get-Content (Join-Path $boot 'config.txt') | Select-String -Pattern 'hdmi|spi|i2c|ignore_lcd|vc4'
