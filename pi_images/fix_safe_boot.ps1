# Safe boot fix — skip GUI (no LightDM), Pi3-friendly display, SPI/I2C on
$ErrorActionPreference = 'Stop'
$PubKey = 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIA+WO1zLHQHMf5nRveK9m94K17bKLx1D4lL8pFlokErN ritchie@lenovo-temp-monitor'

if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Error 'Run as Administrator'
}

$boot = $null
foreach ($c in @('I','J','K','L','M','D')) {
    if (Test-Path "${c}:\config.txt") { $boot = "${c}:\"; break }
}
if (-not $boot) { Write-Error 'SD boot partition not found — insert SD in reader' }

Write-Host "SAFE BOOT fix on $boot"

# Backup
Copy-Item (Join-Path $boot 'config.txt') (Join-Path $boot 'config.txt.bak-fail') -Force -ErrorAction SilentlyContinue
Copy-Item (Join-Path $boot 'cmdline.txt') (Join-Path $boot 'cmdline.txt.bak-fail') -Force -ErrorAction SilentlyContinue

# config.txt
Copy-Item 'C:\Users\ritchie\temp_monitor\pi_images\config.txt.safe' (Join-Path $boot 'config.txt') -Force

# cmdline: boot to multi-user (NO graphical / NO lightdm)
$cmd = (Get-Content (Join-Path $boot 'cmdline.txt') -Raw).Trim()
if ($cmd -notmatch 'systemd\.unit=multi-user\.target') {
    $cmd = "$cmd systemd.unit=multi-user.target"
    Set-Content -Path (Join-Path $boot 'cmdline.txt') -Value $cmd -NoNewline -Encoding ascii
}

# SSH headless
New-Item -Path (Join-Path $boot 'ssh') -ItemType File -Force | Out-Null
Set-Content -Path (Join-Path $boot 'authorized_keys') -Value $PubKey -Encoding ascii

Write-Host 'OK — config.txt.safe + multi-user boot (no LightDM)'
Write-Host 'cmdline:' (Get-Content (Join-Path $boot 'cmdline.txt'))
Write-Host 'config highlights:'
Get-Content (Join-Path $boot 'config.txt') | Select-String 'fkms|hdmi|spi|multi'
